import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.db.models import Score, ScoringJob
from app.services.scoring_pipeline import scoring_pipeline

logger = logging.getLogger(__name__)


class ScoringWorker:
    """
    Background worker that dequeues candidate evaluation requests from scoring_jobs,
    respecting priority ordering (best details score first), circuit breaker thresholds,
    and daily scoring budgets.
    """

    def __init__(self):
        self.is_running = False
        self.consecutive_failures = 0
        self.circuit_breaker_tripped_until: Optional[datetime] = None

    async def run_loop(self):
        self.is_running = True
        settings = get_settings()
        logger.info("ScoringWorker background loop started.")
        while self.is_running:
            try:
                # Check circuit breaker
                now = datetime.now(timezone.utc)
                if self.circuit_breaker_tripped_until and now < self.circuit_breaker_tripped_until:
                    wait_sec = (self.circuit_breaker_tripped_until - now).total_seconds()
                    logger.warning("ScoringWorker circuit breaker active. Pausing for %.1fs...", wait_sec)
                    await asyncio.sleep(min(10.0, wait_sec))
                    continue
                else:
                    self.circuit_breaker_tripped_until = None

                processed = await self.process_next_job()
                if not processed:
                    await asyncio.sleep(settings.queue_poll_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Unexpected error in ScoringWorker loop: %s", e, exc_info=True)
                await asyncio.sleep(settings.queue_poll_interval_seconds)
        logger.info("ScoringWorker background loop stopped.")

    def stop(self):
        self.is_running = False

    async def process_next_job(self) -> bool:
        settings = get_settings()
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)

            # Check daily budget cap
            today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
            q_today_scores = select(func.count()).select_from(Score).where(Score.scored_at >= today_start)
            scored_today = (await db.execute(q_today_scores)).scalar_one()
            if scored_today >= settings.daily_scoring_budget:
                logger.warning("Daily scoring budget cap reached (%d/%d). Scoring paused.", scored_today, settings.daily_scoring_budget)
                return False

            # Transactional claim: FOR UPDATE SKIP LOCKED ordered by priority DESC, queued_at ASC
            q_job = (
                select(ScoringJob)
                .where(ScoringJob.status == "queued", ScoringJob.next_attempt_at <= now)
                .order_by(ScoringJob.priority.desc(), ScoringJob.queued_at.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            job = (await db.execute(q_job)).scalars().first()
            if not job:
                return False

            job.status = "running"
            job.attempts += 1
            await db.commit()

            try:
                await scoring_pipeline.score_candidate(
                    db=db,
                    job_profile_id=str(job.job_profile_id),
                    candidate_id=str(job.candidate_id),
                )
                job.status = "done"
                job.finished_at = datetime.now(timezone.utc)
                self.consecutive_failures = 0
                await db.commit()
                return True

            except Exception as exc:
                self.consecutive_failures += 1
                logger.error("ScoringJob %s failed on attempt %d: %s", job.id, job.attempts, exc, exc_info=True)
                job.last_error = str(exc)

                # Check circuit breaker threshold
                if self.consecutive_failures >= settings.circuit_breaker_failures:
                    logger.error(
                        "ScoringWorker tripped circuit breaker after %d consecutive failures. Cooling off for %ds.",
                        self.consecutive_failures,
                        settings.circuit_breaker_reset_seconds,
                    )
                    self.circuit_breaker_tripped_until = datetime.now(timezone.utc) + timedelta(
                        seconds=settings.circuit_breaker_reset_seconds
                    )

                if job.attempts >= settings.max_job_attempts:
                    job.status = "failed"
                    job.finished_at = datetime.now(timezone.utc)
                else:
                    job.status = "queued"
                    backoff = 5 * (2 ** (job.attempts - 1))
                    job.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)

                await db.commit()
                return True


scoring_worker = ScoringWorker()
