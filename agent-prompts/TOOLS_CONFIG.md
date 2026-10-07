# Recruiter Agent Tool Configuration Specification (`TOOLS_CONFIG.md`)

> **Notice:** This document is the **architectural design and API reference**. For the copy-pasteable, mustache-templated guide ready for the iGentic platform dashboard, please consult:
> **[`agent-prompts/TOOLS_REFERENCE.md`](./TOOLS_REFERENCE.md)**.

---

## 1. Overview & Architectural Principles

All tools for the **Recruiter Agent** are exposed as standard HTTP `POST` endpoints by the FastAPI backend under the base prefix `/api/v1/tools/`.

- **Transport:** HTTP `POST`
- **Serialization:** JSON (`application/json`)
- **Authentication:** Unrestricted / fully open during this phase per project Override 5. Any client or platform can invoke these endpoints directly.
- **Audit Logging:** Every invocation is hashed and recorded in `audit_log` with arguments hash, tool name, execution status, and timestamp.
- **Error Standard:** All errors return HTTP 4xx/5xx with `{ "error": "<ERROR_CODE>", "detail": "<Human readable description>" }`.

---

## 2. Inventory of the 13 HTTP Tools

### 1. `get_pool_stats`
- **Route:** `POST /api/v1/tools/get_pool_stats`
- **Purpose:** Database health and pipeline metrics aggregation.
- **Request Body:** `{}`
- **Response Schema:**
  ```typescript
  interface PoolStatsResponse {
    total_candidates: number;
    unscored_candidates: number;
    active_jds_count: number;
    last_mail_received_at: string | null;
    last_sync_at: string | null;
  }
  ```

### 2. `sync_mailbox`
- **Route:** `POST /api/v1/tools/sync_mailbox`
- **Purpose:** Triggers on-demand Microsoft Graph mailbox delta synchronization.
- **Request Schema:**
  ```typescript
  interface SyncMailboxRequest {
    mailbox?: string;
    mode: "latest" | "all";
  }
  ```
- **Response Schema:**
  ```typescript
  interface SyncMailboxResponse {
    job_id: string;
    status: "running" | "success" | "failed";
    mailbox: string;
  }
  ```

### 3. `list_job_profiles`
- **Route:** `POST /api/v1/tools/list_job_profiles`
- **Purpose:** Lists all Job Profiles with status (`draft`, `active`, `inactive`), experience bounds, and must-have skills.
- **Request Schema:**
  ```typescript
  interface ListJobProfilesRequest {
    status?: "draft" | "active" | "inactive";
    limit?: number;
    offset?: number;
  }
  ```
- **Response Schema:**
  ```typescript
  interface JobProfileSummaryItem {
    job_profile_id: string;
    title: string;
    status: "draft" | "active" | "inactive";
    version: number;
    content_hash: string;
    must_have_skills: string[];
    experience_min_years?: number;
    experience_max_years?: number;
    locations: string[];
    created_at: string;
    confirmed_at?: string;
    confirmed_by?: string;
  }

  interface ListJobProfilesResponse {
    job_profiles: JobProfileSummaryItem[];
    total: number;
  }
  ```

### 4. `save_job_profile`
- **Route:** `POST /api/v1/tools/save_job_profile`
- **Purpose:** Idempotent draft JD creation with SHA-256 canonical hashing.
- **Request Schema:**
  ```typescript
  interface SaveJobProfileRequest {
    title: string;
    raw_text: string;
    structured: {
      title?: string;
      must_have_skills: string[];
      nice_to_have_skills?: string[];
      experience_min_years?: number;
      experience_max_years?: number;
      budget_lpa_max?: number;
      locations?: string[];
      remote_ok?: boolean;
      notice_days_max?: number;
    };
    parent_id?: string;
  }
  ```
- **Response Schema:**
  ```typescript
  interface SaveJobProfileResponse {
    job_profile_id: string;
    status: "draft";
    title: string;
    version: number;
    content_hash: string;
    parsed_summary: Record<string, any>;
  }
  ```

### 5. `activate_job_profile`
- **Route:** `POST /api/v1/tools/activate_job_profile`
- **Purpose:** Confirms draft/inactive JD, flips to active, and enqueues scoring jobs for all candidate pool members.
- **Request Schema:**
  ```typescript
  interface ActivateJobProfileRequest {
    job_profile_id: string;
    confirmed_by?: string;
    confirmed_changes?: Record<string, any>;
  }
  ```
- **Response Schema:**
  ```typescript
  interface ActivateJobProfileResponse {
    job_profile_id: string;
    status: "active";
    scoring_jobs_queued: number;
    message?: string;
  }
  ```

### 6. `deactivate_job_profile`
- **Route:** `POST /api/v1/tools/deactivate_job_profile`
- **Purpose:** Transitions an active JD to inactive, cancelling queued scoring jobs while preserving historical scores and rankings.
- **Request Schema:**
  ```typescript
  interface DeactivateJobProfileRequest {
    job_profile_id: string;
    confirmed_by?: string;
    reason?: string;
  }
  ```
- **Response Schema:**
  ```typescript
  interface DeactivateJobProfileResponse {
    job_profile_id: string;
    status: "inactive";
    cancelled_scoring_jobs: number;
    deactivated_at: string;
    message: string;
  }
  ```

### 7. `get_scoring_status`
- **Route:** `POST /api/v1/tools/get_scoring_status`
- **Purpose:** Progress monitoring for background candidate evaluations against a JD.
- **Request Schema:**
  ```typescript
  interface ScoringStatusRequest {
    job_profile_id: string;
  }
  ```
- **Response Schema:**
  ```typescript
  interface ScoringStatusResponse {
    job_profile_id: string;
    total_jobs: number;
    queued: number;
    running: number;
    complete: number;
    failed: number;
    scored_pct: number;
    eta_hint: string;
  }
  ```

### 8. `search_candidates`
- **Route:** `POST /api/v1/tools/search_candidates`
- **Purpose:** Metadata search and filtering without ranking or scoring.
- **Request Schema:**
  ```typescript
  interface SearchCandidatesRequest {
    filters?: {
      notice_days_max?: number;
      experience_min_years?: number;
      experience_max_years?: number;
      location?: string;
      skills?: string[];
      received_after?: string;
    };
    sort_keys?: string[];
    limit?: number; // 1 to 50
    offset?: number;
  }
  ```
- **Response Schema:**
  ```typescript
  interface SearchCandidatesResponse {
    candidates: Array<{
      candidate_id: string;
      full_name: string;
      email?: string;
      phone?: string;
      headline?: string;
      current_company?: string;
      experience_years?: number;
      current_ctc_lpa?: number;
      notice_days_max?: number;
      location?: string;
      skills: string[];
      last_seen_at: string;
    }>;
    total: number;
  }
  ```

### 9. `get_candidate`
- **Route:** `POST /api/v1/tools/get_candidate`
- **Purpose:** Comprehensive candidate profile, timeline, answers, and scores. Prompts for disambiguation if name matches multiple applicants.
- **Request Schema:**
  ```typescript
  interface GetCandidateRequest {
    candidate_id?: string;
    name?: string;
  }
  ```
- **Response Schema:**
  ```typescript
  interface CandidateDossierResponse {
    disambiguation: boolean;
    candidates?: Array<any>;
    candidate_id?: string;
    full_name?: string;
    email?: string;
    phone?: string;
    headline?: string;
    current_company?: string;
    experience_years?: number;
    current_ctc_lpa?: number;
    notice_days_max?: number;
    location?: string;
    preferred_locations: string[];
    education?: string;
    skills: string[];
    applications: Array<any>;
    scores: Array<any>;
    resume_available: boolean;
  }
  ```

### 10. `rank_candidates`
- **Route:** `POST /api/v1/tools/rank_candidates`
- **Purpose:** Ranks candidates against an active JD and freezes the shortlist in an immutable ranking run.
- **Request Schema:**
  ```typescript
  interface RankCandidatesRequest {
    job_profile_id: string;
    top_n?: number; // 10, 20, 30, max 50
    rank_by?: "final" | "resume" | "details";
    filters?: Record<string, any>;
    sort_keys?: string[];
  }
  ```
- **Response Schema:**
  ```typescript
  interface RankCandidatesResponse {
    run_id: string;
    job_profile_id: string;
    rank_by: string;
    top_n: number;
    scored_pct: number;
    pending_count: number;
    ranked: Array<{
      rank_position: number;
      candidate_id: string;
      full_name: string;
      final_score: number;
      details_score: number;
      resume_score?: number;
      reason?: string;
      missing_skills: string[];
      notice_days_max?: number;
      experience_years?: number;
      location?: string;
    }>;
  }
  ```

### 11. `find_duplicates`
- **Route:** `POST /api/v1/tools/find_duplicates`
- **Purpose:** Queries flagged duplicate candidates requiring recruiter confirmation.
- **Request Schema:**
  ```typescript
  interface FindDuplicatesRequest {
    status?: "pending" | "resolved" | "ignored";
  }
  ```
- **Response Schema:**
  ```typescript
  interface FindDuplicatesResponse {
    duplicates: Array<{
      flag_id: string;
      candidate_a_id: string;
      candidate_a_name: string;
      candidate_b_id: string;
      candidate_b_name: string;
      signals: Record<string, any>;
      status: string;
      created_at: string;
    }>;
  }
  ```

### 12. `merge_candidates`
- **Route:** `POST /api/v1/tools/merge_candidates`
- **Purpose:** Merges duplicate profile into primary record. Re-points applications and resumes.
- **Request Schema:**
  ```typescript
  interface MergeCandidatesRequest {
    flag_id?: string;
    primary_id?: string;
    duplicate_id?: string;
  }
  ```
- **Response Schema:**
  ```typescript
  interface MergeCandidatesResponse {
    merged_candidate_id: string;
    status: "merged";
    re_score_queued: boolean;
  }
  ```

### 13. `generate_report`
- **Route:** `POST /api/v1/tools/generate_report`
- **Purpose:** Generates a formatted Excel workbook (`.xlsx`) snapshot from a frozen ranking run.
- **Request Schema:**
  ```typescript
  interface GenerateReportRequest {
    run_id: string;
    format?: "xlsx" | "pdf" | "docx";
    columns?: string[];
  }
  ```
- **Response Schema:**
  ```typescript
  interface GenerateReportResponse {
    run_id: string;
    format: string;
    filename: string;
    total_rows: number;
    download_url: string;
  }
  ```
