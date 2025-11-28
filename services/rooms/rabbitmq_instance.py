"""
RabbitMQ client instance for Rooms Service.
Creates a singleton RabbitMQ client for publishing room events.

Author: Reem Hamdar
"""
from core.rabbitmq_client import RabbitMQClient

# Singleton instance for the entire service
# Used to publish domain events like room.created, room.updated, room.deleted
rabbitmq_client=RabbitMQClient("rooms-service")