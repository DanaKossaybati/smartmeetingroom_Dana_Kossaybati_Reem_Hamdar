"""
Routes package initializer.

This file combines sub-routers and re-applies the original global
prefix and tags so main.py can continue to do:

    from routes import router as users_router
    app.include_router(users_router)

Author: Dana Kossaybati
"""
from fastapi import APIRouter
from .registration import router as registration_router
from .auth_login import router as auth_login_router
from .profile import router as profile_router
from .admin import router as admin_router

# Create router with the SAME prefix/tags as the original monolithic file
router = APIRouter(
    prefix="/api/users",      # All routes will start with /api/users
    tags=["users"]            # Groups endpoints in auto-generated docs
)

# Mount feature routers under the same global prefix
router.include_router(registration_router)
router.include_router(auth_login_router)
router.include_router(profile_router)
router.include_router(admin_router)
