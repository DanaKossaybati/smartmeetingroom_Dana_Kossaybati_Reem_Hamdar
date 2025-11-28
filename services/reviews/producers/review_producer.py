"""
Review event producer for publishing domain events.
Encapsulates all review-related event publishing logic.

Events published:
- review.created: When a new review is submitted
- review.updated: When a review is modified
- review.deleted: When a review is removed
- review.flagged: When a review is flagged for moderation

Author: Reem Hamdar
"""
import logging

from rabbitmq_instance import rabbitmq_client

logger = logging.getLogger(__name__)

class ReviewProducer:
    """
    Encapsulates all review-related event publishing.
    
    This class publishes domain events to RabbitMQ for other services
    to consume. Uses topic exchange for flexible routing.
    
    Exchange: domain_events (topic)
    Routing keys: review.created, review.updated, review.deleted, review.flagged
    """

    @staticmethod
    def review_created(review_id: int, user_id: int, content: str):
        """
        Publish review.created event.
        
        Notifies other services when a new review is posted.
        Analytics service may use this for sentiment analysis.
        
        Args:
            review_id: ID of the newly created review
            user_id: ID of the user who created the review
            content: Review text content
        
        Event payload:
            {
                "review_id": int,
                "user_id": int,
                "content": str,
                "metadata": {"version": "1.0"}
            }
        """
        rabbitmq_client.publish_event(
            event_name="review.created",
            payload={
                "review_id": review_id,
                "user_id": user_id,
                "content": content,
                "metadata": {"version": "1.0"}
            }
        )
        logger.info(f"Published review.created event for ID {review_id}")

    @staticmethod
    def review_updated(review_id: int, user_id: int):
        """
        Publish review.updated event.
        
        Notifies other services when a review is modified.
        
        Args:
            review_id: ID of the updated review
            user_id: ID of the user who updated the review
        
        Event payload:
            {
                "review_id": int,
                "user_id": int,
                "timestamp": str (ISO format)
            }
        """
        rabbitmq_client.publish_event(
            event_name="review.updated",
            payload={
                "review_id": review_id,
                "user_id": user_id,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        )

    @staticmethod
    def review_deleted(review_id: int):
        """
        Publish review.deleted event.
        
        Notifies other services when a review is deleted.
        
        Args:
            review_id: ID of the deleted review
        
        Event payload:
            {
                "review_id": int
            }
        """
        rabbitmq_client.publish_event(
            event_name="review.deleted",
            payload={"review_id": review_id}
        )
        
    @staticmethod
    def review_flagged(review_id: int, reason: str):
        """
        Publish review.flagged event.
        
        Notifies moderators when a review is flagged for inappropriate content.
        
        Args:
            review_id: ID of the flagged review
            reason: Reason for flagging
        
        Event payload:
            {
                "review_id": int,
                "reason": str
            }
        """
        rabbitmq_client.publish_event(
            event_name="review.flagged",
            payload={"review_id": review_id, "reason": reason}
        )

# Create singleton instance
review_producer = ReviewProducer()