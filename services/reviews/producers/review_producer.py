import logging

from rabbitmq_instance import rabbitmq_client

logger = logging.getLogger(__name__)

class ReviewProducer:
    """Encapsulates all review-related event publishing"""

    @staticmethod
    def review_created(review_id: int, user_id: int, content: str):
        """Publish review.created event"""
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
        """Publish review.updated event"""
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
        """Publish review.deleted event"""
        rabbitmq_client.publish_event(
            event_name="review.deleted",
            payload={"review_id": review_id}
        )
    @staticmethod
    def review_flagged(review_id: int, reason: str):
        rabbitmq_client.publish_event(
            event_name="review.flagged",
            payload={"review_id": review_id, "reason": reason}
        )
# Create singleton instance
review_producer = ReviewProducer()