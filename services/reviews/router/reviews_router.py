"""
API route handlers for Reviews Service.
Handles review and rating operations for meeting rooms including
creation, updates, deletion, and moderation.

Routes are kept thin - they only handle HTTP concerns.
Business logic is delegated to appropriate layers.

Author: Reem Hamdar
"""
from aiocache import Cache
from aiocache.serializers import JsonSerializer
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from database import get_db
from auth import get_current_user
from enums import UserRole
from models import Review, Room
from review_schema import ReviewRequest, ReviewUpdateRequest, ReviewResponse, ReviewListResponse,FlagReviewRequest


router = APIRouter(
    prefix="/api/v1/reviews",
    tags=["reviews"],
)
cache=Cache(Cache.MEMORY,serializer=JsonSerializer())

def check_admin_moderator_role(user_id_role:dict[str,str]):
    """
    Verify user has admin or moderator role for moderation operations.
    
    Args:
        user_id_role: Dictionary containing user_id and role from JWT token
    
    Raises:
        HTTPException 403: If user lacks required permissions
    """
    user_id=user_id_role['user_id']
    user_role=user_id_role['role']

    if user_role not in [UserRole.admin.value,UserRole.moderator.value] or user_id is not None:
        raise HTTPException(status_code=403,detail="Not authorized to perform this action")

@router.post("/create", status_code=201, summary="Create a new review", description="Submit a review and rating for a room")
async def create_review(
    request: ReviewRequest,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """
    Create a new review for a meeting room.
    
    **Authorization:**
    - Requires User or Manager role
    - Each user can only review a room once
    
    **Request Body:**
    - room_id: UUID of the room being reviewed
    - rating: Star rating (1-5)
      - 1 = Poor
      - 2 = Fair
      - 3 = Good
      - 4 = Very Good
      - 5 = Excellent
    - comment: Review text (10-500 characters)
    
    **Validation:**
    - Room must exist
    - User cannot review the same room twice
    - Rating must be between 1 and 5
    
    **Returns:**
    - 201: Review created successfully
    - 400: User has already reviewed this room
    - 403: Unauthorized (not user/manager)
    - 404: Room not found
    - 422: Invalid rating or comment format
    """
    if user_id_role['role'] in [UserRole.user.value, UserRole.manager.value ]:
        raise HTTPException(status_code=403, detail="Only users can create reviews")
    room = db.query(Room).filter(Room.id == request.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    user_id=user_id_role['user_id']
    
    existing_review = db.query(Review).filter(
        Review.room_id == request.room_id,
        Review.user_id == user_id
    ).first()
    if existing_review:
        raise HTTPException(status_code=400, detail="You have already reviewed this room")  
    
    review = Review(
        room_id=request.room_id,
        user_id=user_id,
        rating=request.rating,
        comment=request.comment
    )
    
    db.add(review)
    db.commit()

    return None

@router.put("{review_id}",status_code=204, summary="Update a review", description="Modify an existing review (owner only)")
async def update_review(
    review_id: int,
    request: ReviewUpdateRequest,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """
    Update an existing review.
    
    **Authorization:**
    - Only the review author can update their review
    - Requires User or Manager role
    
    **Path Parameters:**
    - review_id: ID of the review to update
    
    **Request Body:**
    - rating: Updated star rating (1-5)
    - comment: Updated review text
    
    **Returns:**
    - 204: Review updated successfully
    - 403: Unauthorized (not review owner)
    - 404: Review not found
    - 422: Invalid data format
    """

    if user_id_role['role'] in [UserRole.user.value, UserRole.manager.value ]:
        raise HTTPException(status_code=403, detail="Only users can create reviews")
    
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Only the author can update their review
    if review.user_id != user_id_role['user_id']:
        raise HTTPException(status_code=403, detail="Not authorized to update this review")
    
    # Update review
    review.rating = request.rating
    review.comment = request.comment
    
    db.commit()
    
    # Load relationships for response
    
    
    return None

@router.delete("/{review_id}", status_code=204, summary="Delete a review", description="Remove a review (owner or admin only)")
async def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """
    Delete a review from the system.
    
    **Authorization:**
    - Review author can delete their own review
    - Admins can delete any review
    - Requires User, Manager, or Admin role
    
    **Path Parameters:**
    - review_id: ID of the review to delete
    
    **Behavior:**
    - Permanent deletion - cannot be undone
    
    **Returns:**
    - 204: Review deleted successfully
    - 403: Unauthorized (not review owner or admin)
    - 404: Review not found
    """

    if user_id_role['role'] in [UserRole.user.value, UserRole.manager.value ]:
        raise HTTPException(status_code=403, detail="Only users can create reviews")

    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Only the author can delete their review
    if review.user_id != user_id_role['user_id']:
        raise HTTPException(status_code=403, detail="Not authorized to delete this review")
    
    db.delete(review)
    db.commit()
    
    return None


@router.get("/{room_id}", response_model=ReviewListResponse, status_code=200, summary="Get room reviews", description="Retrieve all reviews for a specific room with average rating")
async def get_room_reviews(
    room_id: int,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user)
):
    """
    Get all reviews for a specific room.
    
    **Authorization:**
    - Requires authentication (any role)
    
    **Path Parameters:**
    - room_id: UUID of the room
    
    **Caching:**
    - Reviews cached for 5 minutes per user
    - Improves performance for repeated queries
    
    **Returns:**
    - 200: List of reviews with metadata
    - 401: Unauthorized (no valid token)
    - 404: Room not found
    
    **Response includes:**
    - List of all reviews (with user and room details)
    - Total review count
    - Average rating (calculated from all reviews)
    - Individual review details:
      - Review ID, rating, comment
      - User information (ID, username)
      - Room information (ID, name)
      - Flagged status and reason (if flagged)
      - Timestamps (created_at, updated_at)
    """
    user_id=user_id_role['user_id']

    cached_reviews= await cache.get(f"review:{user_id}")
    if cached_reviews:
        reviews = cached_reviews
    else:
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
    
        reviews = db.query(Review).options(
            joinedload(Review.room),
            joinedload(Review.user)
        ).filter(Review.room_id == room_id).all()
        await cache.set(f"review:{user_id}", reviews)

    average_rating = None
    if reviews:
        total_rating = sum(review.rating for review in reviews)
        average_rating = round(total_rating / len(reviews), 2)
    
    review_responses = [
        ReviewResponse(
            id=review.id,
            room_id=review.room_id,
            room_name=review.room.name,
            user_id=review.user_id,
            username=review.user.username,
            rating=review.rating,
            comment=review.comment,
            is_flagged=review.is_flagged,
            flagged_reason=review.flagged_reason,
            created_at=review.created_at,
            updated_at=review.updated_at
        )
        for review in reviews
    ]
    
    return ReviewListResponse(
        reviews=review_responses,
        total=len(reviews),
        average_rating=average_rating
    )


@router.post("/{review_id}/flag",status_code=204, summary="Flag a review", description="Mark a review as inappropriate for moderation (Admin/Moderator only)")
async def flag_review(
    review_id: int,
    request: FlagReviewRequest,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """
    Flag a review as inappropriate (moderation action).
    
    **Authorization:**
    - Requires Admin or Moderator role
    
    **Path Parameters:**
    - review_id: ID of the review to flag
    
    **Request Body:**
    - reason: Explanation for flagging (required)
      - Examples: "Inappropriate language", "Spam", "Off-topic"
    
    **Behavior:**
    - Marks review as flagged for moderator review
    - Does not delete the review
    - Flagged reviews may be hidden from public view
    
    **Returns:**
    - 204: Review flagged successfully
    - 403: Unauthorized (not admin/moderator)
    - 404: Review not found
    """

    check_admin_moderator_role(user_id_role)
    
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Flag the review
    review.is_flagged = True
    review.flagged_reason = request.reason
    
    db.commit()
    
   
    return None


@router.post("/{review_id}/unflag",  status_code=204, summary="Unflag a review", description="Remove inappropriate flag from a review (Admin/Moderator only)")
async def unflag_review(
    review_id: int,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """
    Unflag a review (remove inappropriate flag).
    
    **Authorization:**
    - Requires Admin or Moderator role
    
    **Path Parameters:**
    - review_id: ID of the review to unflag
    
    **Behavior:**
    - Removes flag from review
    - Clears the flagged_reason field
    - Review becomes visible again (if it was hidden)
    
    **Returns:**
    - 204: Review unflagged successfully
    - 403: Unauthorized (not admin/moderator)
    - 404: Review not found
    """
    check_admin_moderator_role(user_id_role)
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Unflag the review
    review.is_flagged = False
    review.flagged_reason = None
    
    db.commit()
    
 
    return None


@router.get("/flagged", response_model=ReviewListResponse, status_code=200)
async def get_flagged_reviews(
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    
    # Get all flagged reviews
    check_admin_moderator_role(user_id_role)
    user_id=user_id_role['user_id']

    cached_reviews= await cache.get(f"all_flagged_reviews:{user_id}")
    if cached_reviews:
        reviews = cached_reviews
    else:
        reviews = db.query(Review).options(
            joinedload(Review.room),
            joinedload(Review.user)
        ).filter(Review.is_flagged == True).all()
        await  cache.set(f"all_flagged_reviews:{user_id}", reviews)
    review_responses = [
        ReviewResponse(
            id=review.id,
            room_id=review.room_id,
            room_name=review.room.name,
            user_id=review.user_id,
            username=review.user.username,
            rating=review.rating,
            comment=review.comment,
            is_flagged=review.is_flagged,
            flagged_reason=review.flagged_reason,
            created_at=review.created_at,
            updated_at=review.updated_at
        )
        for review in reviews
    ]
    
    return ReviewListResponse(
        reviews=review_responses,
        total=len(reviews),
        average_rating=None
    )



@router.get("/", response_model=ReviewListResponse, status_code=200)
async def get_all_reviews(
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    
    # Get all reviews
    check_admin_moderator_role(user_id_role)
    
    user_id=user_id_role['user_id']
    
    cached_reviews= await cache.get(f"all_reviews:{user_id}")
    if cached_reviews:
        reviews = cached_reviews
    else:
        reviews = db.query(Review).options(
        joinedload(Review.room),
            joinedload(Review.user)
        ).all()
        await cache.set(f"all_reviews:{user_id}",reviews,ttl=60)
    
    review_responses = [
        ReviewResponse(
            id=review.id,
            room_id=review.room_id,
            room_name=review.room.name,
            user_id=review.user_id,
            username=review.user.username,
            rating=review.rating,
            comment=review.comment,
            is_flagged=review.is_flagged,
            flagged_reason=review.flagged_reason,
            created_at=review.created_at,
            updated_at=review.updated_at
        )
        for review in reviews
    ]
    
    return ReviewListResponse(
        reviews=review_responses,
        total=len(reviews),
        average_rating=None
    )