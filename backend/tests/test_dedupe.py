import uuid
import pytest
from sqlalchemy import select
from app.db.models import Candidate, DuplicateFlag, Resume
from app.services.dedupe_service import dedupe_service
from app.services.resume_service import resume_service

@pytest.mark.asyncio
async def test_dedupe_by_email(db_session):
    # Setup candidate
    c1 = Candidate(
        full_name="Vikram Mehta",
        email="vikram.mehta@example.com",
        phone="+919811122233",
        experience_years=5.0,
    )
    db_session.add(c1)
    await db_session.flush()

    found, reason = await dedupe_service.find_existing_candidate(
        db_session,
        email="VIKRAM.MEHTA@EXAMPLE.COM",
        phone=None,
    )
    assert found is not None
    assert found.id == c1.id
    assert reason == "exact_email"


@pytest.mark.asyncio
async def test_dedupe_by_phone(db_session):
    c1 = Candidate(
        full_name="Ananya Roy",
        email="ananya.roy@example.com",
        phone="+919988776655",
        experience_years=4.0,
    )
    db_session.add(c1)
    await db_session.flush()

    found, reason = await dedupe_service.find_existing_candidate(
        db_session,
        email=None,
        phone="+919988776655",
    )
    assert found is not None
    assert found.id == c1.id
    assert reason == "exact_phone"


@pytest.mark.asyncio
async def test_fuzzy_duplicate_flagging(db_session):
    c1 = Candidate(
        full_name="Karthik Subramanian",
        email="karthik.s@example.com",
        phone="+919444011223",
        experience_years=8.0,
        skills=["Python", "Django", "PostgreSQL"],
    )
    db_session.add(c1)
    await db_session.flush()

    c2 = Candidate(
        full_name="Karthik Subramanian",
        email="karthik.subramanian.alt@gmail.com",
        phone="+919444011223",
        experience_years=8.5,
        skills=["Python", "Django", "FastAPI"],
    )
    db_session.add(c2)
    await db_session.flush()

    flags = await dedupe_service.check_and_flag_fuzzy_duplicates(db_session, c2)
    assert len(flags) >= 1
    assert flags[0].status == "pending"
    assert flags[0].signals.get("name_match") is True


def test_resume_pii_redaction():
    raw_resume = (
        "Rahul Sharma\n"
        "Email: rahul.sharma.dev@gmail.com | Phone: +91 9876543210\n"
        "LinkedIn: https://linkedin.com/in/rahul-sharma-dev\n"
        "DOB: 15/08/1995 | Marital Status: Single\n"
        "Experience:\n"
        "Senior Backend Engineer with 6 years experience in Python and FastAPI.\n"
        "Built distributed microservices handling 50k RPM."
    )
    redacted = resume_service.redact_pii(
        raw_resume,
        candidate_name="Rahul Sharma",
        candidate_email="rahul.sharma.dev@gmail.com",
        candidate_phone="+91 9876543210",
    )
    assert "rahul.sharma.dev@gmail.com" not in redacted
    assert "9876543210" not in redacted
    assert "linkedin.com/in/rahul" not in redacted
    assert "[REDACTED_DOB]" in redacted or "DOB" not in redacted or "[REDACTED" in redacted
    assert "Python and FastAPI" in redacted
    assert "Built distributed microservices" in redacted
