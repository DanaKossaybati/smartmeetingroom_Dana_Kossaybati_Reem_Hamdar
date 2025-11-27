from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class ReviewRequest(BaseModel):
    room_id: str
    rating: int = Field(..., ge=1, le=5, description="Rating must be between 1 and 5")
    comment: str = Field(..., min_length=1, max_length=500, description="Comment must be between 1 and 500 characters")

    @field_validator('comment')
    @classmethod
    def validate_comment(cls, v):
        if v and v.strip() == "":
            raise ValueError("Comment cannot be empty or only whitespace")
        return v.strip()


class ReviewUpdateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating must be between 1 and 5")
    comment: str = Field(..., min_length=1, max_length=500, description="Comment must be between 1 and 500 characters")

    @field_validator('comment')
    @classmethod
    def validate_comment(cls, v):
        if v and v.strip() == "":
            raise ValueError("Comment cannot be empty or only whitespace")
        return v.strip()


class FlagReviewRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=200, description="Reason for flagging")

    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v):
        if v and v.strip() == "":
            raise ValueError("Reason cannot be empty or only whitespace")
        return v.strip()


class ReviewResponse(BaseModel):
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
    reviews: list[ReviewResponse]
    total: int
    average_rating: Optional[float] = None