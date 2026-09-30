"""
FastAPI Application Entry Point for AI Voice Customer Support Agent.
"""

from contextlib import asynccontextmanager
import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db, SessionLocal
from app import crud
from app.routers import voice_router, crm_router
from app.utils.logger import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle management.
    """
    logger.info("==================================================================")
    logger.info(f"Starting {settings.APP_NAME} (env: {settings.APP_ENV})")
    logger.info("==================================================================")

    # 1. Initialize SQLite Database Schema
    init_db()

    # 2. Seed initial mock customers & tickets if database is fresh
    db = SessionLocal()
    try:
        crud.seed_initial_data(db)
    except Exception as e:
        logger.error(f"Error during initial data seed: {e}")
    finally:
        db.close()

    # 3. Log external service configuration statuses
    if settings.is_deepseek_configured:
        logger.info(f"DeepSeek LLM: CONFIGURED (Model: {settings.DEEPSEEK_MODEL}, URL: {settings.DEEPSEEK_BASE_URL})")
    else:
        logger.warning("DeepSeek LLM: NOT CONFIGURED (Running in smart fallback mock mode). Set DEEPSEEK_API_KEY in .env")

    if settings.is_twilio_configured:
        logger.info(f"Twilio Voice: CONFIGURED (Phone: {settings.TWILIO_PHONE_NUMBER})")
    else:
        logger.info("Twilio Voice: NOT CONFIGURED (For live calls, set TWILIO credentials. Webhook testing works locally).")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")


# Create FastAPI application
app = FastAPI(
    title="AI Voice Customer Support Agent",
    description="Production-style MVP for AI Voice Customer Support powered by Twilio, DeepSeek, and FastAPI.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(f"HTTP {request.method} {request.url.path} -> Status {response.status_code} ({duration_ms}ms)")
    return response


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your request.",
            "path": request.url.path,
        },
    )


# Include Routers
app.include_router(voice_router)
app.include_router(crm_router)


# Root Health & Info Endpoints
@app.get("/", tags=["General"])
def root():
    """Application welcome and service status overview."""
    return {
        "service": settings.APP_NAME,
        "version": "0.1.0",
        "status": "healthy",
        "endpoints": {
            "twilio_voice_webhook": "POST /voice",
            "twilio_process_call": "POST /process-call",
            "voice_simulation": "POST /voice/simulate",
            "crm_customers": "GET /api/customers",
            "crm_tickets": "GET /api/tickets",
            "crm_call_summaries": "GET /api/call-summaries",
            "api_documentation": "/docs"
        },
        "integrations": {
            "deepseek_configured": settings.is_deepseek_configured,
            "twilio_configured": settings.is_twilio_configured,
        }
    }


@app.get("/health", tags=["General"])
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
