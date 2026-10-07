import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.core.database import get_db
from app.db.models import Candidate, JobProfile
from app.main import app


@pytest_asyncio.fixture
async def api_client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_endpoints(api_client):
    resp = await api_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    resp_ready = await api_client.get("/ready")
    assert resp_ready.status_code == 200
    assert resp_ready.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_get_pool_stats_api(api_client):
    resp = await api_client.post("/api/v1/tools/get_pool_stats", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_candidates" in data
    assert "unscored_candidates" in data
    assert "active_jds_count" in data


@pytest.mark.asyncio
async def test_sync_mailbox_graceful_no_op(api_client):
    resp = await api_client.post(
        "/api/v1/tools/sync_mailbox",
        json={"mailbox": "test@company.com", "mode": "latest"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert data["status"] in ("success", "running")


@pytest.mark.asyncio
async def test_save_and_activate_job_profile(api_client):
    import uuid
    uid = uuid.uuid4().hex[:6]
    # 1. Save draft JD
    jd_payload = {
        "title": f"Lead Python Architect {uid}",
        "raw_text": f"Looking for a Lead Python Architect {uid} with 8+ years experience in FastAPI and PostgreSQL.",
        "structured": {
            "title": f"Lead Python Architect {uid}",
            "must_have_skills": ["Python", "FastAPI", "PostgreSQL"],
            "experience_min_years": 8.0,
            "experience_max_years": 12.0,
            "budget_lpa_max": 35.0,
            "locations": ["Bangalore"],
        },
    }
    resp = await api_client.post("/api/v1/tools/save_job_profile", json=jd_payload)
    assert resp.status_code == 200
    saved_jd = resp.json()
    assert saved_jd["status"] == "draft"
    assert saved_jd["content_hash"] is not None
    jd_id = saved_jd["job_profile_id"]

    # 2. Idempotent check: saving same payload returns same ID
    resp_idem = await api_client.post("/api/v1/tools/save_job_profile", json=jd_payload)
    assert resp_idem.status_code == 200
    assert resp_idem.json()["job_profile_id"] == jd_id

    # 3. Rank candidates BEFORE activation must fail with JD_REQUIRED
    resp_rank_before = await api_client.post(
        "/api/v1/tools/rank_candidates",
        json={"job_profile_id": jd_id, "top_n": 10},
    )
    assert resp_rank_before.status_code == 400
    assert resp_rank_before.json()["detail"]["error"] == "JD_REQUIRED"

    # 4. Activate JD
    resp_act = await api_client.post(
        "/api/v1/tools/activate_job_profile",
        json={"job_profile_id": jd_id, "confirmed_by": "lead_recruiter"},
    )
    assert resp_act.status_code == 200
    assert resp_act.json()["status"] == "active"

    # 5. Get scoring status
    resp_status = await api_client.post(
        "/api/v1/tools/get_scoring_status",
        json={"job_profile_id": jd_id},
    )
    assert resp_status.status_code == 200
    status_data = resp_status.json()
    assert "scored_pct" in status_data
    assert "eta_hint" in status_data


@pytest.mark.asyncio
async def test_search_candidates_no_scores(db_session, api_client):
    import uuid
    uid = uuid.uuid4().hex[:6]
    # Insert candidate
    c = Candidate(
        full_name=f"Deepak Joshi {uid}",
        email=f"deepak.{uid}@example.com",
        phone=f"+91987600{uid[:4]}",
        experience_years=5.0,
        notice_days_max=15,
        location="Pune",
        skills=["Python", "FastAPI"],
    )
    db_session.add(c)
    await db_session.commit()

    resp = await api_client.post(
        "/api/v1/tools/search_candidates",
        json={"filters": {"notice_days_max": 30, "skills": ["Python"]}, "limit": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    found = [x for x in data["candidates"] if x["full_name"] == f"Deepak Joshi {uid}"]
    assert len(found) == 1
    assert "final_score" not in found[0]
    assert "rank_position" not in found[0]


@pytest.mark.asyncio
async def test_get_candidate_and_disambiguation(db_session, api_client):
    import uuid
    uid = uuid.uuid4().hex[:6]
    c1 = Candidate(full_name=f"Kavita Iyer {uid}", email=f"kavita.1.{uid}@example.com")
    c2 = Candidate(full_name=f"Kavita Iyer {uid}", email=f"kavita.2.{uid}@example.com")
    db_session.add_all([c1, c2])
    await db_session.commit()

    # Search by ambiguous name
    resp = await api_client.post("/api/v1/tools/get_candidate", json={"name": f"Kavita Iyer {uid}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["disambiguation"] is True
    assert len(data["candidates"]) >= 2

    # Search by specific candidate_id
    resp_id = await api_client.post("/api/v1/tools/get_candidate", json={"candidate_id": str(c1.id)})
    assert resp_id.status_code == 200
    dossier = resp_id.json()
    assert dossier["disambiguation"] is False
    assert dossier["candidate_id"] == str(c1.id)
    assert dossier["full_name"] == f"Kavita Iyer {uid}"

