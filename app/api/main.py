import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response
import time

from config.settings import settings
from config.database import db_manager
from config.logging_config import setup_logging
from app.api.routes import calls, agents, queue, analytics, customers, webhooks

settings.validate_required_fields()


setup_logging()
logger = logging.getLogger(__name__)

request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting application...")
    
    try:
        await db_manager.connect()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise
    
    yield
    
    logger.info("Shutting down application...")
    await db_manager.disconnect()
    logger.info("Database disconnected")


app = FastAPI(
    title="Customer Service Voice Agent API",
    description="Production-ready API for AI-powered customer service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request timing and metrics"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    if settings.enable_metrics:
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(process_time)
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "path": request.url.path
        }
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "service": "Customer Service Voice Agent API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        pool = db_manager.pool
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )


@app.get("/metrics", tags=["Metrics"])
async def metrics():
    """Prometheus metrics endpoint"""
    if not settings.enable_metrics:
        return Response(content="Metrics disabled", status_code=404)
    
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )


app.include_router(calls.router, prefix="/api/v1", tags=["Calls"])
app.include_router(agents.router, prefix="/api/v1", tags=["Agents"])
app.include_router(queue.router, prefix="/api/v1", tags=["Queue"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
app.include_router(customers.router, prefix="/api/v1", tags=["Customers"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
