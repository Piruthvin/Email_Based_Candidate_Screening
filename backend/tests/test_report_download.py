import os
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.core.config import get_settings
from app.core.database import get_db
from app.db.models import JobProfile, RankingRun, RankingResult, Candidate
from app.main import app
from app.services.tool_service import tool_service


@pytest_asyncio.fixture
async def api_client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_ranking_run(db_session):
    # Create JobProfile
    jp = JobProfile(
        title="Report Test Role",
        raw_text="Sample text",
        structured={"title": "Report Test Role"},
        content_hash=uuid.uuid4().hex,
        status="active"
    )
    db_session.add(jp)
    await db_session.flush()

    # Create candidate
    cand = Candidate(
        full_name="Report Candidate",
        skills=["Python", "FastAPI"],
        experience_years=5.0
    )
    db_session.add(cand)
    await db_session.flush()

    # Create RankingRun
    run = RankingRun(
        job_profile_id=jp.id,
        rank_by="final",
        top_n=10,
        scored_pct=100.0
    )
    db_session.add(run)
    await db_session.flush()

    # Create RankingResult
    res = RankingResult(
        run_id=run.id,
        candidate_id=cand.id,
        rank_position=1,
        final_score=88.5,
        details_score=90.0,
        resume_score=87.0,
        reason="Good fit"
    )
    db_session.add(res)
    await db_session.commit()

    return str(run.id)


@pytest.mark.asyncio
async def test_generate_report_local_url(db_session, sample_ranking_run):
    """Test 1: Local URL generation with default or local PUBLIC_BASE_URL."""
    settings = get_settings()
    orig = settings.public_base_url
    try:
        settings.public_base_url = "http://localhost:8000"
        res = await tool_service.generate_report(db=db_session, run_id=sample_ranking_run)
        assert res.download_url == f"http://localhost:8000/api/v1/reports/download/{res.filename}"
        assert res.download_url.startswith("http://localhost:8000/api/v1/reports/download/")
    finally:
        settings.public_base_url = orig


@pytest.mark.asyncio
async def test_generate_report_azure_url(db_session, sample_ranking_run):
    """Test 2: Azure URL generation with cloud PUBLIC_BASE_URL."""
    settings = get_settings()
    orig = settings.public_base_url
    try:
        settings.public_base_url = "https://my-app.azurecontainerapps.io"
        res = await tool_service.generate_report(db=db_session, run_id=sample_ranking_run)
        assert res.download_url == f"https://my-app.azurecontainerapps.io/api/v1/reports/download/{res.filename}"
        assert res.download_url.startswith("https://my-app.azurecontainerapps.io/api/v1/reports/download/")
    finally:
        settings.public_base_url = orig


@pytest.mark.asyncio
async def test_generate_report_trailing_slash(db_session, sample_ranking_run):
    """Test 3: PUBLIC_BASE_URL with trailing slash strips slash and avoids double slashes."""
    settings = get_settings()
    orig = settings.public_base_url
    try:
        settings.public_base_url = "https://my-app.azurecontainerapps.io/"
        res = await tool_service.generate_report(db=db_session, run_id=sample_ranking_run)
        assert res.download_url == f"https://my-app.azurecontainerapps.io/api/v1/reports/download/{res.filename}"
        assert "//api/" not in res.download_url
    finally:
        settings.public_base_url = orig


@pytest.mark.asyncio
async def test_download_report_file_success(api_client):
    """Test 4: Downloading a generated report file returns HTTP 200 with proper media type."""
    os.makedirs("tmp/reports", exist_ok=True)
    test_filename = f"test_download_{uuid.uuid4().hex[:8]}.xlsx"
    file_path = os.path.join("tmp", "reports", test_filename)
    dummy_content = b"PK\x03\x04test_xlsx_payload_content"
    with open(file_path, "wb") as f:
        f.write(dummy_content)

    try:
        resp = await api_client.get(f"/api/v1/reports/download/{test_filename}")
        assert resp.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.headers["content-type"]
        assert resp.content == dummy_content
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@pytest.mark.asyncio
async def test_download_report_missing_404(api_client):
    """Test 5: Non-existent report file returns HTTP 404."""
    resp = await api_client.get("/api/v1/reports/download/nonexistent_file_9999.xlsx")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Report file not found"


@pytest.mark.asyncio
async def test_download_report_path_traversal_rejection(api_client):
    """Test 6: Path traversal attempts cannot access files outside tmp/reports/."""
    from fastapi import HTTPException
    from app.api.v1.reports import download_report

    # Direct function calls with path traversal patterns raise HTTP 400
    with pytest.raises(HTTPException) as exc_info1:
        await download_report("../../some-secret-file")
    assert exc_info1.value.status_code == 400
    assert exc_info1.value.detail == "Invalid report filename"

    with pytest.raises(HTTPException) as exc_info2:
        await download_report("..\\..\\some-secret-file")
    assert exc_info2.value.status_code == 400
    assert exc_info2.value.detail == "Invalid report filename"

    with pytest.raises(HTTPException) as exc_info3:
        await download_report("subfolder/secret.txt")
    assert exc_info3.value.status_code == 400
    assert exc_info3.value.detail == "Invalid report filename"

    # HTTP client requests with encoded path manipulation are rejected (400 or 404), never 200
    resp1 = await api_client.get("/api/v1/reports/download/..%2F..%2Fsome-secret-file")
    assert resp1.status_code in (400, 404)

    resp2 = await api_client.get("/api/v1/reports/download/..%5C..%5Csome-secret-file")
    assert resp2.status_code in (400, 404)
