import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.db.models import Application, Candidate, IngestJob, JobProfile, Mail, Resume, ScoringJob
from app.services.dedupe_service import dedupe_service
from app.services.nvite_parser import nvite_parser
from app.services.resume_service import resume_service

logger = logging.getLogger(__name__)


class IngestWorker:
    """
    Background worker that dequeues raw emails from ingest_jobs,
    executes NVite parsing, deduplicates candidate records,
    stores candidates and applications, and triggers scoring jobs
    ONLY IF active JDs already exist.
    """

    def __init__(self):
        self.is_running = False

    async def run_loop(self):
        self.is_running = True
        settings = get_settings()
        logger.info("IngestWorker background loop started.")
        while self.is_running:
            try:
                processed = await self.process_next_job()
                if not processed:
                    await asyncio.sleep(settings.queue_poll_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Unexpected error in IngestWorker loop: %s", e, exc_info=True)
                await asyncio.sleep(settings.queue_poll_interval_seconds)
        logger.info("IngestWorker background loop stopped.")

    def stop(self):
        self.is_running = False

    async def process_next_job(self) -> bool:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            # Transactional claim: FOR UPDATE SKIP LOCKED
            q_job = (
                select(IngestJob)
                .where(IngestJob.status == "queued", IngestJob.next_attempt_at <= now)
                .order_by(IngestJob.queued_at.asc())
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
                await self._process_job_record(db, job)
                job.status = "done"
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()
                return True
            except Exception as exc:
                logger.error("IngestJob %s failed on attempt %d: %s", job.id, job.attempts, exc, exc_info=True)
                settings = get_settings()
                job.last_error = str(exc)
                if job.attempts >= settings.max_job_attempts:
                    job.status = "failed"
                    job.finished_at = datetime.now(timezone.utc)
                else:
                    job.status = "queued"
                    # Exponential backoff: 5s, 20s, 60s
                    backoff_secs = 5 * (2 ** (job.attempts - 1))
                    job.next_attempt_at = datetime.now(timezone.utc) + asyncio.timedelta(seconds=backoff_secs)
                await db.commit()
                return True

    async def _process_job_record(self, db: AsyncSession, job: IngestJob) -> None:
        q_mail = select(Mail).where(Mail.id == job.mail_id)
        mail = (await db.execute(q_mail)).scalars().first()
        if not mail:
            raise ValueError(f"Mail {job.mail_id} not found")

        # 1. Parse with NVite parser
        parsed = nvite_parser.parse(
            html_content=mail.raw_body_html,
            text_content=mail.raw_body_text,
            subject=mail.subject,
        )

        if not parsed.is_recognized:
            mail.status = "needs_review"
            mail.error = "Unrecognized email format or missing candidate identity."
            await db.commit()
            return

        # 2. Check for deduplication
        existing_cand, match_reason = await dedupe_service.find_existing_candidate(
            db,
            email=parsed.email,
            phone=parsed.phone,
            full_name=parsed.full_name,
        )

        if existing_cand:
            candidate = existing_cand
            candidate.last_seen_at = mail.received_at
            # Enrich skills and details if more data present
            if parsed.skills:
                combined_skills = list(set(candidate.skills + parsed.skills))
                candidate.skills = combined_skills
            if not candidate.current_company and parsed.current_company:
                candidate.current_company = parsed.current_company
            if not candidate.headline and parsed.headline:
                candidate.headline = parsed.headline
            if candidate.experience_years is None and parsed.experience_years is not None:
                candidate.experience_years = parsed.experience_years
            logger.info("Ingest: Matched existing candidate %s via %s", candidate.id, match_reason)
        else:
            candidate = Candidate(
                full_name=parsed.full_name,
                email=parsed.email,
                phone=parsed.phone,
                headline=parsed.headline,
                current_company=parsed.current_company,
                experience_years=parsed.experience_years,
                current_ctc_lpa=parsed.current_ctc_lpa,
                notice_raw=parsed.notice_raw,
                notice_days_max=parsed.notice_days_max,
                location=parsed.location,
                preferred_locations=parsed.preferred_locations,
                skills=parsed.skills,
                education=parsed.education,
                first_seen_at=mail.received_at,
                last_seen_at=mail.received_at,
            )
            db.add(candidate)
            await db.flush()
            logger.info("Ingest: Created new candidate %s (%s)", candidate.id, candidate.full_name)

        # 3. Create Application
        q_app_exists = select(Application).where(
            Application.candidate_id == candidate.id,
            Application.mail_id == mail.id,
        )
        if not (await db.execute(q_app_exists)).scalars().first():
            app_record = Application(
                candidate_id=candidate.id,
                mail_id=mail.id,
                job_title=parsed.job_title or mail.subject or "Software Engineer",
                job_locations=parsed.preferred_locations,
                expected_ctc_lpa=parsed.expected_ctc_lpa,
                answers=parsed.answers,
                received_at=mail.received_at,
            )
            db.add(app_record)

        # 4. Check for fuzzy duplicates to flag
        await dedupe_service.check_and_flag_fuzzy_duplicates(db, candidate)

        mail.status = "parsed"
        await db.commit()

        # 5. Enqueue scoring ONLY if active JDs exist (R5 rule)
        q_active_jds = select(JobProfile).where(JobProfile.status == "active")
        active_jds = (await db.execute(q_active_jds)).scalars().all()
        for jd in active_jds:
            raw_hash_input = f"{jd.content_hash}:{candidate.id}"
            input_hash = hashlib.sha256(raw_hash_input.encode("utf-8")).hexdigest()
            q_sj_exists = select(ScoringJob).where(
                ScoringJob.job_profile_id == jd.id,
                ScoringJob.candidate_id == candidate.id,
                ScoringJob.input_hash == input_hash,
            )
            if not (await db.execute(q_sj_exists)).scalars().first():
                scoring_job = ScoringJob(
                    job_profile_id=jd.id,
                    candidate_id=candidate.id,
                    input_hash=input_hash,
                    status="queued",
                )
                db.add(scoring_job)

        await db.commit()


ingest_worker = IngestWorker()
