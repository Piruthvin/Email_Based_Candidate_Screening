import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Mail(Base):
    __tablename__ = "mails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    message_id = Column(String(255), unique=True, nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), nullable=False, index=True)
    sender = Column(String(255), nullable=True)
    subject = Column(Text, nullable=True)
    source = Column(String(64), nullable=False, default="naukri_nvite")
    raw_headers = Column(JSONB, nullable=False, default=dict)
    raw_body_text = Column(Text, nullable=True)
    raw_body_html = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="queued", index=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    applications = relationship("Application", back_populates="mail", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="mail", cascade="all, delete-orphan")
    ingest_job = relationship("IngestJob", back_populates="mail", uselist=False, cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    full_name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(64), nullable=True)
    headline = Column(Text, nullable=True)
    current_company = Column(String(255), nullable=True)
    experience_years = Column(Numeric(4, 1), nullable=True)
    current_ctc_lpa = Column(Numeric(6, 2), nullable=True)
    notice_raw = Column(String(128), nullable=True)
    notice_days_max = Column(Integer, nullable=True)
    location = Column(String(128), nullable=True)
    preferred_locations = Column(ARRAY(Text), nullable=False, default=list)
    education = Column(Text, nullable=True)
    skills = Column(ARRAY(Text), nullable=False, default=list)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    merged_into = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="candidate", cascade="all, delete-orphan")
    scoring_jobs = relationship("ScoringJob", back_populates="candidate", cascade="all, delete-orphan")
    ranking_results = relationship("RankingResult", back_populates="candidate", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_candidates_email_active", "email", unique=True, postgresql_where=text("email IS NOT NULL AND merged_into IS NULL")),
        Index("idx_candidates_phone_active", "phone", postgresql_where=text("phone IS NOT NULL AND merged_into IS NULL")),
        Index("idx_candidates_filter", "notice_days_max", "experience_years"),
    )


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    mail_id = Column(UUID(as_uuid=True), ForeignKey("mails.id", ondelete="CASCADE"), nullable=False)
    job_title = Column(String(255), nullable=True)
    job_locations = Column(ARRAY(Text), nullable=False, default=list)
    expected_ctc_lpa = Column(Numeric(6, 2), nullable=True)
    answers = Column(JSONB, nullable=False, default=list)
    received_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    candidate = relationship("Candidate", back_populates="applications")
    mail = relationship("Mail", back_populates="applications")

    __table_args__ = (
        UniqueConstraint("candidate_id", "mail_id", name="uq_applications_candidate_mail"),
    )


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    mail_id = Column(UUID(as_uuid=True), ForeignKey("mails.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False, index=True)
    file_size_bytes = Column(BigInteger, nullable=False)
    file_content_bytes = Column(BYTEA, nullable=False)
    text_content = Column(Text, nullable=True)
    text_quality = Column(String(32), nullable=False, default="ok")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    candidate = relationship("Candidate", back_populates="resumes")
    mail = relationship("Mail", back_populates="resumes")


class JobProfile(Base):
    __tablename__ = "job_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    title = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    structured = Column(JSONB, nullable=False)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("job_profiles.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(32), nullable=False, default="draft", index=True)
    created_by = Column(String(255), nullable=False, default="recruiter")
    confirmed_by = Column(String(255), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    scores = relationship("Score", back_populates="job_profile", cascade="all, delete-orphan")
    scoring_jobs = relationship("ScoringJob", back_populates="job_profile", cascade="all, delete-orphan")
    ranking_runs = relationship("RankingRun", back_populates="job_profile", cascade="all, delete-orphan")


class IngestJob(Base):
    __tablename__ = "ingest_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    mail_id = Column(UUID(as_uuid=True), ForeignKey("mails.id", ondelete="CASCADE"), unique=True, nullable=False)
    status = Column(String(32), nullable=False, default="queued", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    next_attempt_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    queued_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    mail = relationship("Mail", back_populates="ingest_job")

    __table_args__ = (
        Index("idx_ingest_jobs_status_poll", "status", "next_attempt_at"),
    )


class ScoringJob(Base):
    __tablename__ = "scoring_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    job_profile_id = Column(UUID(as_uuid=True), ForeignKey("job_profiles.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    input_hash = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="queued", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    priority = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    queued_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    job_profile = relationship("JobProfile", back_populates="scoring_jobs")
    candidate = relationship("Candidate", back_populates="scoring_jobs")
    resume = relationship("Resume")

    __table_args__ = (
        UniqueConstraint("job_profile_id", "candidate_id", "input_hash", name="uq_scoring_jobs_eval"),
        Index("idx_scoring_jobs_poll", "status", "priority", "next_attempt_at"),
    )


class Score(Base):
    __tablename__ = "scores"

    job_profile_id = Column(UUID(as_uuid=True), ForeignKey("job_profiles.id", ondelete="CASCADE"), primary_key=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    input_hash = Column(String(64), nullable=False)
    details_score = Column(Numeric(5, 2), nullable=False)
    details_breakdown = Column(JSONB, nullable=False, default=dict)
    resume_score = Column(Numeric(5, 2), nullable=True)
    sub_scores = Column(JSONB, nullable=True)
    must_have = Column(JSONB, nullable=True)
    matched_skills = Column(ARRAY(Text), nullable=False, default=list)
    missing_skills = Column(ARRAY(Text), nullable=False, default=list)
    reason = Column(Text, nullable=True)
    confidence = Column(String(32), nullable=False, default="high")
    final_score = Column(Numeric(5, 2), nullable=False)
    flags = Column(ARRAY(Text), nullable=False, default=list)
    status = Column(String(32), nullable=False, default="complete")
    model = Column(String(128), nullable=True)
    prompt_version = Column(String(64), nullable=True)
    scored_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    job_profile = relationship("JobProfile", back_populates="scores")
    candidate = relationship("Candidate", back_populates="scores")

    __table_args__ = (
        Index("idx_scores_final", "job_profile_id", "final_score"),
    )


class RankingRun(Base):
    __tablename__ = "ranking_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    job_profile_id = Column(UUID(as_uuid=True), ForeignKey("job_profiles.id", ondelete="CASCADE"), nullable=False)
    rank_by = Column(String(32), nullable=False, default="final")
    top_n = Column(Integer, nullable=False, default=10)
    filters = Column(JSONB, nullable=False, default=dict)
    sort_keys = Column(JSONB, nullable=False, default=list)
    scored_pct = Column(Numeric(5, 2), nullable=False, default=0.0)
    created_by = Column(String(255), nullable=False, default="recruiter")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    job_profile = relationship("JobProfile", back_populates="ranking_runs")
    results = relationship("RankingResult", back_populates="ranking_run", cascade="all, delete-orphan")


class RankingResult(Base):
    __tablename__ = "ranking_results"

    run_id = Column(UUID(as_uuid=True), ForeignKey("ranking_runs.id", ondelete="CASCADE"), primary_key=True)
    rank_position = Column(Integer, primary_key=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    final_score = Column(Numeric(5, 2), nullable=False)
    details_score = Column(Numeric(5, 2), nullable=False)
    resume_score = Column(Numeric(5, 2), nullable=True)
    reason = Column(Text, nullable=True)
    missing_skills = Column(ARRAY(Text), nullable=False, default=list)

    ranking_run = relationship("RankingRun", back_populates="results")
    candidate = relationship("Candidate", back_populates="ranking_results")


class DuplicateFlag(Base):
    __tablename__ = "duplicate_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    candidate_a = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    candidate_b = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    signals = Column(JSONB, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    candidate_a_rel = relationship("Candidate", foreign_keys=[candidate_a])
    candidate_b_rel = relationship("Candidate", foreign_keys=[candidate_b])

    __table_args__ = (
        UniqueConstraint("candidate_a", "candidate_b", name="uq_duplicate_pair"),
    )


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    mailbox = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="running")
    started_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    new_mails = Column(Integer, nullable=False, default=0)
    new_candidates = Column(Integer, nullable=False, default=0)
    existing_candidates_new_application = Column(Integer, nullable=False, default=0)
    duplicate_flags = Column(Integer, nullable=False, default=0)
    last_mail_received_at = Column(DateTime(timezone=True), nullable=True)
    delta_link = Column(Text, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(String(255), nullable=False, default="anonymous")
    run_id = Column(UUID(as_uuid=True), nullable=True)
    tool = Column(String(128), nullable=False, index=True)
    args_hash = Column(String(64), nullable=False)
    request_body = Column(JSONB, nullable=True)
    status = Column(String(32), nullable=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("idx_audit_log_tool_time", "tool", "created_at"),
    )
