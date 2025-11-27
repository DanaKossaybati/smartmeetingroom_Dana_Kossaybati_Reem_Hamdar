import pika
import json
import logging
from datetime import datetime, timezone
import threading

logger = logging.getLogger(__name__)

class RabbitMQClient:
    """Thread-safe RabbitMQ client with separate producer and consumer connections"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.producer_connection = None
        self.producer_channel = None
        self.consumer_connection = None
        self.consumer_channel = None
        self._connected = False
        self._lock = threading.Lock()  # Thread safety for producer

    def _get_connection_params(self):
        """Get connection parameters"""
        return pika.ConnectionParameters(
            host='rabbitmq',
            port=5672,
            virtual_host='/dev',
            credentials=pika.PlainCredentials('admin', 'admin123'),
            connection_attempts=5,
            retry_delay=3,
            heartbeat=600,
            blocked_connection_timeout=300
        )

    def connect(self) -> bool:
        """Connect producer - call this once on startup"""
        try:
            logger.info(f"[{self.service_name}] Connecting producer to RabbitMQ...")

            self.producer_connection = pika.BlockingConnection(self._get_connection_params())
            self.producer_channel = self.producer_connection.channel()
            self.producer_channel.confirm_delivery()

            # Declare exchange upfront
            self.producer_channel.exchange_declare(
                exchange='domain_events',
                exchange_type='topic',
                durable=True
            )

            logger.info(f"[{self.service_name}] ✅ Producer connected to RabbitMQ")
            self._connected = True
            return True

        except pika.exceptions.ProbableAuthenticationError as e:
            logger.error(f"[{self.service_name}] ❌ Authentication failed: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"[{self.service_name}] ❌ Connection failed: {e}")
            self._connected = False
            return False

    def is_connected(self) -> bool:
        """Check if producer connection is active"""
        return (self._connected and
                self.producer_connection and
                not self.producer_connection.is_closed and
                self.producer_channel and
                self.producer_channel.is_open)

    def publish_event(self, event_name: str, payload: dict):
        """
        Thread-safe event publishing
        Example: publish_event("user.created", {"user_id": 123})
        """
        if not self.is_connected():
            logger.warning(f"[{self.service_name}] ⚠️ Cannot publish {event_name}: Not connected")
            return False

        message = {
            "event_type": event_name,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name
        }

        # Thread-safe publishing
        with self._lock:
            try:
                self.producer_channel.basic_publish(
                    exchange='domain_events',
                    routing_key=event_name,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json',
                        timestamp=int(datetime.now(timezone.utc).timestamp())
                    )
                )

                logger.info(f"[{self.service_name}] 📤 Published {event_name}")
                return True

            except Exception as e:
                logger.error(f"[{self.service_name}] 📤 Publish failed: {e}")
                self._connected = False
                return False

    def start_consuming(self, queue_name: str, event_handlers: dict):
        """
        Start consuming events with dedicated consumer connection
        event_handlers = {"user.created": handler_function}
        """
        try:
            logger.info(f"[{self.service_name}] Connecting consumer to RabbitMQ...")

            # Separate connection for consumer
            self.consumer_connection = pika.BlockingConnection(self._get_connection_params())
            self.consumer_channel = self.consumer_connection.channel()

            # Declare exchange
            self.consumer_channel.exchange_declare(
                exchange='domain_events',
                exchange_type='topic',
                durable=True
            )

            # Declare queue
            self.consumer_channel.queue_declare(
                queue=queue_name,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': 'dlx_exchange',
                    'x-message-ttl': 86400000
                }
            )

            # Bind queue to events
            for event_name in event_handlers.keys():
                self.consumer_channel.queue_bind(
                    exchange='domain_events',
                    queue=queue_name,
                    routing_key=event_name
                )
                logger.info(f"[{self.service_name}] 🔗 Bound to {event_name}")

            def callback(ch, method, properties, body):
                try:
                    message = json.loads(body)
                    event_type = message['event_type']

                    if event_type in event_handlers:
                        handler = event_handlers[event_type]
                        handler(message['payload'])
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    else:
                        logger.warning(f"[{self.service_name}] ⚠️ No handler for {event_type}")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

                except Exception as e:
                    logger.error(f"[{self.service_name}] ❌ Message processing failed: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            self.consumer_channel.basic_qos(prefetch_count=10)
            self.consumer_channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback
            )

            logger.info(f"[{self.service_name}] ✅ Consumer started, waiting for messages...")
            self.consumer_channel.start_consuming()

        except Exception as e:
            logger.error(f"[{self.service_name}] ❌ Consumer failed: {e}")
            raise

    def close(self):
        """Graceful shutdown"""
        if self.producer_connection and not self.producer_connection.is_closed:
            self.producer_connection.close()
            logger.info(f"[{self.service_name}] ❌ Producer disconnected")

        if self.consumer_connection and not self.consumer_connection.is_closed:
            self.consumer_connection.close()
            logger.info(f"[{self.service_name}] ❌ Consumer disconnected")

        self._connected = False