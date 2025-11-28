"""
Pydantic schemas for Reviews Service request/response validation.
Defines data models for API endpoints with automatic validation.

Author: Reem Hamdar
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class ReviewRequest(BaseModel):
    """
    Schema for creating a new review.
    
    Attributes:
        room_id: UUID of the room being reviewed
        rating: Star rating (1-5)
        comment: Review text (1-500 characters)
    
    Validation:
        - Rating must be between 1 and 5
        - Comment must not be empty or whitespace only
        - Comment length between 1 and 500 characters
    """
    room_id: str
    rating: int = Field(..., ge=1, le=5, description="Rating must be between 1 and 5")
    comment: str = Field(..., min_length=1, max_length=500, description="Comment must be between 1 and 500 characters")

    @field_validator('comment')
    @classmethod
    def validate_comment(cls, v):
        """Ensure comment contains meaningful content."""
        if v and v.strip() == "":
            raise ValueError("Comment cannot be empty or only whitespace")
        return v.strip()


class ReviewUpdateRequest(BaseModel):
    """
    Schema for updating an existing review.
    
    Only the review owner can update their review.
    
    Attributes:
        rating: Updated star rating (1-5)
        comment: Updated review text (1-500 characters)
    
    Validation:
        - Same validations as ReviewRequest
    """
    rating: int = Field(..., ge=1, le=5, description="Rating must be between 1 and 5")
    comment: str = Field(..., min_length=1, max_length=500, description="Comment must be between 1 and 500 characters")

    @field_validator('comment')
    @classmethod
    def validate_comment(cls, v):
        """Ensure comment contains meaningful content."""
        if v and v.strip() == "":
            raise ValueError("Comment cannot be empty or only whitespace")
        return v.strip()


class FlagReviewRequest(BaseModel):
    """
    Schema for flagging a review (moderation).
    
    Used by admins/moderators to mark inappropriate content.
    
    Attributes:
        reason: Explanation for flagging (1-200 characters)
    
    Validation:
        - Reason must not be empty or whitespace only
    
    Examples:
        - "Contains inappropriate language"
        - "Spam or off-topic content"
        - "Harassment or personal attack"
    """
    reason: str = Field(..., min_length=1, max_length=200, description="Reason for flagging")

    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v):
        """Ensure reason is meaningful."""
        if v and v.strip() == "":
            raise ValueError("Reason cannot be empty or only whitespace")
        return v.strip()


class ReviewResponse(BaseModel):
    """
    Schema for review data in API responses.
    
    Attributes:
        id: Review ID
        room_id: Room being reviewed
        room_name: Name of the room
        user_id: User who created the review
        username: Username of reviewer
        rating: Star rating (1-5)
        comment: Review text
        is_flagged: Whether review is flagged for moderation
        flagged_reason: Reason if flagged (optional)
        created_at: When review was created
        updated_at: When review was last modified
    """
    id: str
    room_id: str
    room_name: str
    user_id: str
    username: str
    rating: int
    comment: str
    is_flagged: bool
    flagged_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    """
    Schema for list of reviews in API responses.
    
    Used by GET /api/v1/reviews/{room_id} endpoint.
    
    Attributes:
        reviews: Array of review objects
        total: Total number of reviews
        average_rating: Calculated average of all ratings (optional)
    
    Business Logic:
        - Average rating is calculated server-side
        - Rounds to 2 decimal places
        - Null if no reviews exist
    """
    reviews: list[ReviewResponse]
    total: int
    average_rating: Optional[float] = None