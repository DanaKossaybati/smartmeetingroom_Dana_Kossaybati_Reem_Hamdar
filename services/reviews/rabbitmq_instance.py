"""
RabbitMQ client instance for Reviews Service.
Creates a singleton RabbitMQ client for publishing review events.

Author: Reem Hamdar
"""
from core.rabbitmq_client import RabbitMQClient

# Singleton instance for the entire service
# Used to publish domain events like review.created, review.updated, review.flagged
rabbitmq_client=RabbitMQClient("reviews-service")