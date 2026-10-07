import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Application, Candidate, JobProfile, Resume, Score, ScoringJob
from app.services.details_scorer import details_scorer
from app.services.evidence_grounding import evidence_grounding_validator
from app.services.resume_service import resume_service
from app.services.scoring_agent_client import scoring_agent_client

logger = logging.getLogger(__name__)


class ScoringPipeline:
    """
    Orchestrates the two-stage candidate scoring pipeline:
    1. Deterministic Python details_score
    2. AI Scoring Agent rubric assessment (or fallback when resume missing)
    3. Evidence grounding verification
    4. Python final score composition (0.4 * details + 0.6 * resume)
    """

    @staticmethod
    def compute_input_hash(jd_hash: str, candidate_id: str, resume_hash: Optional[str]) -> str:
        raw = f"{jd_hash}:{candidate_id}:{resume_hash or 'no_resume'}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def score_candidate(
        self,
        db: AsyncSession,
        job_profile_id: str,
        candidate_id: str,
    ) -> Score:
        # Verify active JD invariant
        q_jd = select(JobProfile).where(JobProfile.id == job_profile_id)
        jd = (await db.execute(q_jd)).scalars().first()
        if not jd:
            raise ValueError(f"JobProfile {job_profile_id} not found")
        if jd.status != "active":
            raise ValueError(f"JobProfile {job_profile_id} is not active (status={jd.status}). Scoring refused.")

        q_cand = select(Candidate).where(Candidate.id == candidate_id)
        cand = (await db.execute(q_cand)).scalars().first()
        if not cand:
            raise ValueError(f"Candidate {candidate_id} not found")

        # Fetch latest application for candidate to get expected CTC
        q_app = (
            select(Application)
            .where(Application.candidate_id == cand.id)
            .order_by(Application.received_at.desc())
            .limit(1)
        )
        app = (await db.execute(q_app)).scalars().first()
        expected_ctc = float(app.expected_ctc_lpa) if app and app.expected_ctc_lpa else None

        # Fetch resume if available
        q_resume = (
            select(Resume)
            .where(Resume.candidate_id == cand.id)
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
        resume = (await db.execute(q_resume)).scalars().first()

        # Build candidate facts
        candidate_facts = {
            "skills": cand.skills or [],
            "experience_years": float(cand.experience_years) if cand.experience_years else None,
            "notice_days_max": cand.notice_days_max,
            "location": cand.location,
            "preferred_locations": cand.preferred_locations or [],
            "expected_ctc_lpa": expected_ctc,
            "current_ctc_lpa": float(cand.current_ctc_lpa) if cand.current_ctc_lpa else None,
            "headline": cand.headline,
        }

        # 1. Deterministic Python details score
        details_score_val, details_breakdown = details_scorer.compute_details_score(
            candidate_facts=candidate_facts,
            jd_requirements=jd.structured,
        )

        input_hash = self.compute_input_hash(
            jd.content_hash, str(cand.id), resume.file_hash if resume else None
        )

        # Check existing score for idempotency
        q_score = select(Score).where(
            Score.job_profile_id == jd.id,
            Score.candidate_id == cand.id,
        )
        existing_score = (await db.execute(q_score)).scalars().first()

        flags: List[str] = []

        # 2. Case: No resume available
        if not resume or not resume.text_content or len(resume.text_content.strip()) < 50:
            flags.append("resume_missing")
            final_score_val = details_score_val
            resume_score_val = None
            reason_text = f"Details score only ({details_score_val:.1f}/100). Resume missing or unreadable."

            if existing_score:
                existing_score.input_hash = input_hash
                existing_score.details_score = details_score_val
                existing_score.details_breakdown = details_breakdown
                existing_score.resume_score = None
                existing_score.final_score = final_score_val
                existing_score.reason = reason_text
                existing_score.flags = flags
                existing_score.status = "complete"
                existing_score.scored_at = datetime.now(timezone.utc)
                await db.commit()
                return existing_score

            new_score = Score(
                job_profile_id=jd.id,
                candidate_id=cand.id,
                input_hash=input_hash,
                details_score=details_score_val,
                details_breakdown=details_breakdown,
                resume_score=None,
                sub_scores=None,
                must_have=None,
                matched_skills=[],
                missing_skills=jd.structured.get("must_have_skills", []),
                reason=reason_text,
                confidence="medium",
                final_score=final_score_val,
                flags=flags,
                status="complete",
                model="details_only",
                prompt_version="v1.0",
                scored_at=datetime.now(timezone.utc),
            )
            db.add(new_score)
            await db.commit()
            return new_score

        # 3. Case: Resume available -> Blind PII Redaction
        redacted_resume = resume_service.redact_pii(
            resume_text=resume.text_content,
            candidate_name=cand.full_name,
            candidate_email=cand.email,
            candidate_phone=cand.phone,
        )

        # 4. Call Scoring Agent
        rubric_output = await scoring_agent_client.score_resume(
            request_id=input_hash,
            job_profile=jd.structured,
            job_text=jd.raw_text,
            candidate_facts=candidate_facts,
            resume_text=redacted_resume,
        )

        # 5. Evidence Grounding Verification
        validated_must_have, grounding_flags, unverified_count = evidence_grounding_validator.validate(
            resume_text=resume.text_content,
            must_have_evaluations=rubric_output.must_have,
        )
        flags.extend(grounding_flags)

        # Sum sub-scores in Python (Scoring Agent never computes totals)
        sub_scores = dict(rubric_output.sub_scores)
        if unverified_count > 0:
            # Penalize coverage proportionally
            sub_scores["must_have_coverage"] = max(
                0, sub_scores.get("must_have_coverage", 0) - (unverified_count * 10)
            )

        raw_resume_score = sum(sub_scores.values())
        resume_score_val = float(min(100, max(0, raw_resume_score)))

        # 6. Python Final Score Composition (0.4 * details + 0.6 * resume)
        final_score_val = round(0.4 * details_score_val + 0.6 * resume_score_val, 2)

        if existing_score:
            existing_score.input_hash = input_hash
            existing_score.details_score = details_score_val
            existing_score.details_breakdown = details_breakdown
            existing_score.resume_score = resume_score_val
            existing_score.sub_scores = sub_scores
            existing_score.must_have = validated_must_have
            existing_score.matched_skills = rubric_output.matched_skills
            existing_score.missing_skills = rubric_output.missing_skills
            existing_score.reason = rubric_output.reason
            existing_score.confidence = rubric_output.confidence
            existing_score.final_score = final_score_val
            existing_score.flags = flags
            existing_score.status = "complete"
            existing_score.model = rubric_output.model
            existing_score.prompt_version = rubric_output.prompt_version
            existing_score.scored_at = datetime.now(timezone.utc)
            await db.commit()
            return existing_score

        new_score = Score(
            job_profile_id=jd.id,
            candidate_id=cand.id,
            input_hash=input_hash,
            details_score=details_score_val,
            details_breakdown=details_breakdown,
            resume_score=resume_score_val,
            sub_scores=sub_scores,
            must_have=validated_must_have,
            matched_skills=rubric_output.matched_skills,
            missing_skills=rubric_output.missing_skills,
            reason=rubric_output.reason,
            confidence=rubric_output.confidence,
            final_score=final_score_val,
            flags=flags,
            status="complete",
            model=rubric_output.model,
            prompt_version=rubric_output.prompt_version,
            scored_at=datetime.now(timezone.utc),
        )
        db.add(new_score)
        await db.commit()
        return new_score


scoring_pipeline = ScoringPipeline()
