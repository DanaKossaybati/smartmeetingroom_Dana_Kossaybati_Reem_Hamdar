"""
Room event producer for publishing domain events.
Encapsulates all room-related event publishing logic.

Events published:
- room.created: When a new room is added
- room.updated: When room details are modified
- room.deleted: When a room is removed
- room.flagged: When a room is flagged for review

Author: Reem Hamdar
"""
import logging

from rabbitmq_instance import rabbitmq_client

logger = logging.getLogger(__name__)

class RoomProducer:
    """
    Encapsulates all room-related event publishing.
    
    This class publishes domain events to RabbitMQ for other services
    to consume. Uses topic exchange for flexible routing.
    
    Exchange: domain_events (topic)
    Routing keys: room.created, room.updated, room.deleted, room.flagged
    """

    @staticmethod
    def room_created(room_id: int, room_name: str):
        """
        Publish room.created event.
        
        Notifies other services when a new room is created.
        Bookings service may use this to enable booking for the room.
        
        Args:
            room_id: ID of the newly created room
            room_name: Name of the room
        
        Event payload:
            {
                "room_id": int,
                "room_name": str,
                "metadata": {"version": "1.0"}
            }
        """
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
        """
        Publish room.updated event.
        
        Notifies other services when room details are modified.
        
        Args:
            room_id: ID of the updated room
        
        Event payload:
            {
                "room_id": int,
                "timestamp": str (ISO format)
            }
        """
        rabbitmq_client.publish_event(
            event_name="room.updated",
            payload={
                "room_id": room_id,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        )

    @staticmethod
    def room_deleted(room_id: int):
        """
        Publish room.deleted event.
        
        Notifies other services when a room is deleted.
        Bookings service may use this to cancel future bookings.
        
        Args:
            room_id: ID of the deleted room
        
        Event payload:
            {
                "room_id": int
            }
        """
        rabbitmq_client.publish_event(
            event_name="room.deleted",
            payload={"room_id": room_id}
        )
        
    @staticmethod
    def room_flagged(room_id: int, reason: str):
        """
        Publish room.flagged event.
        
        Notifies admins when a room is flagged for review.
        
        Args:
            room_id: ID of the flagged room
            reason: Reason for flagging
        
        Event payload:
            {
                "room_id": int,
                "reason": str
            }
        """
        rabbitmq_client.publish_event(
            event_name="room.flagged",
            payload={"room_id": room_id, "reason": reason}
        )

# Create singleton instance
room_producer = RoomProducer()