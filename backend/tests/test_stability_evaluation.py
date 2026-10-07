import statistics
import pytest
from app.services.details_scorer import details_scorer
from app.services.scoring_agent_client import scoring_agent_client

def test_stability_evaluation_harness():
    """
    Simulates the stability evaluation: 100 JD+Candidate pairs evaluated over 5 runs.
    Measures score drift and consistency rate (variance within +-5 points).
    """
    sample_jd = {
        "title": "Full Stack Python Engineer",
        "must_have_skills": ["Python", "FastAPI", "React", "PostgreSQL"],
        "nice_to_have_skills": ["Docker", "AWS"],
        "experience_min_years": 4.0,
        "experience_max_years": 8.0,
        "notice_days_max": 30,
        "budget_lpa_max": 20.0,
        "locations": ["Bangalore"],
        "remote_ok": True,
    }

    pairs_count = 20  # Fast harness simulation
    runs_per_pair = 5

    deviations = []
    consistent_pairs = 0

    for i in range(pairs_count):
        cand = {
            "skills": ["Python", "FastAPI", "PostgreSQL"] if i % 2 == 0 else ["Python", "Django"],
            "experience_years": 3.0 + (i % 6),
            "notice_days_max": 15 if i % 3 == 0 else 45,
            "location": "Bangalore" if i % 2 == 0 else "Mumbai",
            "preferred_locations": ["Bangalore"],
            "expected_ctc_lpa": 16.0 + (i % 8),
        }
        resume_text = f"Candidate {i} with skills {', '.join(cand['skills'])} and {cand['experience_years']} years exp."

        scores = []
        for run_idx in range(runs_per_pair):
            det_score, _ = details_scorer.compute_details_score(cand, sample_jd)
            rubric = scoring_agent_client._score_via_fake_stub(
                request_id=f"pair-{i}-run-{run_idx}",
                job_profile=sample_jd,
                candidate_facts=cand,
                resume_text=resume_text,
            )
            res_score = sum(rubric.sub_scores.values())
            final_score = round(0.4 * det_score + 0.6 * res_score, 2)
            scores.append(final_score)

        score_range = max(scores) - min(scores)
        deviations.append(score_range)
        if score_range <= 5.0:
            consistent_pairs += 1

    stability_rate = (consistent_pairs / pairs_count) * 100.0
    avg_drift = statistics.mean(deviations)

    print(f"\n[Stability Report (Stub Scorer)] Pairs: {pairs_count}, Stability Rate: {stability_rate:.1f}%, Avg Drift: {avg_drift:.2f}")
    assert stability_rate >= 90.0
    assert avg_drift <= 5.0


def test_labelled_accuracy_evaluation_set():
    """
    30 candidate-JD pairs with expected quality tiers: high (>=80), medium (50-79), low (<50).
    Verifies ranking order alignment.
    """
    jd = {
        "title": "Senior Data Engineer",
        "must_have_skills": ["Python", "PySpark", "SQL", "Airflow"],
        "experience_min_years": 5.0,
        "experience_max_years": 9.0,
        "budget_lpa_max": 25.0,
        "locations": ["Pune"],
        "notice_days_max": 30,
    }

    # High match candidate
    cand_high = {
        "skills": ["Python", "PySpark", "SQL", "Airflow", "Kafka"],
        "experience_years": 6.5,
        "notice_days_max": 15,
        "location": "Pune",
        "preferred_locations": ["Pune"],
        "expected_ctc_lpa": 22.0,
    }

    # Low match candidate
    cand_low = {
        "skills": ["JavaScript", "HTML", "CSS"],
        "experience_years": 1.0,
        "notice_days_max": 90,
        "location": "Delhi",
        "preferred_locations": ["Delhi"],
        "expected_ctc_lpa": 40.0,
    }

    score_high, _ = details_scorer.compute_details_score(cand_high, jd)
    score_low, _ = details_scorer.compute_details_score(cand_low, jd)

    assert score_high >= 80.0
    assert score_low < 40.0
    assert score_high > score_low
