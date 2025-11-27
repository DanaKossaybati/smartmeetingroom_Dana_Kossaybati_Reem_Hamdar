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
    user_id=user_id_role['user_id']
    user_role=user_id_role['role']

    if user_role not in [UserRole.admin.value,UserRole.moderator.value] or user_id is not None:
        raise HTTPException(status_code=403,detail="Not authorized to perform this action")

@router.post("/create", status_code=201)
async def create_review(
    request: ReviewRequest,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
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
    review_id: str,
    request: ReviewUpdateRequest,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):

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
    review_id: str,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):

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


@router.get("/{room_id}", response_model=ReviewListResponse, status_code=200)
async def get_room_reviews(
    room_id: str,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user)
):
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


@router.post("/{review_id}/flag",status_code=204)
async def flag_review(
    review_id: str,
    request: FlagReviewRequest,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """Flag a review as inappropriate (moderation)"""

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
    review_id: str,
    db: Session = Depends(get_db),
        user_id_role: dict[str,str] = Depends(get_current_user),
):
    """Unflag a review (remove flag)"""
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