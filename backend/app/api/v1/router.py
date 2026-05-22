from fastapi import APIRouter

from app.api.v1.endpoints.cipher import router as cipher_router
from app.api.v1.endpoints.health import router as health_router

router = APIRouter(prefix="/api/v1")
router.include_router(cipher_router)
router.include_router(health_router)
