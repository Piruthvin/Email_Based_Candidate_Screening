# iGentic Tools Reference Guide (Authoritative Dashboard Configuration)

> **Document Purpose:** This is the **authoritative, iGentic-dashboard-ready reference guide** for configuring the **13 HTTP tools** in the iGentic platform portal for `Recruiter_Agent`. Every tool payload below is formatted using iGentic's native runtime template-variable syntax (`{{variable_name}}` with quotes `"{{var}}"` for strings, and unquoted `{{var}}` for numbers/integers/booleans). For architectural background and Pydantic schemas, refer to `agent-prompts/TOOLS_CONFIG.md`.
>
> **Setup Note:** In the iGentic dashboard, create `Recruiter_Agent` as an independent app and attach these 13 tools to it. `Scoring_Agent` is a completely separate app that has ZERO tools.

---

## Tool 1: Get Pool Stats

**Name:** `get_pool_stats`

**Description:** Retrieves aggregate statistics across the candidate database, including total candidates, unscored candidates, active JDs count, and last mail sync timestamp.

**Endpoint:** http://localhost:8000/api/v1/tools/get_pool_stats

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{}
```

**How to call this tool correctly:**
Call this when the recruiter asks "how many candidates do we have?", "what is the pool status?", or wants an overview of the talent pipeline before running shortlists.

**Sample response:**
```json
{
  "total_candidates": 142,
  "unscored_candidates": 18,
  "active_jds_count": 3,
  "last_mail_received_at": "2026-10-07T10:45:00Z",
  "last_sync_at": "2026-10-07T10:46:12Z"
}
```

---

## Tool 2: Sync Mailbox

**Name:** `sync_mailbox`

**Description:** Triggers an on-demand mailbox synchronization against Microsoft Graph delta stream to pull new candidate application emails.

**Endpoint:** http://localhost:8000/api/v1/tools/sync_mailbox

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{
  "mailbox": "{{mailbox}}",
  "mode": "{{mode}}"
}
```

**How to call this tool correctly:**
Call this when the recruiter commands "sync mailbox", "check for new applicant emails", or "update recent applications". `mailbox` can be empty string `""` to use the default configured mailbox, and `mode` should be `"latest"`.

**Sample response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "status": "running",
  "mailbox": "careers@acmecorp.com"
}
```

---

## Tool 3: List Job Profiles

**Name:** `list_job_profiles`

**Description:** Retrieves all Job Profiles in the system, with optional filtering by lifecycle status (`draft`, `active`, `inactive`).

**Endpoint:** http://localhost:8000/api/v1/tools/list_job_profiles

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{
  "status": "{{status}}"
}
```

**How to call this tool correctly:**
Call this when the recruiter asks to see open jobs, find draft JDs for activation, or inspect active roles before deactivation. Pass `"draft"` to find unactivated JDs, `"active"` for active JDs, or empty string `""` to list all.

**Sample response:**
```json
{
  "job_profiles": [
    {
      "job_profile_id": "b7c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e",
      "title": "Lead Python Architect",
      "status": "draft",
      "version": 1,
      "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "must_have_skills": ["Python", "FastAPI", "PostgreSQL"],
      "experience_min_years": 8.0,
      "experience_max_years": 12.0,
      "locations": ["Bangalore"],
      "created_at": "2026-10-07T10:45:00Z",
      "confirmed_at": null,
      "confirmed_by": null
    }
  ],
  "total": 1
}
```

---

## Tool 4: Save Job Profile

**Name:** `save_job_profile`

**Description:** Parses and stores a Job Description in draft status with SHA-256 canonical hashing for idempotency.

**Endpoint:** http://localhost:8000/api/v1/tools/save_job_profile

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{
  "title": "{{title}}",
  "raw_text": "{{raw_text}}",
  "structured": {
    "title": "{{title}}",
    "must_have_skills": ["{{must_have_1}}", "{{must_have_2}}"],
    "experience_min_years": {{experience_min_years}},
    "experience_max_years": {{experience_max_years}},
    "budget_lpa_max": {{budget_lpa_max}},
    "locations": ["{{location}}"]
  }
}
```

**How to call this tool correctly:**
Call this immediately when a recruiter submits or edits a Job Description. This saves the requisition as a `draft`. You must show the parsed summary to the recruiter for confirmation before activating it.

**Sample response:**
```json
{
  "job_profile_id": "b7c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e",
  "status": "draft",
  "title": "Senior Python Developer",
  "version": 1,
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "parsed_summary": {
    "must_have_skills": ["Python", "FastAPI", "PostgreSQL"],
    "experience_min_years": 5.0,
    "experience_max_years": 9.0,
    "budget_lpa_max": 25.0
  }
}
```

---

## Tool 5: Activate Job Profile

**Name:** `activate_job_profile`

**Description:** Transitions a draft or inactive Job Profile to active status and enqueues scoring jobs for all candidates in the talent pool.

**Endpoint:** http://localhost:8000/api/v1/tools/activate_job_profile

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{
  "job_profile_id": "{{job_profile_id}}",
  "confirmed_by": "{{confirmed_by}}"
}
```

**How to call this tool correctly:**
Call this ONLY AFTER the recruiter has reviewed the draft JD details and explicitly confirmed activation.

**Sample response:**
```json
{
  "job_profile_id": "b7c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e",
  "status": "active",
  "scoring_jobs_queued": 142,
  "message": "Job profile 'Lead Python Architect' is now active. 142 scoring jobs queued."
}
```

---

## Tool 6: Deactivate Job Profile

**Name:** `deactivate_job_profile`

**Description:** Transitions an active Job Profile to inactive status, cancelling any pending queued scoring jobs while preserving all historical scores and rankings.

**Endpoint:** http://localhost:8000/api/v1/tools/deactivate_job_profile

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{
  "job_profile_id": "{{job_profile_id}}",
  "confirmed_by": "{{confirmed_by}}",
  "reason": "{{reason}}"
}
```

**How to call this tool correctly:**
Call this when the recruiter asks to close, pause, or deactivate an active job role. Always verify the JD ID first via `list_job_profiles(status="active")` and confirm with the recruiter.

**Sample response:**
```json
{
  "job_profile_id": "b7c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e",
  "status": "inactive",
  "cancelled_scoring_jobs": 14,
  "deactivated_at": "2026-10-07T11:00:00Z",
  "message": "Job profile 'Lead Python Architect' is now inactive. 14 queued scoring jobs were cancelled. Historical scores and ranking runs are preserved."
}
```

---

## Tool 7: Get Scoring Status

**Name:** `get_scoring_status`

**Description:** Checks background candidate evaluation progress and percentage completion for an active Job Profile.

**Endpoint:** http://localhost:8000/api/v1/tools/get_scoring_status

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{
  "job_profile_id": "{{job_profile_id}}"
}
```

**How to call this tool correctly:**
Call this when checking if scoring has completed for a newly activated JD, or when the recruiter asks about evaluation progress.

**Sample response:**
```json
{
  "job_profile_id": "b7c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e",
  "total_jobs": 142,
  "queued": 12,
  "running": 2,
  "complete": 128,
  "failed": 0,
  "scored_pct": 90.1,
  "eta_hint": "~28s remaining"
}
```

---

## Tool 8: Search Candidates

**Name:** `search_candidates`

**Description:** Searches candidate metadata using filters (notice period, experience, skills, location) WITHOUT scoring or ranking.

**Endpoint:** http://localhost:8000/api/v1/tools/search_candidates

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{
  "filters": {
    "notice_days_max": {{notice_days_max}},
    "experience_min_years": {{experience_min_years}},
    "skills": ["{{skill_keyword}}"]
  },
  "limit": {{limit}},
  "offset": {{offset}}
}
```

**How to call this tool correctly:**
Call this when the recruiter asks to filter or inspect candidates without specifying an active JD (e.g. "show candidates who can join in 15 days").

**Sample response:**
```json
{
  "candidates": [
    {
      "candidate_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
      "full_name": "Rahul Sharma",
      "email": "rahul.sharma.dev@gmail.com",
      "phone": "+919876543210",
      "headline": "Senior Backend Engineer",
      "current_company": "Tech Mahindra Ltd",
      "experience_years": 6.5,
      "current_ctc_lpa": 18.5,
      "notice_days_max": 15,
      "location": "Bangalore",
      "skills": ["Python", "FastAPI", "PostgreSQL"],
      "last_seen_at": "2026-10-07T10:45:00Z"
    }
  ],
  "total": 1
}
```

---

## Tool 9: Get Candidate

**Name:** `get_candidate`

**Description:** Retrieves a comprehensive candidate dossier, application timeline, Q&A responses, and rubric scores per active JD; prompts for disambiguation if multiple match by name.

**Endpoint:** http://localhost:8000/api/v1/tools/get_candidate

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{
  "candidate_id": "{{candidate_id}}",
  "name": "{{name}}"
}
```

**How to call this tool correctly:**
Call this when a recruiter asks for detailed history, answers, or scores for a specific person. Provide either `candidate_id` or `name`.

**Sample response:**
```json
{
  "disambiguation": false,
  "candidate_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
  "full_name": "Rahul Sharma",
  "email": "rahul.sharma.dev@gmail.com",
  "headline": "Senior Backend Engineer",
  "experience_years": 6.5,
  "notice_days_max": 15,
  "location": "Bangalore",
  "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
  "applications": [
    {
      "job_title": "Senior Python Developer",
      "received_at": "2026-10-07T10:45:00Z",
      "expected_ctc_lpa": 24.0
    }
  ],
  "scores": [
    {
      "job_title": "Senior Python Developer",
      "final_score": 91.2,
      "details_score": 94.0,
      "resume_score": 89.3,
      "reason": "6.5 years experience, strong FastAPI background",
      "missing_skills": []
    }
  ],
  "resume_available": true
}
```

---

## Tool 10: Rank Candidates

**Name:** `rank_candidates`

**Description:** Returns Top N scored candidates for an active Job Profile and freezes the shortlist in an immutable ranking run. Returns JD_REQUIRED error if no active JD exists.

**Endpoint:** http://localhost:8000/api/v1/tools/rank_candidates

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{
  "job_profile_id": "{{job_profile_id}}",
  "top_n": {{top_n}},
  "rank_by": "{{rank_by}}"
}
```

**How to call this tool correctly:**
Call this when the recruiter requests a ranked shortlist ("top 10", "top 20", "rank based on resume"). `top_n` can be 10, 20, 30, 40 (max 50). `rank_by` can be `"final"`, `"resume"`, or `"details"`.

**Sample response:**
```json
{
  "run_id": "r9a8b7c6-d5e4-3f2a-1b0c-9d8e7f6a5b4c",
  "job_profile_id": "b7c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e",
  "rank_by": "final",
  "top_n": 10,
  "scored_pct": 100.0,
  "pending_count": 0,
  "ranked": [
    {
      "rank_position": 1,
      "candidate_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
      "full_name": "Rahul Sharma",
      "final_score": 91.2,
      "details_score": 94.0,
      "resume_score": 89.3,
      "reason": "6.5 yrs exp, expert in FastAPI and PostgreSQL",
      "missing_skills": [],
      "notice_days_max": 15,
      "experience_years": 6.5,
      "location": "Bangalore"
    }
  ]
}
```

---

## Tool 11: Find Duplicates

**Name:** `find_duplicates`

**Description:** Queries candidate pairs flagged as potential duplicates for recruiter review.

**Endpoint:** http://localhost:8000/api/v1/tools/find_duplicates

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{
  "status": "{{status}}"
}
```

**How to call this tool correctly:**
Call this when the recruiter asks to inspect flagged duplicates. Default `status` is `"pending"`.

**Sample response:**
```json
{
  "duplicates": [
    {
      "flag_id": "d1e2f3a4-b5c6-7d8e-9f0a-1b2c3d4e5f6a",
      "candidate_a_id": "c1...",
      "candidate_a_name": "Karthik Subramanian",
      "candidate_b_id": "c2...",
      "candidate_b_name": "Karthik Subramanian",
      "signals": {
        "name_match": true,
        "phone_suffix_match": true,
        "skills_overlap": ["Python", "Django"]
      },
      "status": "pending",
      "created_at": "2026-10-07T10:45:00Z"
    }
  ]
}
```

---

## Tool 12: Merge Candidates

**Name:** `merge_candidates`

**Description:** Merges a duplicate candidate into a primary record, re-points applications and resumes, and marks the duplicate as merged.

**Endpoint:** http://localhost:8000/api/v1/tools/merge_candidates

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{
  "flag_id": "{{flag_id}}",
  "primary_id": "{{primary_id}}",
  "duplicate_id": "{{duplicate_id}}"
}
```

**How to call this tool correctly:**
Call this when a recruiter confirms merging two duplicate profiles. Pass `flag_id` or both `primary_id` and `duplicate_id`.

**Sample response:**
```json
{
  "merged_candidate_id": "c1...",
  "status": "merged",
  "re_score_queued": true
}
```

---

## Tool 13: Generate Report

**Name:** `generate_report`

**Description:** Generates a downloadable Excel workbook (`.xlsx`) snapshot from a frozen ranking run.

**Endpoint:** http://localhost:8000/api/v1/tools/generate_report

**Method:** POST

**Headers:**
- Content-Type: application/json
- No authentication header is mandatory.

**Payload:**
```json
{
  "run_id": "{{run_id}}",
  "format": "{{format}}"
}
```

**How to call this tool correctly:**
Call this when the recruiter asks to download or export the ranked shortlist. `run_id` is the frozen run ID returned by `rank_candidates`. `format` is `"xlsx"`.

**Sample response:**
```json
{
  "run_id": "r9a8b7c6-d5e4-3f2a-1b0c-9d8e7f6a5b4c",
  "format": "xlsx",
  "filename": "ranking_report_r9a8b7c6.xlsx",
  "total_rows": 10,
  "download_url": "http://localhost:8000/api/v1/reports/download/ranking_report_r9a8b7c6.xlsx"
}
```
