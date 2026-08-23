"""v1 API router aggregation."""

from fastapi import APIRouter

from app.api.v1 import auth, system_design

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(system_design.router)
