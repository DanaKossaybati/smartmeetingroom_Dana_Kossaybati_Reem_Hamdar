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
    Verify user has admin or moderator role.
    
    Helper function to enforce role-based access control for
    review moderation operations.
    
    Args:
        user_id_role: Dictionary containing 'user_id' and 'role' keys
    
    Raises:
        HTTPException: 403 if user lacks required permissions
    """
    user_id=user_id_role['user_id']
    user_role=user_id_role['role']

    if user_role not in [UserRole.admin.value,UserRole.moderator.value] or user_id is  None:
        raise HTTPException(status_code=403,detail="Not authorized to perform this action")

@router.post("/create", status_code=201)
async def create_review(
    request: ReviewRequest,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """
    Create a new review for a room.
    
    Regular users can create reviews. Users can only review
    each room once.
    
    Args:
        request: Review data (room_id, rating, comment)
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        None on success
    
    Raises:
        HTTPException: 403 if unauthorized, 404 if room not found,
                      400 if user already reviewed this room
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

@router.put("{review_id}",status_code=204)
async def update_review(
    review_id: int,
    request: ReviewUpdateRequest,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """
    Update an existing review.
    
    Only the review author can update their own review.
    
    Args:
        review_id: ID of the review to update
        request: Updated review data (rating, comment)
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        None on success
    
    Raises:
        HTTPException: 403 if unauthorized or not author,
                      404 if review not found
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

@router.delete("/{review_id}", status_code=204)
async def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """
    Delete a review.
    
    Only the review author can delete their own review.
    
    Args:
        review_id: ID of the review to delete
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        None on success
    
    Raises:
        HTTPException: 403 if unauthorized or not author,
                      404 if review not found
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


@router.get("/flagged", response_model=ReviewListResponse, status_code=200)
async def get_flagged_reviews(
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """
    Get all flagged reviews.
    
    Requires admin or moderator role.
    Returns only reviews marked as flagged for moderation.
    Results are cached per user for 5 minutes.
    
    Args:
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        ReviewListResponse: List of flagged reviews with total count
    
    Raises:
        HTTPException: 403 if unauthorized
    
    Caching:
        - Cache key: all_flagged_reviews:{user_id}
        - TTL: 300 seconds (5 minutes)
    """
    # Get all flagged reviews
    check_admin_moderator_role(user_id_role)
    user_id = user_id_role['user_id']

    cached_reviews = await cache.get(f"all_flagged_reviews:{user_id}")
    if cached_reviews:
        reviews_data = cached_reviews
    else:
        reviews = db.query(Review).options(
            joinedload(Review.room),
            joinedload(Review.user)
        ).filter(Review.is_flagged == True).all()
        
        # Serialize reviews to dictionaries for caching
        reviews_data = [
            {
                "id": review.id,
                "room_id": review.room_id,
                "room_name": review.room.name,
                "user_id": review.user_id,
                "username": review.user.username,
                "rating": review.rating,
                "comment": review.comment,
                "is_flagged": review.is_flagged,
                "flagged_reason": review.flagged_reason,
                "created_at": review.created_at.isoformat() if review.created_at else None,
                "updated_at": review.updated_at.isoformat() if review.updated_at else None
            }
            for review in reviews
        ]
        await cache.set(f"all_flagged_reviews:{user_id}", reviews_data, ttl=300)
    
    review_responses = [
        ReviewResponse(**review_dict)
        for review_dict in reviews_data
    ]
    
    return ReviewListResponse(
        reviews=review_responses,
        total=len(reviews_data),
        average_rating=None
    )


@router.get("/", response_model=ReviewListResponse, status_code=200)
async def get_all_reviews(
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """
    Get all reviews in the system.
    
    Returns all reviews regardless of flag status.
    Results are cached per user for 5 minutes.
    
    Args:
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        ReviewListResponse: List of all reviews with total count
    
    Caching:
        - Cache key: all_reviews:{user_id}
        - TTL: 300 seconds (5 minutes)
    """
    # Get all reviews
    #check_admin_moderator_role(user_id_role)
    
    user_id = user_id_role['user_id']
    
    cached_reviews = await cache.get(f"all_reviews:{user_id}")
    if cached_reviews:
        reviews_data = cached_reviews
    else:
        reviews = db.query(Review).options(
            joinedload(Review.room),
            joinedload(Review.user)
        ).all()
        
        # Serialize reviews to dictionaries for caching
        reviews_data = [
            {
                "id": review.id,
                "room_id": review.room_id,
                "room_name": review.room.name,
                "user_id": review.user_id,
                "username": review.user.username,
                "rating": review.rating,
                "comment": review.comment,
                "is_flagged": review.is_flagged,
                "flagged_reason": review.flagged_reason,
                "created_at": review.created_at.isoformat() if review.created_at else None,
                "updated_at": review.updated_at.isoformat() if review.updated_at else None
            }
            for review in reviews
        ]
        await cache.set(f"all_reviews:{user_id}", reviews_data, ttl=300)
    
    review_responses = [
        ReviewResponse(**review_dict)
        for review_dict in reviews_data
    ]
    
    return ReviewListResponse(
        reviews=review_responses,
        total=len(reviews_data),
        average_rating=None
    )


@router.get("/{room_id}", response_model=ReviewListResponse, status_code=200)
async def get_room_reviews(
    room_id: int,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user)
):
    """
    Get all reviews for a specific room.
    
    Returns reviews with calculated average rating.
    Results are cached per user for 5 minutes.
    
    Args:
        room_id: ID of the room to get reviews for
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        ReviewListResponse: List of reviews with total count and average rating
    
    Raises:
        HTTPException: 404 if room not found
    
    Caching:
        - Cache key: review:{room_id}:{user_id}
        - TTL: 300 seconds (5 minutes)
    """
    user_id = user_id_role['user_id']

    cached_reviews = await cache.get(f"review:{room_id}:{user_id}")
    if cached_reviews:
        reviews_data = cached_reviews
    else:
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
    
        reviews = db.query(Review).options(
            joinedload(Review.room),
            joinedload(Review.user)
        ).filter(Review.room_id == room_id).all()
        
        # Serialize reviews to dictionaries for caching
        reviews_data = [
            {
                "id": review.id,
                "room_id": review.room_id,
                "room_name": review.room.name,
                "user_id": review.user_id,
                "username": review.user.username,
                "rating": review.rating,
                "comment": review.comment,
                "is_flagged": review.is_flagged,
                "flagged_reason": review.flagged_reason,
                "created_at": review.created_at.isoformat() if review.created_at else None,
                "updated_at": review.updated_at.isoformat() if review.updated_at else None
            }
            for review in reviews
        ]
        await cache.set(f"review:{room_id}:{user_id}", reviews_data, ttl=300)

    average_rating = None
    if reviews_data:
        total_rating = sum(review["rating"] for review in reviews_data)
        average_rating = round(total_rating / len(reviews_data), 2)
    
    review_responses = [
        ReviewResponse(**review_dict)
        for review_dict in reviews_data
    ]
    
    return ReviewListResponse(
        reviews=review_responses,
        total=len(reviews_data),
        average_rating=average_rating
    )


@router.post("/{review_id}/flag",status_code=204)
async def flag_review(
    review_id: int,
    request: FlagReviewRequest,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """
    Flag a review as inappropriate (moderation).
    
    Requires admin or moderator role.
    Adds a flag with a reason for moderation tracking.
    
    Args:
        review_id: ID of the review to flag
        request: Flag reason data
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        None on success
    
    Raises:
        HTTPException: 403 if unauthorized, 404 if review not found
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


@router.post("/{review_id}/unflag",  status_code=204)
async def unflag_review(
    review_id: int,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """
    Unflag a review (remove moderation flag).
    
    Requires admin or moderator role.
    Removes the flag and clears the flag reason.
    
    Args:
        review_id: ID of the review to unflag
        db: Database session
        user_id_role: Current user authentication info
    
    Returns:
        None on success
    
    Raises:
        HTTPException: 403 if unauthorized, 404 if review not found
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