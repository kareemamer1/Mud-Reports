from fastapi import APIRouter

from backend.routers.items import router as items_router
from backend.routers.insights import router as insights_router

api_router = APIRouter()
api_router.include_router(items_router, prefix="/items", tags=["items"])
api_router.include_router(insights_router, prefix="/insights", tags=["insights"])
