import base64
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import IngestJob, Mail, Resume, SyncRun

logger = logging.getLogger(__name__)


class GraphSyncService:
    """
    Microsoft Graph REST API Client for delta mailbox synchronization.
    Safely no-ops with clear log output when MS_* credentials are not configured.
    """

    async def sync_mailbox(self, db: AsyncSession, mailbox: Optional[str] = None, mode: str = "latest") -> SyncRun:
        settings = get_settings()
        target_mailbox = mailbox or settings.ms_mailbox_upn or "unconfigured@mailbox.local"

        sync_run = SyncRun(
            mailbox=target_mailbox,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(sync_run)
        await db.commit()
        await db.refresh(sync_run)

        if not settings.is_graph_configured:
            logger.warning(
                "Microsoft Graph sync is NOT configured (MS_TENANT_ID / MS_CLIENT_ID / MS_CLIENT_SECRET / MS_MAILBOX_UPN are empty). "
                "Sync run %s finished as graceful no-op.",
                sync_run.id,
            )
            sync_run.status = "success"
            sync_run.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return sync_run

        try:
            token = await self._acquire_token(settings)
            delta_link = await self._get_last_delta_link(db, target_mailbox)
            new_mails_count, latest_received, new_delta = await self._fetch_and_store_delta(
                db, token, target_mailbox, delta_link
            )

            sync_run.status = "success"
            sync_run.finished_at = datetime.now(timezone.utc)
            sync_run.new_mails = new_mails_count
            sync_run.last_mail_received_at = latest_received
            sync_run.delta_link = new_delta
            await db.commit()
            return sync_run

        except Exception as exc:
            logger.error("Microsoft Graph sync failed for %s: %s", target_mailbox, exc, exc_info=True)
            sync_run.status = "failed"
            sync_run.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return sync_run

    async def _acquire_token(self, settings) -> str:
        url = f"https://login.microsoftonline.com/{settings.ms_tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": settings.ms_client_id,
            "client_secret": settings.ms_client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, data=data)
            resp.raise_for_status()
            payload = resp.json()
            return payload["access_token"]

    async def _get_last_delta_link(self, db: AsyncSession, mailbox: str) -> Optional[str]:
        q = (
            select(SyncRun.delta_link)
            .where(SyncRun.mailbox == mailbox, SyncRun.status == "success", SyncRun.delta_link.is_not(None))
            .order_by(SyncRun.started_at.desc())
            .limit(1)
        )
        return (await db.execute(q)).scalars().first()

    async def _fetch_and_store_delta(
        self, db: AsyncSession, token: str, mailbox: str, delta_link: Optional[str]
    ) -> tuple[int, Optional[datetime], Optional[str]]:
        headers = {
            "Authorization": f"Bearer {token}",
            "Prefer": "odata.maxpagesize=50",
        }
        url = delta_link or f"https://graph.microsoft.com/v1.0/users/{mailbox}/mailFolders/Inbox/messages/delta?$select=id,receivedDateTime,subject,from,hasAttachments,body"

        new_mails = 0
        latest_received = None
        final_delta = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                messages = data.get("value", [])
                for msg in messages:
                    if "@removed" in msg:
                        continue  # Skipped deleted items

                    msg_id = msg.get("id")
                    # Check if already exists
                    q_exists = select(Mail).where(Mail.message_id == msg_id)
                    if (await db.execute(q_exists)).scalars().first():
                        continue

                    raw_received = msg.get("receivedDateTime")
                    received_dt = datetime.fromisoformat(raw_received.replace("Z", "+00:00")) if raw_received else datetime.now(timezone.utc)
                    if latest_received is None or received_dt > latest_received:
                        latest_received = received_dt

                    sender_email = (msg.get("from") or {}).get("emailAddress", {}).get("address")
                    subject = msg.get("subject")
                    body_dict = msg.get("body") or {}
                    body_content = body_dict.get("content", "")
                    content_type = body_dict.get("contentType", "text").lower()

                    html_body = body_content if "html" in content_type else None
                    text_body = body_content if "text" in content_type else None

                    mail_row = Mail(
                        message_id=msg_id,
                        received_at=received_dt,
                        sender=sender_email,
                        subject=subject,
                        source="naukri_nvite" if "naukri" in str(subject).lower() or "naukri" in str(sender_email).lower() else "unknown",
                        raw_body_html=html_body,
                        raw_body_text=text_body,
                        raw_headers=msg,
                        status="queued",
                    )
                    db.add(mail_row)
                    await db.flush()

                    # Enqueue in ingest_jobs
                    ingest_job = IngestJob(
                        mail_id=mail_row.id,
                        status="queued",
                        attempts=0,
                    )
                    db.add(ingest_job)
                    new_mails += 1

                if "@odata.nextLink" in data:
                    url = data["@odata.nextLink"]
                elif "@odata.deltaLink" in data:
                    final_delta = data["@odata.deltaLink"]
                    url = None
                else:
                    url = None

            await db.commit()

        return new_mails, latest_received, final_delta


graph_sync_service = GraphSyncService()
