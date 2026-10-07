# Hybrid Talent Pool & Candidate Screening Backend

An intelligent, production-ready candidate profile screening backend powered by two **iGentic platform agents**:
1. **Recruiter Agent** (`Recruiter_Agent`): Conversational recruiter assistant equipped with 13 HTTP backend tools for searching candidates, comparing profiles, inspecting rubric breakdowns, and generating reports.
2. **Scoring Agent** (`Scoring_Agent`): Stateless, tool-free AI evaluator that receives an anonymized candidate resume and Job Description, and emits structured scoring JSON strictly following the evaluation rubric.

---

## 1. System Architecture

```mermaid
graph TD
    subgraph Email Ingestion Pipeline
        M365[Microsoft 365 Exchange] -->|Graph Delta Sync| SyncSvc[Graph Sync Service]
        SyncSvc -->|Store Raw EML & Parse| IngestWorker[Ingestion Worker]
        Nvite[nVitae HTML/EML Mails] --> IngestWorker
        IngestWorker -->|Redact PII & Extract Text| ResumeSvc[Resume Parser]
        IngestWorker -->|Deduplication & Cross-link| DedupeSvc[Dedupe Service]
        IngestWorker -->|Queue Scoring Jobs| ScoringQueue[(Postgres Scoring Jobs)]
    end

    subgraph Data Store (PostgreSQL)
        PG[(PostgreSQL 16)]
        Candidates[(candidates)]
        Resumes[(resumes)]
        Scores[(scores)]
        Jobs[(job_profiles)]
        Audit[(tool_audit_log)]
    end

    subgraph Scoring Pipeline
        ScoringQueue --> ScoringWorker[Scoring Worker]
        ScoringWorker --> DetailsScorer[Deterministic Details Scorer]
        ScoringWorker --> ScoringClient[Scoring Agent Client]
        ScoringClient -->|Fake Mode or iGentic API| ScoringAgent[iGentic Scoring Agent]
        ScoringAgent --> Grounding[Evidence Grounding Validator]
        Grounding --> ScoreCombiner[Score Combiner 70/30 or 100/0]
        ScoreCombiner --> Scores
    end

    subgraph Recruiter Experience
        Recruiter[Recruiter / Hiring Manager] <-->|Chat / UI| RecruiterAgent[iGentic Recruiter Agent]
        RecruiterAgent -->|13 REST Tools| ToolAPI[Tool API / FastAPI]
        ToolAPI --> PG
        ToolAPI --> ReportSvc[Excel Report Generator]
    end
```

---

## 2. Key Features

- **Dual-Scoring Formula**:
  - Combined Score: **70% Resume Evaluation** + **30% Candidate Details** (when resume text is present).
  - Renormalized Score: **100% Candidate Details** when resume is missing or unreadable (flagged with `resume_missing`).
- **Evidence Grounding Verification**: Penalizes and flags unverified claims if the scoring agent hallucinates evidence not present in the candidate's actual resume text.
- **Robust Deduplication**: Multi-tier matching (email, normalized phone, fuzzy name + company, resume content hash) with automated manual review flag generation (`duplicate_flags`).
- **Prompt Injection Defense**: Anonymized evaluation prompts and deterministic Python scoring guard against hostile resumes attempting to override evaluation weights.
- **Circuit Breaker & Budget Guard**: Daily budget enforcement and sliding-window failure tripwires prevent API runaways during batch screening.
- **Audit-Logged Tool API**: Every tool call by the Recruiter Agent is persisted with caller, parameters, duration, and status in `tool_audit_log`.

---

## 3. Quickstart

### Prerequisites
- Docker & Docker Compose (or Python 3.11+ and PostgreSQL 16)

### Option A: Running via Docker Compose (Recommended)

1. Clone repository and navigate to root:
   ```bash
   cd "P:\Projects\Igentic\Email-based candidate profile screening agent"
   ```
2. Build and start PostgreSQL and Backend:
   ```bash
   docker compose up -d --build
   ```
3. Verify liveness and readiness:
   ```bash
   curl http://localhost:8000/health
   # Response: {"status":"ok","service":"talentpool-backend"}

   curl http://localhost:8000/ready
   # Response: {"status":"ready","database":"connected"}
   ```
4. Access interactive OpenAPI documentation:
   - [http://localhost:8000/docs](http://localhost:8000/docs)

### Option B: Local Development Setup

1. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Or on Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Configure environment:
   ```bash
   cp backend/.env.example backend/.env
   # Update DATABASE_URL with your PostgreSQL credentials
   ```
4. Run Alembic migrations:
   ```bash
   cd backend
   alembic upgrade head
   ```
5. Start development server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 4. Configuration Reference (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Asynchronous SQLAlchemy connection string |
| `APP_ENV` | `development` | Environment mode (`development`, `production`, `test`) |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Public base URL for generated report download links (local or `https://<azure-container-app-fqdn>`) |
| `SCORING_AGENT_MODE` | `fake` | Scoring agent mode: `fake` (deterministic stub) or `igentic` (real iGentic app) |
| `IGENTIC_BASE_URL` | `https://api.igentic.ai` | Base URL for the iGentic API |
| `IGENTIC_API_KEY` | `""` | API key for iGentic platform authentication |
| `IGENTIC_SCORING_APP_ID` | `""` | App ID of the stateless Scoring Agent |
| `IGENTIC_RECRUITER_APP_ID` | `""` | App ID of the Recruiter Agent |
| `IGENTIC_USERNAME` | `recruiter-system` | Service username for iGentic audit headers |
| `MS_TENANT_ID` | `""` | Azure AD / Microsoft Entra Tenant ID (Optional) |
| `MS_CLIENT_ID` | `""` | Azure App Client ID for Graph Mail API (Optional) |
| `MS_CLIENT_SECRET` | `""` | Azure App Client Secret (Optional) |
| `MAILBOX_UPN` | `""` | Target mailbox User Principal Name (Optional) |
| `DAILY_BUDGET_CENTS` | `5000` | Daily scoring pipeline budget cap in cents ($50.00) |
| `RATE_LIMIT_PER_MINUTE` | `60` | Tool API rate limit threshold |

*Note: When Microsoft Graph credentials are empty or omitted, the mailbox sync gracefully runs in safe no-op mode without crashing.*

---

## 5. The Two iGentic Agents

### 1. Recruiter Agent (`Recruiter_Agent`)
- **Role**: Conversational Recruiter Assistant.
- **Prompt Specification**: [`agent-prompts/Recruiter_Agent.md`](agent-prompts/Recruiter_Agent.md).
- **Tools**: Equipped with all 13 backend REST tools defined in [`agent-prompts/TOOLS_CONFIG.md`](agent-prompts/TOOLS_CONFIG.md) and [`agent-prompts/TOOLS_REFERENCE.md`](agent-prompts/TOOLS_REFERENCE.md).
- **Behavior**: Strictly grounded in database records; verifies candidate IDs before actions; prompts for missing criteria; enforces active JD requirement before ranking.

### 2. Scoring Agent (`Scoring_Agent`)
- **Role**: Stateless Resume Evaluator.
- **Prompt Specification**: [`agent-prompts/Scoring_Agent.md`](agent-prompts/Scoring_Agent.md).
- **Tools**: **Zero tools**. Operates as a pure input-to-output evaluation engine.
- **Behavior**: Accepts an anonymized candidate resume and JD criteria; outputs strict JSON conforming to the evaluation rubric schema; resistant to prompt injections embedded in resume text.

---

## 6. Recruiter Agent 13 Tools Catalog

| # | Tool Name | HTTP Endpoint | Description |
|---|---|---|---|
| **1** | `get_pool_stats` | `POST /api/v1/tools/get_pool_stats` | Pipeline candidate totals, processing states, and active JDs. |
| **2** | `sync_mailbox` | `POST /api/v1/tools/sync_mailbox` | Trigger Graph API delta sync for candidate emails. |
| **3** | `list_job_profiles` | `POST /api/v1/tools/list_job_profiles` | List open job roles with filter by status (`draft`, `active`, `inactive`). |
| **4** | `save_job_profile` | `POST /api/v1/tools/save_job_profile` | Create or update a JD draft with structured criteria. |
| **5** | `activate_job_profile`| `POST /api/v1/tools/activate_job_profile`| Transition JD to active and queue scoring jobs for pool. |
| **6** | `deactivate_job_profile`| `POST /api/v1/tools/deactivate_job_profile`| Transition JD to inactive, cancel queued scoring jobs, preserve history. |
| **7** | `get_scoring_status` | `POST /api/v1/tools/get_scoring_status` | Query scoring queue progress and failure metrics for a JD. |
| **8** | `search_candidates` | `POST /api/v1/tools/search_candidates` | Filter candidates by skills, experience, notice period, location. |
| **9** | `get_candidate` | `POST /api/v1/tools/get_candidate` | Return comprehensive candidate dossier with scores & history. |
| **10**| `rank_candidates` | `POST /api/v1/tools/rank_candidates` | Generate frozen ranking run for active JD with custom weights. |
| **11**| `find_duplicates` | `POST /api/v1/tools/find_duplicates` | Query potential duplicate candidate records for review. |
| **12**| `merge_candidates` | `POST /api/v1/tools/merge_candidates` | Merge duplicate candidate profile into primary record. |
| **13**| `generate_report` | `POST /api/v1/tools/generate_report` | Generate downloadable formatted Excel (`.xlsx`) shortlist report. |

---

## 7. Testing & Verification

### Running Unit & Integration Tests
Execute the full pytest suite:
```bash
cd backend
python -m pytest -q
# Result: 27 passed in < 6s
```

### Running the End-to-End Recruiter Scenario Script
Verifies all 13 tools and the end-to-end recruiter workflow against live backend:
```bash
python scripts/run_recruiter_scenario.py
```
This script exercises:
1. Ingesting candidate email fixtures (`nvite_sample_1.html`, `nvite_sample_2.html`, `nvite_sample_1.eml`).
2. Checking pipeline stats (`get_pool_stats`).
3. Drafting a JD (`save_job_profile`).
4. Listing JDs (`list_job_profiles`).
5. Verifying rejection of unactivated ranking (`rank_candidates` -> HTTP 400 `JD_REQUIRED`).
6. Activating the JD (`activate_job_profile`) and batch-enqueuing scoring jobs.
7. Processing scoring queue in deterministic `fake` mode.
8. Monitoring scoring queue progress (`get_scoring_status` -> 100%).
9. Freezing candidate ranking (`rank_candidates`).
10. Inspecting candidate dossier (`get_candidate`).
11. Generating and downloading the formatted Excel report (`generate_report` -> `.xlsx`).
12. Deactivating the JD (`deactivate_job_profile`) and cancelling queued scoring jobs while preserving historical scores.
13. Reactivating the JD (`activate_job_profile`) back to active status.

### Testing iGentic Chat Integration
Once you have configured valid iGentic credentials in `backend/.env`, test conversation prompts:
```bash
python scripts/test_recruiter_agent_chat.py
```
