import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import structlog
from core.config import settings
from core.rate_limit import RateLimitMiddleware, DEFAULT_CONFIG
from core.telemetry import init_telemetry, instrument_fastapi

logger = structlog.get_logger()


def create_app() -> FastAPI:
    init_telemetry("omnirag-api")
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    instrument_fastapi(app)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RateLimitMiddleware, config=DEFAULT_CONFIG)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start_time
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            duration=duration,
            status=response.status_code,
        )
        return response

    @app.get("/v1/health")
    async def health_check():
        return {"status": "ok", "timestamp": time.time()}

    from apps.api.routers import documents, query, auth, analytics, collections, feedback, retrieval, api_keys

    app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
    app.include_router(documents.router, prefix=settings.API_V1_STR, tags=["documents"])
    app.include_router(query.router, prefix=settings.API_V1_STR, tags=["query"])
    app.include_router(retrieval.router, prefix=settings.API_V1_STR, tags=["retrieval"])
    app.include_router(analytics.router, prefix=settings.API_V1_STR, tags=["analytics"])
    app.include_router(collections.router, prefix=settings.API_V1_STR, tags=["collections"])
    app.include_router(feedback.router, prefix=settings.API_V1_STR, tags=["feedback"])
    app.include_router(api_keys.router, prefix=settings.API_V1_STR, tags=["api-keys"])

    return app


app = create_app()