import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import structlog
from core.config import settings

logger = structlog.get_logger()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    from apps.api.routers import documents, query, auth

    app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
    app.include_router(documents.router, prefix=settings.API_V1_STR, tags=["documents"])
    app.include_router(query.router, prefix=settings.API_V1_STR, tags=["query"])

    return app


app = create_app()