"""
End-to-End Live Scoring Pipeline Verification
Calls the scoring pipeline using real iGentic platform executor for Vikramaditya Bose.
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure backend is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.db.models import Candidate, JobProfile, Resume
from app.services.scoring_pipeline import scoring_pipeline

async def test_live_scoring():
    settings = get_settings()
    print("=" * 70)
    print("End-to-End Pipeline Evaluation with Live iGentic Scoring Agent")
    print(f"Scoring Agent Mode: {settings.scoring_agent_mode}")
    print(f"Executor URL:       {settings.scoring_igentic_executor_url}")
    print("=" * 70)

    async with AsyncSessionLocal() as db:
        # Find candidate Vikramaditya Bose
        q_c = select(Candidate).where(Candidate.email == "vikram.bose.python@talentseed.dev")
        cand = (await db.execute(q_c)).scalars().first()
        assert cand is not None, "Candidate Vikramaditya Bose not found"

        # Find or create a matching active Job Profile
        q_jd = select(JobProfile).where(JobProfile.status == "active").limit(1)
        jd = (await db.execute(q_jd)).scalars().first()
        assert jd is not None, "No active Job Profile found"

        print(f"\nEvaluating Candidate: {cand.full_name} ({cand.email})")
        print(f"Against Job Profile:  {jd.title} (ID: {jd.id})")
        print("Required Skills:     ", jd.structured.get("must_have_skills"))

        # Score candidate through scoring_pipeline
        print("\nInvoking scoring_pipeline.score_candidate()...")
        score = await scoring_pipeline.score_candidate(
            db=db,
            job_profile_id=str(jd.id),
            candidate_id=str(cand.id),
        )

        print("\n" + "=" * 70)
        print("LIVE SCORING RESULT RECEIVED & PERSISTED")
        print("=" * 70)
        print(f"Final Combined Score: {score.final_score} / 100")
        print(f"  - Resume Score (70%):  {score.resume_score} / 100")
        print(f"  - Details Score (30%): {score.details_score} / 100")
        print(f"Confidence:            {score.confidence}")
        print(f"Model / Agent:         {score.model}")
        print(f"Matched Skills:        {score.matched_skills}")
        print(f"Missing Skills:        {score.missing_skills}")
        print(f"Flags:                 {score.flags}")
        print(f"Justification Reason:  {score.reason}")
        print(f"Sub-scores:            {score.sub_scores}")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_live_scoring())
