from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.rate_limit import RateLimiterUnavailable, RateLimitExceeded
from app.core.request_id import RequestIdMiddleware
from app.core.security_headers import SecurityHeadersMiddleware

settings = get_settings()


app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


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
