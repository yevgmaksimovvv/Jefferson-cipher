from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.rate_limit import RateLimiterUnavailable, RateLimitExceeded
from app.core.request_id import RequestIdMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.web.routes import router as web_router

settings = get_settings()
WEB_STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"


app = FastAPI(
    title="Jefferson Cipher Service",
    version="0.1.0",
    description=(
        "Jefferson cipher API.\n\n"
        "- persisted disk sets\n"
        "- JWT auth + refresh tokens\n"
        "- rate limiting\n"
        "- readiness endpoint"
    ),
    openapi_tags=[
        {
            "name": "health",
            "description": "Liveness and readiness probes.",
        },
        {
            "name": "auth",
            "description": "JWT registration, login, refresh, and logout.",
        },
        {
            "name": "users",
            "description": "Current authenticated user.",
        },
        {
            "name": "cipher",
            "description": "Stateless cipher operations and disk-set-backed ciphering.",
        },
        {
            "name": "disk-sets",
            "description": "Persisted disk-set CRUD and listing.",
        },
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory=WEB_STATIC_DIR), name="static")


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    headers = {}
    if exc.retry_after is not None:
        headers["Retry-After"] = str(exc.retry_after)
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded",
            }
        },
        headers=headers or None,
    )


@app.exception_handler(RateLimiterUnavailable)
async def rate_limiter_unavailable_handler(
    request: Request, exc: RateLimiterUnavailable
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "RATE_LIMITER_UNAVAILABLE",
                "message": "Rate limiter unavailable",
            }
        },
    )


app.include_router(api_v1_router)
app.include_router(web_router)

_OPTIONAL_AUTH_OPENAPI_PATHS = {
    "/api/v1/disk-sets": {"get"},
    "/api/v1/disk-sets/{disk_set_id}": {"get"},
    "/api/v1/cipher/encrypt/from-disk-set": {"post"},
    "/api/v1/cipher/decrypt/from-disk-set": {"post"},
}


def custom_openapi() -> dict:
    if app.openapi_schema is not None:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    for path, methods in _OPTIONAL_AUTH_OPENAPI_PATHS.items():
        for method in methods:
            schema["paths"][path][method].pop("security", None)

    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
