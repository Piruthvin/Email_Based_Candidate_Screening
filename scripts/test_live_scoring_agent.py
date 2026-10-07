"""
Test script to invoke the live iGentic Scoring Agent using credentials in backend/.env.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import httpx

# Load backend/.env
env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
load_dotenv(env_path)

EXECUTOR_URL = os.getenv("SCORING_IGENTIC_EXECUTOR_URL", "").strip()
APP_ID = os.getenv("SCORING_IGENTIC_APP_ID", "iGentic-2.0").strip()
API_KEY = os.getenv("SCORING_IGENTIC_API_KEY", "").strip()
BEARER_TOKEN = os.getenv("SCORING_IGENTIC_BEARER_TOKEN", "").strip()
USERNAME = os.getenv("SCORING_IGENTIC_USERNAME", "").strip()

print("=" * 70)
print("Testing live iGentic Scoring Agent")
print("=" * 70)
print(f"Target URL: {EXECUTOR_URL}")
print(f"App ID:     {APP_ID}")
print(f"API Key:    {API_KEY[:4]}...{API_KEY[-3:] if len(API_KEY)>6 else ''}")
print(f"Username:   {USERNAME}")
print(f"Bearer:     {BEARER_TOKEN[:15]}... (length: {len(BEARER_TOKEN)})")
print("=" * 70)

# Sample candidate facts & resume
CANDIDATE_FACTS = {
    "full_name": "Vikramaditya Bose",
    "experience_years": 4.0,
    "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Kafka", "Docker", "AWS"],
    "current_company": "CRED",
    "location": "Bengaluru",
    "notice_days_max": 30
}

JOB_PROFILE = {
    "title": "Senior Python Backend Engineer",
    "must_have_skills": ["Python", "FastAPI", "PostgreSQL", "Kafka"],
    "experience_min_years": 3.0,
    "experience_max_years": 6.0,
    "locations": ["Bengaluru", "Remote"],
    "notice_days_max": 45
}

JOB_TEXT = (
    "Looking for a Senior Python Backend Engineer with 3-6 years experience in FastAPI, "
    "PostgreSQL, Kafka, and Redis caching. Must have strong distributed systems fundamentals."
)

RESUME_TEXT = """
VIKRAMADITYA BOSE
Bengaluru, Karnataka | vikram.bose.python@talentseed.dev

SUMMARY:
Senior Python Backend Developer with 4 years of experience building high-throughput microservices
using Python, FastAPI, PostgreSQL, and Kafka.

EXPERIENCE:
CRED — Senior Python Engineer (2021 - Present)
- Designed low-latency reward service in FastAPI handling 10,000 req/sec with p99 < 35ms.
- Built event streaming pipelines using Apache Kafka and Redis caching.
- Optimized PostgreSQL queries and database indexing strategy.

SKILLS:
Python, FastAPI, Django, PostgreSQL, Redis, Kafka, Docker, Kubernetes, AWS
"""

async def test_agent():
    payload_obj = {
        "request_id": "test-live-eval-001",
        "prompt_version": "score-v1",
        "job_profile": JOB_PROFILE,
        "job_text": JOB_TEXT,
        "candidate_facts": CANDIDATE_FACTS,
        "resume_text": RESUME_TEXT,
    }

    user_input_str = json.dumps(payload_obj)

    body = {
        "userInput": user_input_str,
        "UserInputType": "",
        "sessionId": "",
        "executionId": "",
        "connectionID": "",
        "isStreaming": False,
        "Username": USERNAME,
    }

    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "x-api-key": API_KEY,
        "x-app-id": APP_ID,
        "x-username": USERNAME,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    print("\n[SENDING REQUEST TO IGENTIC EXECUTOR]...")
    timeout = httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(EXECUTOR_URL, json=body, headers=headers)
            print(f"\n[HTTP STATUS CODE]: {resp.status_code}")
            print(f"[HEADERS]: {dict(resp.headers)}")
            
            try:
                resp_json = resp.json()
                print("\n[RESPONSE JSON]:")
                print(json.dumps(resp_json, indent=2)[:1500])
            except Exception:
                print(f"\n[RAW RESPONSE BODY]: {resp.text[:1500]}")

        except httpx.RequestError as exc:
            print(f"\n[HTTP REQUEST FAILED]: {exc}")

if __name__ == "__main__":
    asyncio.run(test_agent())
