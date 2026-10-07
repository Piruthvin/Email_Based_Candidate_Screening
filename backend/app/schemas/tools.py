from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- Tool 1: get_pool_stats ---
class PoolStatsRequest(BaseModel):
    pass


class PoolStatsResponse(BaseModel):
    total_candidates: int
    unscored_candidates: int
    active_jds_count: int
    last_mail_received_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None


# --- Tool 2: sync_mailbox ---
class SyncMailboxRequest(BaseModel):
    mailbox: Optional[str] = None
    mode: str = "latest"


class SyncMailboxResponse(BaseModel):
    job_id: str
    status: str
    mailbox: str


# --- Tool 3: get_sync_status ---
class SyncStatusRequest(BaseModel):
    job_id: str


class SyncStatusResponse(BaseModel):
    job_id: str
    status: str
    new_mails: int
    new_candidates: int
    existing_candidates_new_application: int
    duplicate_flags: int
    last_mail_received_at: Optional[datetime] = None
    delta_link_present: bool = False


# --- Tool 3: list_job_profiles ---
class ListJobProfilesRequest(BaseModel):
    status: Optional[str] = None  # draft | active | inactive | None for all
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class JobProfileSummaryItem(BaseModel):
    job_profile_id: str
    title: str
    status: str
    version: int
    content_hash: str
    must_have_skills: List[str] = Field(default_factory=list)
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    locations: List[str] = Field(default_factory=list)
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None


class ListJobProfilesResponse(BaseModel):
    job_profiles: List[JobProfileSummaryItem]
    total: int


# --- Tool 4: save_job_profile ---
class SaveJobProfileRequest(BaseModel):
    title: str
    raw_text: str
    structured: Dict[str, Any]
    parent_id: Optional[str] = None


class SaveJobProfileResponse(BaseModel):
    job_profile_id: str
    status: str
    title: str
    version: int
    content_hash: str
    parsed_summary: Dict[str, Any]


# --- Tool 5: activate_job_profile ---
class ActivateJobProfileRequest(BaseModel):
    job_profile_id: str
    confirmed_by: Optional[str] = "recruiter"
    confirmed_changes: Optional[Dict[str, Any]] = None


class ActivateJobProfileResponse(BaseModel):
    job_profile_id: str
    status: str
    scoring_jobs_queued: int
    message: Optional[str] = None


# --- Tool 6: deactivate_job_profile ---
class DeactivateJobProfileRequest(BaseModel):
    job_profile_id: str
    confirmed_by: Optional[str] = "recruiter"
    reason: Optional[str] = None


class DeactivateJobProfileResponse(BaseModel):
    job_profile_id: str
    status: str
    cancelled_scoring_jobs: int
    deactivated_at: datetime
    message: str


# --- Tool 6: get_scoring_status ---
class ScoringStatusRequest(BaseModel):
    job_profile_id: str


class ScoringStatusResponse(BaseModel):
    job_profile_id: str
    total_jobs: int
    queued: int
    running: int
    complete: int
    failed: int
    scored_pct: float
    eta_hint: str


# --- Tool 7: search_candidates (NO ranking, NO scores) ---
class CandidateFilter(BaseModel):
    notice_days_max: Optional[int] = None
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    location: Optional[str] = None
    skills: Optional[List[str]] = None
    received_after: Optional[datetime] = None


class SearchCandidatesRequest(BaseModel):
    filters: Optional[CandidateFilter] = None
    sort_keys: Optional[List[str]] = Field(default_factory=lambda: ["received_at"])
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class CandidateSummaryItem(BaseModel):
    candidate_id: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    headline: Optional[str] = None
    current_company: Optional[str] = None
    experience_years: Optional[float] = None
    current_ctc_lpa: Optional[float] = None
    notice_days_max: Optional[int] = None
    location: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    last_seen_at: datetime


class SearchCandidatesResponse(BaseModel):
    candidates: List[CandidateSummaryItem]
    total: int


# --- Tool 8: get_candidate ---
class GetCandidateRequest(BaseModel):
    candidate_id: Optional[str] = None
    name: Optional[str] = None


class CandidateDossierResponse(BaseModel):
    disambiguation: bool = False
    candidates: Optional[List[CandidateSummaryItem]] = None
    candidate_id: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    headline: Optional[str] = None
    current_company: Optional[str] = None
    experience_years: Optional[float] = None
    current_ctc_lpa: Optional[float] = None
    notice_raw: Optional[str] = None
    notice_days_max: Optional[int] = None
    location: Optional[str] = None
    preferred_locations: List[str] = Field(default_factory=list)
    education: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    applications: List[Dict[str, Any]] = Field(default_factory=list)
    scores: List[Dict[str, Any]] = Field(default_factory=list)
    resume_available: bool = False


# --- Tool 9: rank_candidates ---
class RankCandidatesRequest(BaseModel):
    job_profile_id: str
    top_n: int = Field(default=10, ge=1, le=50)
    rank_by: str = Field(default="final")  # final | resume | details | custom
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    sort_keys: Optional[List[str]] = Field(default_factory=list)


class RankedCandidateItem(BaseModel):
    rank_position: int
    candidate_id: str
    full_name: str
    final_score: float
    details_score: float
    resume_score: Optional[float] = None
    reason: Optional[str] = None
    missing_skills: List[str] = Field(default_factory=list)
    notice_days_max: Optional[int] = None
    experience_years: Optional[float] = None
    location: Optional[str] = None


class RankCandidatesResponse(BaseModel):
    run_id: str
    job_profile_id: str
    rank_by: str
    top_n: int
    scored_pct: float
    pending_count: int
    ranked: List[RankedCandidateItem]


# --- Tool 10: find_duplicates ---
class FindDuplicatesRequest(BaseModel):
    status: str = "pending"  # pending | resolved | ignored


class DuplicateFlagItem(BaseModel):
    flag_id: str
    candidate_a_id: str
    candidate_a_name: str
    candidate_b_id: str
    candidate_b_name: str
    signals: Dict[str, Any]
    status: str
    created_at: datetime


class FindDuplicatesResponse(BaseModel):
    duplicates: List[DuplicateFlagItem]


# --- Tool 11: merge_candidates ---
class MergeCandidatesRequest(BaseModel):
    flag_id: Optional[str] = None
    primary_id: Optional[str] = None
    duplicate_id: Optional[str] = None


class MergeCandidatesResponse(BaseModel):
    merged_candidate_id: str
    status: str
    re_score_queued: bool


# --- Tool 12: generate_report ---
class GenerateReportRequest(BaseModel):
    run_id: str
    format: str = "xlsx"  # xlsx | pdf | docx
    columns: Optional[List[str]] = None


class GenerateReportResponse(BaseModel):
    run_id: str
    format: str
    filename: str
    total_rows: int
    download_url: str


# --- Consistent Error Shape ---
class ApiErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: Optional[str] = None
