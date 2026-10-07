import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_db
from app.db.models import AuditLog, Candidate, JobProfile, Score, ScoringJob
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
async def test_list_job_profiles_all_and_filtering(db_session, api_client):
    uid = uuid.uuid4().hex[:6]

    # Create 1 draft, 1 active, 1 inactive JD
    jd_draft = JobProfile(
        title=f"Draft Role {uid}",
        raw_text="Requires Python",
        structured={"must_have_skills": ["Python"], "experience_min_years": 2.0},
        content_hash=f"hash_draft_{uid}",
        status="draft",
    )
    jd_active = JobProfile(
        title=f"Active Role {uid}",
        raw_text="Requires React",
        structured={"must_have_skills": ["React"], "experience_min_years": 3.0},
        content_hash=f"hash_active_{uid}",
        status="active",
    )
    jd_inactive = JobProfile(
        title=f"Inactive Role {uid}",
        raw_text="Requires Java",
        structured={"must_have_skills": ["Java"], "experience_min_years": 5.0},
        content_hash=f"hash_inactive_{uid}",
        status="inactive",
    )
    db_session.add_all([jd_draft, jd_active, jd_inactive])
    await db_session.commit()

    # 1. List all
    res_all = await api_client.post("/api/v1/tools/list_job_profiles", json={})
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] >= 3
    all_ids = [jp["job_profile_id"] for jp in data_all["job_profiles"]]
    assert str(jd_draft.id) in all_ids
    assert str(jd_active.id) in all_ids
    assert str(jd_inactive.id) in all_ids

    # 2. Filter draft
    res_draft = await api_client.post("/api/v1/tools/list_job_profiles", json={"status": "draft"})
    assert res_draft.status_code == 200
    for jp in res_draft.json()["job_profiles"]:
        assert jp["status"] == "draft"
    draft_ids = [jp["job_profile_id"] for jp in res_draft.json()["job_profiles"]]
    assert str(jd_draft.id) in draft_ids
    assert str(jd_active.id) not in draft_ids

    # 3. Filter active
    res_act = await api_client.post("/api/v1/tools/list_job_profiles", json={"status": "active"})
    assert res_act.status_code == 200
    for jp in res_act.json()["job_profiles"]:
        assert jp["status"] == "active"
    act_ids = [jp["job_profile_id"] for jp in res_act.json()["job_profiles"]]
    assert str(jd_active.id) in act_ids

    # 4. Filter inactive
    res_inact = await api_client.post("/api/v1/tools/list_job_profiles", json={"status": "inactive"})
    assert res_inact.status_code == 200
    for jp in res_inact.json()["job_profiles"]:
        assert jp["status"] == "inactive"
    inact_ids = [jp["job_profile_id"] for jp in res_inact.json()["job_profiles"]]
    assert str(jd_inactive.id) in inact_ids

    # 5. Filter nonexistent status returns empty
    res_none = await api_client.post("/api/v1/tools/list_job_profiles", json={"status": "archived_unknown"})
    assert res_none.status_code == 200
    assert res_none.json()["total"] == 0
    assert len(res_none.json()["job_profiles"]) == 0


@pytest.mark.asyncio
async def test_activate_job_profile_lifecycle(db_session, api_client):
    uid = uuid.uuid4().hex[:6]

    # Create candidate so bulk scoring enqueue has work
    cand = Candidate(
        full_name=f"Test Candidate {uid}",
        email=f"cand_{uid}@example.com",
        experience_years=4.0,
        skills=["Python", "FastAPI"],
    )
    db_session.add(cand)

    jd = JobProfile(
        title=f"Backend Lead {uid}",
        raw_text="Requires Python and FastAPI",
        structured={"must_have_skills": ["Python", "FastAPI"], "experience_min_years": 4.0},
        content_hash=f"hash_act_{uid}",
        status="draft",
    )
    db_session.add(jd)
    await db_session.commit()

    # 1. Valid Draft -> Active
    resp = await api_client.post(
        "/api/v1/tools/activate_job_profile",
        json={"job_profile_id": str(jd.id), "confirmed_by": "recruiter_bob"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert data["job_profile_id"] == str(jd.id)
    assert data["scoring_jobs_queued"] >= 1
    assert "now active" in data["message"]

    # 2. Already active -> Reject with 400 ALREADY_ACTIVE
    resp_dup = await api_client.post(
        "/api/v1/tools/activate_job_profile",
        json={"job_profile_id": str(jd.id), "confirmed_by": "recruiter_bob"},
    )
    assert resp_dup.status_code == 400
    err = resp_dup.json()["detail"]
    assert err["error"] == "ALREADY_ACTIVE"

    # 3. Nonexistent ID -> 404 NOT_FOUND
    random_uuid = str(uuid.uuid4())
    resp_nf = await api_client.post(
        "/api/v1/tools/activate_job_profile",
        json={"job_profile_id": random_uuid},
    )
    assert resp_nf.status_code == 404
    assert resp_nf.json()["detail"]["error"] == "NOT_FOUND"

    # 4. Malformed UUID -> 400 INVALID_ID
    resp_inv = await api_client.post(
        "/api/v1/tools/activate_job_profile",
        json={"job_profile_id": "not-a-valid-uuid"},
    )
    assert resp_inv.status_code == 400
    assert resp_inv.json()["detail"]["error"] == "INVALID_ID"


@pytest.mark.asyncio
async def test_deactivate_job_profile_lifecycle(db_session, api_client):
    uid = uuid.uuid4().hex[:6]

    cand = Candidate(
        full_name=f"Candidate {uid}",
        email=f"cand_deact_{uid}@example.com",
        experience_years=5.0,
        skills=["Python"],
    )
    db_session.add(cand)

    jd = JobProfile(
        title=f"Active Role To Deactivate {uid}",
        raw_text="Requires Python",
        structured={"must_have_skills": ["Python"]},
        content_hash=f"hash_deact_{uid}",
        status="active",
    )
    db_session.add(jd)
    await db_session.flush()

    # Create a queued scoring job and a completed score
    s_job = ScoringJob(
        job_profile_id=jd.id,
        candidate_id=cand.id,
        input_hash=f"input_{uid}",
        status="queued",
    )
    db_session.add(s_job)

    hist_score = Score(
        job_profile_id=jd.id,
        candidate_id=cand.id,
        input_hash=f"input_{uid}",
        details_score=85.0,
        final_score=85.0,
        confidence="high",
        status="complete",
    )
    db_session.add(hist_score)
    await db_session.commit()

    # 1. Valid Active -> Inactive
    resp = await api_client.post(
        "/api/v1/tools/deactivate_job_profile",
        json={"job_profile_id": str(jd.id), "confirmed_by": "recruiter_alice", "reason": "Role closed"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "inactive"
    assert data["cancelled_scoring_jobs"] == 1
    assert "now inactive" in data["message"]

    # Verify JD status in DB
    await db_session.refresh(jd)
    assert jd.status == "inactive"

    # Verify scoring job was cancelled
    await db_session.refresh(s_job)
    assert s_job.status == "cancelled"
    assert "Cancelled upon JD deactivation" in (s_job.last_error or "")

    # Verify historical score was NOT deleted
    q_score = select(Score).where(Score.job_profile_id == jd.id, Score.candidate_id == cand.id)
    score_in_db = (await db_session.execute(q_score)).scalars().first()
    assert score_in_db is not None
    assert float(score_in_db.final_score) == 85.0

    # 2. Already inactive -> 400 ALREADY_INACTIVE
    resp_again = await api_client.post(
        "/api/v1/tools/deactivate_job_profile",
        json={"job_profile_id": str(jd.id)},
    )
    assert resp_again.status_code == 400
    assert resp_again.json()["detail"]["error"] == "ALREADY_INACTIVE"

    # 3. Draft -> Inactive is INVALID_TRANSITION
    jd_draft = JobProfile(
        title=f"Draft Role {uid}",
        raw_text="Raw text",
        structured={},
        content_hash=f"hash_draft_trans_{uid}",
        status="draft",
    )
    db_session.add(jd_draft)
    await db_session.commit()

    resp_draft_deact = await api_client.post(
        "/api/v1/tools/deactivate_job_profile",
        json={"job_profile_id": str(jd_draft.id)},
    )
    assert resp_draft_deact.status_code == 400
    assert resp_draft_deact.json()["detail"]["error"] == "INVALID_TRANSITION"

    # 4. Reactivation: Inactive -> Active
    resp_react = await api_client.post(
        "/api/v1/tools/activate_job_profile",
        json={"job_profile_id": str(jd.id), "confirmed_by": "recruiter_alice"},
    )
    assert resp_react.status_code == 200
    assert resp_react.json()["status"] == "active"
    assert "reactivated" in resp_react.json()["message"]


@pytest.mark.asyncio
async def test_job_profile_audit_logging(db_session, api_client):
    uid = uuid.uuid4().hex[:6]
    jd = JobProfile(
        title=f"Audit Test Role {uid}",
        raw_text="Requires Python",
        structured={},
        content_hash=f"hash_audit_{uid}",
        status="draft",
    )
    db_session.add(jd)
    await db_session.commit()

    # Call activate
    await api_client.post("/api/v1/tools/activate_job_profile", json={"job_profile_id": str(jd.id)})
    # Call deactivate
    await api_client.post("/api/v1/tools/deactivate_job_profile", json={"job_profile_id": str(jd.id)})

    # Verify audit log entries
    q_aud = select(AuditLog).where(AuditLog.tool.in_(["activate_job_profile", "deactivate_job_profile"]))
    audit_entries = (await db_session.execute(q_aud)).scalars().all()
    tools_logged = [e.tool for e in audit_entries]
    assert "activate_job_profile" in tools_logged
    assert "deactivate_job_profile" in tools_logged


@pytest.mark.asyncio
async def test_job_profile_negative_api_payloads(api_client):
    # 1. Missing body
    resp = await api_client.post("/api/v1/tools/activate_job_profile")
    assert resp.status_code == 422

    # 2. Empty body
    resp = await api_client.post("/api/v1/tools/activate_job_profile", json={})
    assert resp.status_code == 422

    # 3. Missing job_profile_id
    resp = await api_client.post("/api/v1/tools/deactivate_job_profile", json={"confirmed_by": "me"})
    assert resp.status_code == 422

    # 4. Null job_profile_id
    resp = await api_client.post("/api/v1/tools/deactivate_job_profile", json={"job_profile_id": None})
    assert resp.status_code == 422
