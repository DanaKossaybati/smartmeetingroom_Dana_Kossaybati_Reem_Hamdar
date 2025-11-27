import logging

from rabbitmq_instance import rabbitmq_client

logger = logging.getLogger(__name__)

class RoomProducer:
    """Encapsulates all room-related event publishing"""

    @staticmethod
    def room_created(room_id: int, room_name: str):
        """Publish room.created event"""
        rabbitmq_client.publish_event(
            event_name="room.created",
            payload={
                "room_id": room_id,
                "room_name": room_name,
                "metadata": {"version": "1.0"}
            }
        )
        logger.info(f"Published room.created event for ID {room_id}")

    @staticmethod
    def room_updated(room_id: int):
        """Publish room.updated event"""
        rabbitmq_client.publish_event(
            event_name="room.updated",
            payload={
                "room_id": room_id,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        )

    @staticmethod
    def room_deleted(room_id: int):
        """Publish room.deleted event"""
        rabbitmq_client.publish_event(
            event_name="room.deleted",
            payload={"room_id": room_id}
        )
    @staticmethod
    def room_flagged(room_id: int, reason: str):
        rabbitmq_client.publish_event(
            event_name="room.flagged",
            payload={"room_id": room_id, "reason": reason}
        )
# Create singleton instance
room_producer = RoomProducer()