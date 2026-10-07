from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness Probe")
async def health():
    return {"status": "ok", "service": "talentpool-backend"}


@router.get("/ready", summary="Readiness Probe")
async def ready(db: AsyncSession = Depends(get_db)):
    try:
        res = await db.execute(text("SELECT 1"))
        val = res.scalar()
        if val == 1:
            return {"status": "ready", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database_error": str(e)},
        )
    return {"status": "ready"}
