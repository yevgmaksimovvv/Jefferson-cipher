from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.cipher import router as cipher_router
from app.api.v1.endpoints.disk_sets import router as disk_sets_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.users import router as users_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(cipher_router)
router.include_router(disk_sets_router)
router.include_router(health_router)
router.include_router(users_router)
