import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1.reports import router as reports_router
from app.api.v1.tools import router as tools_router
from app.core.config import get_settings
from app.workers.ingest_worker import ingest_worker
from app.workers.scoring_worker import scoring_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("talentpool")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting %s (%s mode)...", settings.app_name, settings.app_env)
    logger.info("Scoring Agent connectivity mode: %s", settings.scoring_agent_mode)
    if not settings.is_graph_configured:
        logger.warning("Microsoft Graph credentials not configured. Mailbox sync will operate in safe no-op mode.")

    # Ensure tmp directories exist
    os.makedirs("tmp/reports", exist_ok=True)

    # Start background worker loops
    ingest_task = asyncio.create_task(ingest_worker.run_loop())
    scoring_task = asyncio.create_task(scoring_worker.run_loop())

    yield

    logger.info("Shutting down background workers...")
    ingest_worker.stop()
    scoring_worker.stop()
    ingest_task.cancel()
    scoring_task.cancel()
    try:
        await asyncio.gather(ingest_task, scoring_task, return_exceptions=True)
    except Exception:
        pass
    logger.info("Talent pool backend stopped.")


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Tool API and Ingestion Backend for the Hybrid Talent Pool Screening Agent",
    lifespan=lifespan,
)

# Wide-open CORS per override 5
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router)
app.include_router(tools_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_SERVER_ERROR", "detail": str(exc)},
    )
