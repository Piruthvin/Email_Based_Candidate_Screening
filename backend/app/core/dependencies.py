import hashlib
import json
import logging
from typing import Any, Dict, Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog

logger = logging.getLogger(__name__)


async def audit_tool_call(
    db: AsyncSession,
    tool_name: str,
    request: Request,
    payload: Optional[Dict[str, Any]] = None,
    status: str = "success",
    error: Optional[str] = None,
    user_id: str = "anonymous",
) -> None:
    """
    Records an entry in the audit_log table for tracking agent tool calls.
    """
    try:
        payload_str = json.dumps(payload or {}, default=str, sort_keys=True)
        args_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        log_entry = AuditLog(
            user_id=user_id,
            tool=tool_name,
            args_hash=args_hash,
            request_body=payload,
            status=status,
            error=error,
        )
        db.add(log_entry)
        await db.commit()
    except Exception as exc:
        logger.warning("Failed to record audit log entry for tool %s: %s", tool_name, exc)
