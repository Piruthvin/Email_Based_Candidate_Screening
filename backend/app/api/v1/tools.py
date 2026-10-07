import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import audit_tool_call
from app.schemas.tools import (
    ActivateJobProfileRequest,
    ActivateJobProfileResponse,
    CandidateDossierResponse,
    DeactivateJobProfileRequest,
    DeactivateJobProfileResponse,
    FindDuplicatesRequest,
    FindDuplicatesResponse,
    GenerateReportRequest,
    GenerateReportResponse,
    GetCandidateRequest,
    ListJobProfilesRequest,
    ListJobProfilesResponse,
    MergeCandidatesRequest,
    MergeCandidatesResponse,
    PoolStatsRequest,
    PoolStatsResponse,
    RankCandidatesRequest,
    RankCandidatesResponse,
    SaveJobProfileRequest,
    SaveJobProfileResponse,
    ScoringStatusRequest,
    ScoringStatusResponse,
    SearchCandidatesRequest,
    SearchCandidatesResponse,
    SyncMailboxRequest,
    SyncMailboxResponse,
    SyncStatusRequest,
    SyncStatusResponse,
)
from app.services.tool_service import tool_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["Recruiter Agent Tools"])


# --- Tool 1: get_pool_stats ---
@router.post(
    "/get_pool_stats",
    response_model=PoolStatsResponse,
    summary="Get Talent Pool Statistics",
    description="Aggregates metrics across all candidates, unscored applications, active JDs, and mailbox sync status.",
)
async def get_pool_stats(
    request: Request,
    payload: Optional[PoolStatsRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.get_pool_stats(db)
        await audit_tool_call(db, "get_pool_stats", request, payload.model_dump() if payload else {}, status="success")
        return res
    except Exception as e:
        await audit_tool_call(db, "get_pool_stats", request, payload.model_dump() if payload else {}, status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 2: sync_mailbox ---
@router.post(
    "/sync_mailbox",
    response_model=SyncMailboxResponse,
    summary="Synchronize Mailbox",
    description="Initiates an asynchronous mailbox synchronization run against Microsoft Graph delta stream.",
)
async def sync_mailbox(
    request: Request,
    payload: SyncMailboxRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.sync_mailbox(db, mailbox=payload.mailbox, mode=payload.mode)
        await audit_tool_call(db, "sync_mailbox", request, payload.model_dump(), status="success")
        return res
    except Exception as e:
        await audit_tool_call(db, "sync_mailbox", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 3: get_sync_status ---
@router.post(
    "/get_sync_status",
    response_model=SyncStatusResponse,
    summary="Get Mailbox Sync Progress",
    description="Retrieves the real-time execution status and discovered candidate counters for a specific sync job.",
)
async def get_sync_status(
    request: Request,
    payload: SyncStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.get_sync_status(db, job_id=payload.job_id)
        await audit_tool_call(db, "get_sync_status", request, payload.model_dump(), status="success")
        return res
    except ValueError as e:
        await audit_tool_call(db, "get_sync_status", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "detail": str(e)})
    except Exception as e:
        await audit_tool_call(db, "get_sync_status", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 3: list_job_profiles ---
@router.post(
    "/list_job_profiles",
    response_model=ListJobProfilesResponse,
    summary="List Job Profiles",
    description="Lists all Job Descriptions with their status (draft, active, inactive), metadata, and required skills.",
)
async def list_job_profiles(
    request: Request,
    payload: Optional[ListJobProfilesRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        p = payload or ListJobProfilesRequest()
        res = await tool_service.list_job_profiles(
            db,
            status=p.status,
            limit=p.limit,
            offset=p.offset,
        )
        await audit_tool_call(db, "list_job_profiles", request, p.model_dump(), status="success")
        return res
    except Exception as e:
        await audit_tool_call(db, "list_job_profiles", request, payload.model_dump() if payload else {}, status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 4: save_job_profile ---
@router.post(
    "/save_job_profile",
    response_model=SaveJobProfileResponse,
    summary="Save Draft Job Profile",
    description="Parses and saves a Job Description in draft status with SHA-256 canonical hashing for idempotency.",
)
async def save_job_profile(
    request: Request,
    payload: SaveJobProfileRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.save_job_profile(
            db,
            title=payload.title,
            raw_text=payload.raw_text,
            structured=payload.structured,
            parent_id=payload.parent_id,
        )
        await audit_tool_call(db, "save_job_profile", request, payload.model_dump(), status="success")
        return res
    except Exception as e:
        await audit_tool_call(db, "save_job_profile", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 5: activate_job_profile ---
@router.post(
    "/activate_job_profile",
    response_model=ActivateJobProfileResponse,
    summary="Activate Job Profile",
    description="Transitions a job profile from draft (or inactive) to active and bulk-enqueues scoring jobs for all existing pool candidates.",
)
async def activate_job_profile(
    request: Request,
    payload: ActivateJobProfileRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.activate_job_profile(
            db,
            job_profile_id=payload.job_profile_id,
            confirmed_by=payload.confirmed_by,
            confirmed_changes=payload.confirmed_changes,
        )
        await audit_tool_call(db, "activate_job_profile", request, payload.model_dump(), status="success")
        return res
    except ValueError as e:
        msg = str(e)
        status_code = 404 if "NOT_FOUND" in msg else 400
        error_code = msg.split(":")[0].strip() if ":" in msg else "INVALID_REQUEST"
        await audit_tool_call(db, "activate_job_profile", request, payload.model_dump(), status="error", error=msg)
        raise HTTPException(status_code=status_code, detail={"error": error_code, "detail": msg})
    except Exception as e:
        await audit_tool_call(db, "activate_job_profile", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 6: deactivate_job_profile ---
@router.post(
    "/deactivate_job_profile",
    response_model=DeactivateJobProfileResponse,
    summary="Deactivate Job Profile",
    description="Transitions an active job profile to inactive and cancels any pending queued scoring jobs while preserving historical scores.",
)
async def deactivate_job_profile(
    request: Request,
    payload: DeactivateJobProfileRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.deactivate_job_profile(
            db,
            job_profile_id=payload.job_profile_id,
            confirmed_by=payload.confirmed_by,
            reason=payload.reason,
        )
        await audit_tool_call(db, "deactivate_job_profile", request, payload.model_dump(), status="success")
        return res
    except ValueError as e:
        msg = str(e)
        status_code = 404 if "NOT_FOUND" in msg else 400
        error_code = msg.split(":")[0].strip() if ":" in msg else "INVALID_REQUEST"
        await audit_tool_call(db, "deactivate_job_profile", request, payload.model_dump(), status="error", error=msg)
        raise HTTPException(status_code=status_code, detail={"error": error_code, "detail": msg})
    except Exception as e:
        await audit_tool_call(db, "deactivate_job_profile", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 6: get_scoring_status ---
@router.post(
    "/get_scoring_status",
    response_model=ScoringStatusResponse,
    summary="Get Scoring Progress",
    description="Monitors background evaluation progress and calculates completion percentage for an active JD.",
)
async def get_scoring_status(
    request: Request,
    payload: ScoringStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.get_scoring_status(db, job_profile_id=payload.job_profile_id)
        await audit_tool_call(db, "get_scoring_status", request, payload.model_dump(), status="success")
        return res
    except ValueError as e:
        await audit_tool_call(db, "get_scoring_status", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "detail": str(e)})
    except Exception as e:
        await audit_tool_call(db, "get_scoring_status", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 7: search_candidates (NO ranking, NO scores) ---
@router.post(
    "/search_candidates",
    response_model=SearchCandidatesResponse,
    summary="Search Candidates Without Scores",
    description="Queries and filters candidate pool metadata without ranking or scoring them.",
)
async def search_candidates(
    request: Request,
    payload: SearchCandidatesRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.search_candidates(
            db,
            filters=payload.filters,
            sort_keys=payload.sort_keys,
            limit=payload.limit,
            offset=payload.offset,
        )
        await audit_tool_call(db, "search_candidates", request, payload.model_dump(), status="success")
        return res
    except Exception as e:
        await audit_tool_call(db, "search_candidates", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 8: get_candidate ---
@router.post(
    "/get_candidate",
    response_model=CandidateDossierResponse,
    summary="Get Candidate Dossier",
    description="Fetches comprehensive profile details, application timeline, Q&A, and scores per active JD; returns disambiguation if name matches multiple.",
)
async def get_candidate(
    request: Request,
    payload: GetCandidateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.get_candidate(db, candidate_id=payload.candidate_id, name=payload.name)
        await audit_tool_call(db, "get_candidate", request, payload.model_dump(), status="success")
        return res
    except ValueError as e:
        await audit_tool_call(db, "get_candidate", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "detail": str(e)})
    except Exception as e:
        await audit_tool_call(db, "get_candidate", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 9: rank_candidates ---
@router.post(
    "/rank_candidates",
    response_model=RankCandidatesResponse,
    summary="Rank Candidates",
    description="Ranks candidates against an active JD and freezes the result into an immutable ranking run. Returns JD_REQUIRED error if no active JD.",
)
async def rank_candidates(
    request: Request,
    payload: RankCandidatesRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.rank_candidates(
            db,
            job_profile_id=payload.job_profile_id,
            top_n=payload.top_n,
            rank_by=payload.rank_by,
            filters=payload.filters,
            sort_keys=payload.sort_keys,
        )
        await audit_tool_call(db, "rank_candidates", request, payload.model_dump(), status="success")
        return res
    except ValueError as e:
        err_msg = str(e)
        status_code = 400 if "JD_REQUIRED" in err_msg else 404
        await audit_tool_call(db, "rank_candidates", request, payload.model_dump(), status="error", error=err_msg)
        raise HTTPException(
            status_code=status_code,
            detail={"error": "JD_REQUIRED" if "JD_REQUIRED" in err_msg else "INVALID_REQUEST", "detail": err_msg},
        )
    except Exception as e:
        await audit_tool_call(db, "rank_candidates", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 10: find_duplicates ---
@router.post(
    "/find_duplicates",
    response_model=FindDuplicatesResponse,
    summary="Find Duplicate Candidate Flags",
    description="Queries flagged duplicate candidate pairs pending recruiter review and resolution.",
)
async def find_duplicates(
    request: Request,
    payload: FindDuplicatesRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.find_duplicates(db, status=payload.status)
        await audit_tool_call(db, "find_duplicates", request, payload.model_dump(), status="success")
        return res
    except Exception as e:
        await audit_tool_call(db, "find_duplicates", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 11: merge_candidates ---
@router.post(
    "/merge_candidates",
    response_model=MergeCandidatesResponse,
    summary="Merge Candidate Records",
    description="Merges a duplicate candidate into a primary record, re-points applications and resumes, and queues re-scoring if needed.",
)
async def merge_candidates(
    request: Request,
    payload: MergeCandidatesRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.merge_candidates(
            db,
            flag_id=payload.flag_id,
            primary_id=payload.primary_id,
            duplicate_id=payload.duplicate_id,
        )
        await audit_tool_call(db, "merge_candidates", request, payload.model_dump(), status="success")
        return res
    except ValueError as e:
        await audit_tool_call(db, "merge_candidates", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=400, detail={"error": "INVALID_REQUEST", "detail": str(e)})
    except Exception as e:
        await audit_tool_call(db, "merge_candidates", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})


# --- Tool 12: generate_report ---
@router.post(
    "/generate_report",
    response_model=GenerateReportResponse,
    summary="Generate Shortlist Report",
    description="Generates a downloadable Excel (.xlsx) report from a frozen ranking run.",
)
async def generate_report(
    request: Request,
    payload: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await tool_service.generate_report(
            db,
            run_id=payload.run_id,
            format=payload.format,
            columns=payload.columns,
        )
        await audit_tool_call(db, "generate_report", request, payload.model_dump(), status="success")
        return res
    except ValueError as e:
        await audit_tool_call(db, "generate_report", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "detail": str(e)})
    except Exception as e:
        await audit_tool_call(db, "generate_report", request, payload.model_dump(), status="error", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "SERVER_ERROR", "detail": str(e)})
