import pytest
from app.db.models import Candidate, JobProfile
from app.services.details_scorer import details_scorer
from app.services.scoring_pipeline import scoring_pipeline

def test_details_scorer_full_match():
    cand = {
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
        "experience_years": 6.0,
        "notice_days_max": 15,
        "location": "Bangalore",
        "preferred_locations": ["Bangalore", "Remote"],
        "expected_ctc_lpa": 22.0,
    }
    jd = {
        "must_have_skills": ["Python", "FastAPI", "PostgreSQL"],
        "nice_to_have_skills": ["Docker", "AWS"],
        "experience_min_years": 5.0,
        "experience_max_years": 8.0,
        "notice_days_max": 30,
        "locations": ["Bangalore"],
        "remote_ok": True,
        "budget_lpa_max": 25.0,
    }
    score, breakdown = details_scorer.compute_details_score(cand, jd)
    assert score >= 90.0
    assert breakdown["skills"] == 100.0
    assert breakdown["experience"] == 100.0
    assert breakdown["notice"] == 90.0
    assert breakdown["location"] == 100.0
    assert breakdown["budget"] == 100.0


def test_details_scorer_missing_budget_and_location_renormalization():
    cand = {
        "skills": ["Python"],
        "experience_years": 4.0,
        "notice_days_max": 30,
        "location": None,
        "preferred_locations": [],
        "expected_ctc_lpa": None,
    }
    jd = {
        "must_have_skills": ["Python", "Go"],
        "nice_to_have_skills": [],
        "experience_min_years": 5.0,
        "experience_max_years": 7.0,
        "locations": [],
        "remote_ok": False,
        "budget_lpa_max": None,
    }
    score, breakdown = details_scorer.compute_details_score(cand, jd)
    assert "skills" in breakdown
    assert "experience" in breakdown
    assert breakdown["location"] is None
    assert breakdown["budget"] is None
    # 1 out of 2 must have = 50.0
    assert breakdown["skills"] == 50.0
    # 4.0 exp vs 5.0 min = 100 - 15*1 = 85.0
    assert breakdown["experience"] == 85.0
    # Notice = 30 days -> 70.0
    assert breakdown["notice"] == 70.0
    # Renormalized over weights skills(0.35), exp(0.25), notice(0.20) => sum=0.80
    # Expected: (0.35*50 + 0.25*85 + 0.20*70) / 0.80 = (17.5 + 21.25 + 14) / 0.8 = 52.75 / 0.8 = 65.94
    assert abs(score - 65.94) < 0.5


@pytest.mark.asyncio
async def test_no_score_without_active_jd_invariant(db_session):
    # Candidate
    c = Candidate(full_name="Raj Kumar", email="raj@example.com")
    db_session.add(c)

    # Draft JD (not active)
    jd_draft = JobProfile(
        title="Frontend Engineer",
        raw_text="React developer needed",
        structured={"must_have_skills": ["React"]},
        content_hash="draft_hash_123",
        status="draft",
    )
    db_session.add(jd_draft)
    await db_session.flush()

    with pytest.raises(ValueError, match="is not active"):
        await scoring_pipeline.score_candidate(
            db=db_session,
            job_profile_id=str(jd_draft.id),
            candidate_id=str(c.id),
        )
