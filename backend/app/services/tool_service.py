import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import (
    Application,
    Candidate,
    DuplicateFlag,
    JobProfile,
    Mail,
    RankingResult,
    RankingRun,
    Resume,
    Score,
    ScoringJob,
    SyncRun,
)
from app.schemas.tools import (
    ActivateJobProfileResponse,
    CandidateDossierResponse,
    CandidateFilter,
    CandidateSummaryItem,
    DeactivateJobProfileResponse,
    DuplicateFlagItem,
    FindDuplicatesResponse,
    GenerateReportResponse,
    JobProfileSummaryItem,
    ListJobProfilesResponse,
    MergeCandidatesResponse,
    PoolStatsResponse,
    RankCandidatesResponse,
    RankedCandidateItem,
    SaveJobProfileResponse,
    ScoringStatusResponse,
    SearchCandidatesResponse,
    SyncMailboxResponse,
    SyncStatusResponse,
)
from app.services.graph_sync_service import graph_sync_service
from app.services.report_service import report_service

logger = logging.getLogger(__name__)


class ToolService:
    """
    Execution engine for the 12 Recruiter Agent tools.
    """

    # --- Tool 1: get_pool_stats ---
    async def get_pool_stats(self, db: AsyncSession) -> PoolStatsResponse:
        q_total_cand = select(func.count(Candidate.id)).where(Candidate.merged_into.is_(None))
        total_cand = (await db.execute(q_total_cand)).scalar_one()

        # Candidates with zero complete scores
        q_scored_cands = select(func.count(func.distinct(Score.candidate_id)))
        scored_cand_count = (await db.execute(q_scored_cands)).scalar_one()
        unscored_cand = max(0, total_cand - scored_cand_count)

        q_active_jds = select(func.count(JobProfile.id)).where(JobProfile.status == "active")
        active_jds = (await db.execute(q_active_jds)).scalar_one()

        q_last_mail = select(func.max(Mail.received_at))
        last_mail = (await db.execute(q_last_mail)).scalar_one()

        q_last_sync = select(func.max(SyncRun.finished_at)).where(SyncRun.status == "success")
        last_sync = (await db.execute(q_last_sync)).scalar_one()

        return PoolStatsResponse(
            total_candidates=total_cand,
            unscored_candidates=unscored_cand,
            active_jds_count=active_jds,
            last_mail_received_at=last_mail,
            last_sync_at=last_sync,
        )

    # --- Tool 2: sync_mailbox ---
    async def sync_mailbox(self, db: AsyncSession, mailbox: Optional[str] = None, mode: str = "latest") -> SyncMailboxResponse:
        sync_run = await graph_sync_service.sync_mailbox(db=db, mailbox=mailbox, mode=mode)
        return SyncMailboxResponse(
            job_id=str(sync_run.id),
            status=sync_run.status,
            mailbox=sync_run.mailbox,
        )

    # --- Tool 3: get_sync_status ---
    async def get_sync_status(self, db: AsyncSession, job_id: str) -> SyncStatusResponse:
        q = select(SyncRun).where(SyncRun.id == job_id)
        run = (await db.execute(q)).scalars().first()
        if not run:
            raise ValueError(f"Sync run {job_id} not found")

        return SyncStatusResponse(
            job_id=str(run.id),
            status=run.status,
            new_mails=run.new_mails,
            new_candidates=run.new_candidates,
            existing_candidates_new_application=run.existing_candidates_new_application,
            duplicate_flags=run.duplicate_flags,
            last_mail_received_at=run.last_mail_received_at,
            delta_link_present=bool(run.delta_link),
        )

    # --- Tool 3: list_job_profiles ---
    async def list_job_profiles(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ListJobProfilesResponse:
        query = select(JobProfile)
        if status:
            clean_status = status.lower().strip()
            query = query.where(JobProfile.status == clean_status)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar_one()

        query = query.order_by(JobProfile.created_at.desc()).limit(limit).offset(offset)
        profiles = (await db.execute(query)).scalars().all()

        items = []
        for jp in profiles:
            struct = jp.structured or {}
            min_exp = struct.get("experience_min_years")
            max_exp = struct.get("experience_max_years")
            items.append(
                JobProfileSummaryItem(
                    job_profile_id=str(jp.id),
                    title=jp.title,
                    status=jp.status,
                    version=jp.version,
                    content_hash=jp.content_hash,
                    must_have_skills=struct.get("must_have_skills") or [],
                    experience_min_years=float(min_exp) if min_exp is not None else None,
                    experience_max_years=float(max_exp) if max_exp is not None else None,
                    locations=struct.get("locations") or [],
                    created_at=jp.created_at,
                    confirmed_at=jp.confirmed_at,
                    confirmed_by=jp.confirmed_by,
                )
            )

        return ListJobProfilesResponse(job_profiles=items, total=total)

    # --- Tool 4: save_job_profile ---
    async def save_job_profile(
        self,
        db: AsyncSession,
        title: str,
        raw_text: str,
        structured: Dict[str, Any],
        parent_id: Optional[str] = None,
    ) -> SaveJobProfileResponse:
        # Canonical canonicalization for SHA-256 content hash
        canonical_json = json.dumps(structured, sort_keys=True)
        content_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        q_existing = select(JobProfile).where(JobProfile.content_hash == content_hash)
        existing = (await db.execute(q_existing)).scalars().first()
        if existing:
            return SaveJobProfileResponse(
                job_profile_id=str(existing.id),
                status=existing.status,
                title=existing.title,
                version=existing.version,
                content_hash=existing.content_hash,
                parsed_summary=existing.structured,
            )

        version = 1
        if parent_id:
            q_parent = select(JobProfile).where(JobProfile.id == parent_id)
            parent = (await db.execute(q_parent)).scalars().first()
            if parent:
                version = parent.version + 1

        new_jd = JobProfile(
            title=title,
            raw_text=raw_text,
            structured=structured,
            content_hash=content_hash,
            version=version,
            parent_id=uuid.UUID(parent_id) if parent_id else None,
            status="draft",
        )
        db.add(new_jd)
        await db.commit()
        await db.refresh(new_jd)

        return SaveJobProfileResponse(
            job_profile_id=str(new_jd.id),
            status=new_jd.status,
            title=new_jd.title,
            version=new_jd.version,
            content_hash=new_jd.content_hash,
            parsed_summary=new_jd.structured,
        )

    # --- Tool 5: activate_job_profile ---
    async def activate_job_profile(
        self,
        db: AsyncSession,
        job_profile_id: str,
        confirmed_by: Optional[str] = "recruiter",
        confirmed_changes: Optional[Dict[str, Any]] = None,
    ) -> ActivateJobProfileResponse:
        try:
            jd_uuid = uuid.UUID(str(job_profile_id))
        except (ValueError, TypeError):
            raise ValueError(f"INVALID_ID: Invalid UUID format for job_profile_id: '{job_profile_id}'")

        q = select(JobProfile).where(JobProfile.id == jd_uuid)
        jd = (await db.execute(q)).scalars().first()
        if not jd:
            raise ValueError(f"NOT_FOUND: JobProfile '{job_profile_id}' not found.")

        if jd.status == "active":
            raise ValueError(f"ALREADY_ACTIVE: Job profile '{job_profile_id}' is already active.")

        if jd.status not in ("draft", "inactive"):
            raise ValueError(f"INVALID_TRANSITION: Cannot activate job profile in '{jd.status}' status.")

        if confirmed_changes:
            merged_structured = dict(jd.structured)
            merged_structured.update(confirmed_changes)
            jd.structured = merged_structured
            canonical_json = json.dumps(merged_structured, sort_keys=True)
            jd.content_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        was_inactive = (jd.status == "inactive")
        jd.status = "active"
        jd.confirmed_by = confirmed_by or "recruiter"
        jd.confirmed_at = datetime.now(timezone.utc)
        await db.commit()

        # Bulk enqueue scoring jobs for all existing active candidates (R4 rule)
        q_cands = select(Candidate.id).where(Candidate.merged_into.is_(None))
        candidate_ids = (await db.execute(q_cands)).scalars().all()

        enqueued_count = 0
        for cid in candidate_ids:
            raw_hash_input = f"{jd.content_hash}:{cid}"
            input_hash = hashlib.sha256(raw_hash_input.encode("utf-8")).hexdigest()
            q_exists = select(ScoringJob).where(
                ScoringJob.job_profile_id == jd.id,
                ScoringJob.candidate_id == cid,
                ScoringJob.input_hash == input_hash,
            )
            if not (await db.execute(q_exists)).scalars().first():
                scoring_job = ScoringJob(
                    job_profile_id=jd.id,
                    candidate_id=cid,
                    input_hash=input_hash,
                    status="queued",
                )
                db.add(scoring_job)
                enqueued_count += 1

        await db.commit()
        msg = f"Job profile '{jd.title}' is now active. {enqueued_count} scoring jobs queued."
        if was_inactive:
            msg = f"Job profile '{jd.title}' reactivated. {enqueued_count} scoring jobs queued for unscored candidates."

        return ActivateJobProfileResponse(
            job_profile_id=str(jd.id),
            status="active",
            scoring_jobs_queued=enqueued_count,
            message=msg,
        )

    # --- Tool 6: deactivate_job_profile ---
    async def deactivate_job_profile(
        self,
        db: AsyncSession,
        job_profile_id: str,
        confirmed_by: Optional[str] = "recruiter",
        reason: Optional[str] = None,
    ) -> DeactivateJobProfileResponse:
        try:
            jd_uuid = uuid.UUID(str(job_profile_id))
        except (ValueError, TypeError):
            raise ValueError(f"INVALID_ID: Invalid UUID format for job_profile_id: '{job_profile_id}'")

        q = select(JobProfile).where(JobProfile.id == jd_uuid)
        jd = (await db.execute(q)).scalars().first()
        if not jd:
            raise ValueError(f"NOT_FOUND: JobProfile '{job_profile_id}' not found.")

        if jd.status == "inactive":
            raise ValueError(f"ALREADY_INACTIVE: Job profile '{job_profile_id}' is already inactive.")

        if jd.status != "active":
            raise ValueError(
                f"INVALID_TRANSITION: Cannot deactivate job profile in '{jd.status}' status. Only active job profiles can be deactivated."
            )

        now = datetime.now(timezone.utc)
        jd.status = "inactive"

        # Cancel pending/queued scoring jobs for this JD to preserve worker bandwidth and budget
        q_cancel = (
            update(ScoringJob)
            .where(
                ScoringJob.job_profile_id == jd.id,
                ScoringJob.status == "queued",
            )
            .values(
                status="cancelled",
                last_error=f"Cancelled upon JD deactivation by {confirmed_by or 'recruiter'}: {reason or 'No reason provided'}",
                finished_at=now,
            )
        )
        res_cancel = await db.execute(q_cancel)
        cancelled_count = res_cancel.rowcount or 0

        await db.commit()

        return DeactivateJobProfileResponse(
            job_profile_id=str(jd.id),
            status="inactive",
            cancelled_scoring_jobs=cancelled_count,
            deactivated_at=now,
            message=f"Job profile '{jd.title}' is now inactive. {cancelled_count} queued scoring jobs were cancelled. Historical scores and ranking runs are preserved.",
        )

    # --- Tool 6: get_scoring_status ---
    async def get_scoring_status(self, db: AsyncSession, job_profile_id: str) -> ScoringStatusResponse:
        q_jd = select(JobProfile).where(JobProfile.id == job_profile_id)
        jd = (await db.execute(q_jd)).scalars().first()
        if not jd:
            raise ValueError(f"JobProfile {job_profile_id} not found")

        q_jobs = select(ScoringJob.status, func.count(ScoringJob.id)).where(ScoringJob.job_profile_id == jd.id).group_by(ScoringJob.status)
        counts = dict((await db.execute(q_jobs)).all())

        queued = counts.get("queued", 0)
        running = counts.get("running", 0)
        complete = counts.get("done", 0)
        failed = counts.get("failed", 0)
        total = queued + running + complete + failed

        scored_pct = round((complete / max(1, total)) * 100.0, 1) if total > 0 else 0.0
        eta = "Complete" if (queued + running) == 0 else f"~{((queued + running) * 2)}s remaining"

        return ScoringStatusResponse(
            job_profile_id=str(jd.id),
            total_jobs=total,
            queued=queued,
            running=running,
            complete=complete,
            failed=failed,
            scored_pct=scored_pct,
            eta_hint=eta,
        )

    # --- Tool 7: search_candidates ---
    async def search_candidates(
        self,
        db: AsyncSession,
        filters: Optional[CandidateFilter] = None,
        sort_keys: Optional[List[str]] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> SearchCandidatesResponse:
        query = select(Candidate).where(Candidate.merged_into.is_(None))

        if filters:
            if filters.notice_days_max is not None:
                query = query.where(Candidate.notice_days_max <= filters.notice_days_max)
            if filters.experience_min_years is not None:
                query = query.where(Candidate.experience_years >= filters.experience_min_years)
            if filters.experience_max_years is not None:
                query = query.where(Candidate.experience_years <= filters.experience_max_years)
            if filters.location:
                query = query.where(
                    or_(
                        Candidate.location.ilike(f"%{filters.location}%"),
                        func.array_to_string(Candidate.preferred_locations, ",").ilike(f"%{filters.location}%"),
                    )
                )
            if filters.skills:
                for skill in filters.skills:
                    query = query.where(func.array_to_string(Candidate.skills, ",").ilike(f"%{skill}%"))
            if filters.received_after:
                query = query.where(Candidate.last_seen_at >= filters.received_after)

        # Count total
        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar_one()

        # Sort order
        query = query.order_by(Candidate.last_seen_at.desc()).limit(limit).offset(offset)
        candidates = (await db.execute(query)).scalars().all()

        items = [
            CandidateSummaryItem(
                candidate_id=str(c.id),
                full_name=c.full_name,
                email=c.email,
                phone=c.phone,
                headline=c.headline,
                current_company=c.current_company,
                experience_years=float(c.experience_years) if c.experience_years else None,
                current_ctc_lpa=float(c.current_ctc_lpa) if c.current_ctc_lpa else None,
                notice_days_max=c.notice_days_max,
                location=c.location,
                skills=c.skills or [],
                last_seen_at=c.last_seen_at,
            )
            for c in candidates
        ]

        return SearchCandidatesResponse(candidates=items, total=total)

    # --- Tool 8: get_candidate ---
    async def get_candidate(
        self,
        db: AsyncSession,
        candidate_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> CandidateDossierResponse:
        if candidate_id:
            q = select(Candidate).where(Candidate.id == candidate_id)
            c = (await db.execute(q)).scalars().first()
            if not c:
                raise ValueError(f"Candidate {candidate_id} not found")
            return await self._build_dossier(db, c)

        if name:
            clean_name = name.strip()
            q = select(Candidate).where(Candidate.full_name.ilike(f"%{clean_name}%"), Candidate.merged_into.is_(None))
            matches = (await db.execute(q)).scalars().all()
            if not matches:
                raise ValueError(f"No candidate matching name '{name}'")
            if len(matches) > 1:
                # Disambiguation needed!
                items = [
                    CandidateSummaryItem(
                        candidate_id=str(c.id),
                        full_name=c.full_name,
                        email=c.email,
                        phone=c.phone,
                        headline=c.headline,
                        current_company=c.current_company,
                        experience_years=float(c.experience_years) if c.experience_years else None,
                        current_ctc_lpa=float(c.current_ctc_lpa) if c.current_ctc_lpa else None,
                        notice_days_max=c.notice_days_max,
                        location=c.location,
                        skills=c.skills or [],
                        last_seen_at=c.last_seen_at,
                    )
                    for c in matches
                ]
                return CandidateDossierResponse(disambiguation=True, candidates=items)
            return await self._build_dossier(db, matches[0])

        raise ValueError("Either candidate_id or name must be provided")

    async def _build_dossier(self, db: AsyncSession, c: Candidate) -> CandidateDossierResponse:
        # Applications
        q_apps = select(Application).where(Application.candidate_id == c.id).order_by(Application.received_at.desc())
        apps = (await db.execute(q_apps)).scalars().all()
        app_list = [
            {
                "job_title": a.job_title,
                "received_at": a.received_at.isoformat(),
                "expected_ctc_lpa": float(a.expected_ctc_lpa) if a.expected_ctc_lpa else None,
                "answers": a.answers,
            }
            for a in apps
        ]

        # Scores
        q_scores = (
            select(Score, JobProfile.title)
            .join(JobProfile, JobProfile.id == Score.job_profile_id)
            .where(Score.candidate_id == c.id)
        )
        score_rows = (await db.execute(q_scores)).all()
        score_list = [
            {
                "job_title": title,
                "final_score": float(s.final_score),
                "details_score": float(s.details_score),
                "resume_score": float(s.resume_score) if s.resume_score is not None else None,
                "reason": s.reason,
                "missing_skills": s.missing_skills,
                "flags": s.flags,
            }
            for s, title in score_rows
        ]

        # Resume presence
        q_res = select(func.count(Resume.id)).where(Resume.candidate_id == c.id)
        has_resume = (await db.execute(q_res)).scalar_one() > 0

        return CandidateDossierResponse(
            disambiguation=False,
            candidate_id=str(c.id),
            full_name=c.full_name,
            email=c.email,
            phone=c.phone,
            headline=c.headline,
            current_company=c.current_company,
            experience_years=float(c.experience_years) if c.experience_years else None,
            current_ctc_lpa=float(c.current_ctc_lpa) if c.current_ctc_lpa else None,
            notice_raw=c.notice_raw,
            notice_days_max=c.notice_days_max,
            location=c.location,
            preferred_locations=c.preferred_locations or [],
            education=c.education,
            skills=c.skills or [],
            applications=app_list,
            scores=score_list,
            resume_available=has_resume,
        )

    # --- Tool 9: rank_candidates ---
    async def rank_candidates(
        self,
        db: AsyncSession,
        job_profile_id: str,
        top_n: int = 10,
        rank_by: str = "final",
        filters: Optional[Dict[str, Any]] = None,
        sort_keys: Optional[List[str]] = None,
    ) -> RankCandidatesResponse:
        # Check active JD
        q_jd = select(JobProfile).where(JobProfile.id == job_profile_id)
        jd = (await db.execute(q_jd)).scalars().first()
        if not jd or jd.status != "active":
            raise ValueError("JD_REQUIRED: No active Job Description found. A confirmed and active JD is required before ranking.")

        # Check scoring completion
        q_stats = await self.get_scoring_status(db, job_profile_id)

        # Base query joining scores and candidates
        query = (
            select(Score, Candidate)
            .join(Candidate, Candidate.id == Score.candidate_id)
            .where(
                Score.job_profile_id == jd.id,
                Candidate.merged_into.is_(None),
                Score.final_score.is_not(None),
            )
        )

        # Apply optional filters
        if filters:
            if filters.get("notice_days_max") is not None:
                query = query.where(Candidate.notice_days_max <= filters["notice_days_max"])
            if filters.get("experience_min_years") is not None:
                query = query.where(Candidate.experience_years >= filters["experience_min_years"])
            if filters.get("location"):
                query = query.where(Candidate.location.ilike(f"%{filters['location']}%"))

        # Sort strategy
        if rank_by == "resume":
            query = query.order_by(Score.resume_score.desc().nullslast(), Score.details_score.desc(), Candidate.id)
        elif rank_by == "details":
            query = query.order_by(Score.details_score.desc(), Score.final_score.desc(), Candidate.id)
        else:  # final
            query = query.order_by(Score.final_score.desc(), Score.details_score.desc(), Candidate.id)

        query = query.limit(top_n)
        results = (await db.execute(query)).all()

        if not results and q_stats.total_jobs == 0:
            raise ValueError("JD_REQUIRED: No candidates scored yet for this JD.")

        # Freeze ranking run
        run = RankingRun(
            job_profile_id=jd.id,
            rank_by=rank_by,
            top_n=top_n,
            filters=filters or {},
            sort_keys=sort_keys or [],
            scored_pct=q_stats.scored_pct,
            created_by="recruiter",
        )
        db.add(run)
        await db.flush()

        ranked_items = []
        for idx, (score_row, cand_row) in enumerate(results, start=1):
            r_res = RankingResult(
                run_id=run.id,
                rank_position=idx,
                candidate_id=cand_row.id,
                final_score=score_row.final_score,
                details_score=score_row.details_score,
                resume_score=score_row.resume_score,
                reason=score_row.reason,
                missing_skills=score_row.missing_skills or [],
            )
            db.add(r_res)

            ranked_items.append(
                RankedCandidateItem(
                    rank_position=idx,
                    candidate_id=str(cand_row.id),
                    full_name=cand_row.full_name,
                    final_score=float(score_row.final_score),
                    details_score=float(score_row.details_score),
                    resume_score=float(score_row.resume_score) if score_row.resume_score is not None else None,
                    reason=score_row.reason,
                    missing_skills=score_row.missing_skills or [],
                    notice_days_max=cand_row.notice_days_max,
                    experience_years=float(cand_row.experience_years) if cand_row.experience_years else None,
                    location=cand_row.location,
                )
            )

        await db.commit()

        return RankCandidatesResponse(
            run_id=str(run.id),
            job_profile_id=str(jd.id),
            rank_by=rank_by,
            top_n=top_n,
            scored_pct=q_stats.scored_pct,
            pending_count=q_stats.queued + q_stats.running,
            ranked=ranked_items,
        )

    # --- Tool 10: find_duplicates ---
    async def find_duplicates(self, db: AsyncSession, status: str = "pending") -> FindDuplicatesResponse:
        q = (
            select(DuplicateFlag, Candidate, Candidate)
            .join(Candidate, Candidate.id == DuplicateFlag.candidate_a)
            .where(DuplicateFlag.status == status)
            .order_by(DuplicateFlag.created_at.desc())
        )
        # Separate joins for candidate a and candidate b
        q = (
            select(DuplicateFlag)
            .where(DuplicateFlag.status == status)
            .order_by(DuplicateFlag.created_at.desc())
        )
        flags = (await db.execute(q)).scalars().all()

        items = []
        for f in flags:
            cand_a = (await db.execute(select(Candidate).where(Candidate.id == f.candidate_a))).scalars().first()
            cand_b = (await db.execute(select(Candidate).where(Candidate.id == f.candidate_b))).scalars().first()
            items.append(
                DuplicateFlagItem(
                    flag_id=str(f.id),
                    candidate_a_id=str(f.candidate_a),
                    candidate_a_name=cand_a.full_name if cand_a else "Unknown",
                    candidate_b_id=str(f.candidate_b),
                    candidate_b_name=cand_b.full_name if cand_b else "Unknown",
                    signals=f.signals,
                    status=f.status,
                    created_at=f.created_at,
                )
            )

        return FindDuplicatesResponse(duplicates=items)

    # --- Tool 11: merge_candidates ---
    async def merge_candidates(
        self,
        db: AsyncSession,
        flag_id: Optional[str] = None,
        primary_id: Optional[str] = None,
        duplicate_id: Optional[str] = None,
    ) -> MergeCandidatesResponse:
        if flag_id:
            q_flag = select(DuplicateFlag).where(DuplicateFlag.id == flag_id)
            flag = (await db.execute(q_flag)).scalars().first()
            if not flag:
                raise ValueError(f"Duplicate flag {flag_id} not found")
            p_id = flag.candidate_a
            d_id = flag.candidate_b
            flag.status = "resolved"
            flag.resolved_at = datetime.now(timezone.utc)
        elif primary_id and duplicate_id:
            p_id = uuid.UUID(primary_id)
            d_id = uuid.UUID(duplicate_id)
        else:
            raise ValueError("Either flag_id or (primary_id and duplicate_id) must be provided")

        q_primary = select(Candidate).where(Candidate.id == p_id)
        primary = (await db.execute(q_primary)).scalars().first()
        q_dup = select(Candidate).where(Candidate.id == d_id)
        duplicate = (await db.execute(q_dup)).scalars().first()

        if not primary or not duplicate:
            raise ValueError("Primary or duplicate candidate record not found")

        # Mark merged_into on duplicate
        duplicate.merged_into = primary.id

        # Merge skills
        if duplicate.skills:
            primary.skills = list(set((primary.skills or []) + duplicate.skills))

        # Re-point applications
        await db.execute(
            update(Application).where(Application.candidate_id == duplicate.id).values(candidate_id=primary.id)
        )

        # Re-point resumes
        await db.execute(
            update(Resume).where(Resume.candidate_id == duplicate.id).values(candidate_id=primary.id)
        )

        await db.commit()

        return MergeCandidatesResponse(
            merged_candidate_id=str(primary.id),
            status="merged",
            re_score_queued=True,
        )

    # --- Tool 12: generate_report ---
    async def generate_report(
        self,
        db: AsyncSession,
        run_id: str,
        format: str = "xlsx",
        columns: Optional[List[str]] = None,
    ) -> GenerateReportResponse:
        file_bytes, filename, total_rows = await report_service.generate_ranking_excel(
            db=db,
            run_id=run_id,
            columns=columns,
        )

        # Save to local report download cache folder
        os.makedirs("tmp/reports", exist_ok=True)
        report_path = os.path.join("tmp/reports", filename)
        with open(report_path, "wb") as f:
            f.write(file_bytes)

        settings = get_settings()
        base_url = settings.public_base_url.rstrip("/")
        download_url = f"{base_url}/api/v1/reports/download/{filename}"

        return GenerateReportResponse(
            run_id=run_id,
            format=format,
            filename=filename,
            total_rows=total_rows,
            download_url=download_url,
        )


tool_service = ToolService()
