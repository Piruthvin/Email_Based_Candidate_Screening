"""
Interactive / Automated Test Harness for Recruiter Agent via iGentic Platform API.

Reads credentials from backend/.env:
- IGENTIC_BASE_URL
- IGENTIC_API_KEY
- IGENTIC_RECRUITER_APP_ID
- IGENTIC_USERNAME

If credentials are present, sends conversational prompts to the iGentic Recruiter Agent endpoint
and streams/prints the response.
If credentials are not configured, runs a simulated verification mode against the local Tool API.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env
env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
load_dotenv(env_path)

IGENTIC_BASE_URL = os.getenv("IGENTIC_BASE_URL", "").strip().rstrip("/")
IGENTIC_API_KEY = os.getenv("IGENTIC_API_KEY", "").strip()
IGENTIC_RECRUITER_APP_ID = os.getenv("IGENTIC_RECRUITER_APP_ID", "").strip()
IGENTIC_USERNAME = os.getenv("IGENTIC_USERNAME", "").strip()

DEFAULT_PROMPTS = [
    "Hi, can you give me an overview of our current candidate pipeline and processing status?",
    "Show me the top candidates for Senior Data Engineer.",
    "Show me profile details for Rajesh Kumar."
]

async def call_igentic_recruiter_agent(user_message: str) -> str:
    import httpx
    
    url = f"{IGENTIC_BASE_URL}/chat"
    headers = {
        "Authorization": f"Bearer {IGENTIC_API_KEY}",
        "x-api-key": IGENTIC_API_KEY,
        "x-app-id": IGENTIC_RECRUITER_APP_ID,
        "x-username": IGENTIC_USERNAME,
        "Content-Type": "application/json"
    }
    payload = {
        "userInput": user_message,
        "isStreaming": False
    }

    print(f"\n[USER PROMPT] >> {user_message}")
    print(f"[SENDING] POST {url} (App: {IGENTIC_RECRUITER_APP_ID})...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            reply = data.get("response") or data.get("message") or json.dumps(data, indent=2)
            print(f"[RECRUITER AGENT] >>\n{reply}\n")
            return reply
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] HTTP {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            raise

async def verify_local_tools_fallback():
    """Verify tool endpoints when iGentic credentials are not configured."""
    import httpx
    print("\n" + "=" * 60)
    print("iGentic credentials are empty or unconfigured.")
    print("Running Local Tool API verification test instead...")
    print("=" * 60)
    
    base_url = "http://localhost:8000/api/v1/tools"
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Check health
        try:
            health = await client.get("http://localhost:8000/health")
            print(f"[*] Tool API Health: {health.status_code} -> {health.json()}")
        except Exception as e:
            print(f"[!] Tool API not running on http://localhost:8000: {e}")
            print("    Please start the backend with `uvicorn app.main:app` or docker compose.")
            return

        # Check get_pipeline_stats
        try:
            res = await client.post(f"{base_url}/get_pipeline_stats", json={})
            print(f"[*] Tool `get_pipeline_stats`: {res.status_code} -> {res.json()}")
        except Exception as e:
            print(f"[!] Tool test error: {e}")

async def main():
    has_creds = bool(
        IGENTIC_BASE_URL and 
        IGENTIC_API_KEY and 
        IGENTIC_RECRUITER_APP_ID and 
        IGENTIC_USERNAME and
        not IGENTIC_API_KEY.startswith("<")
    )

    if not has_creds:
        print("[NOTICE] Real iGentic platform credentials not set in backend/.env.")
        print(f"  IGENTIC_BASE_URL: '{IGENTIC_BASE_URL}'")
        print(f"  IGENTIC_RECRUITER_APP_ID: '{IGENTIC_RECRUITER_APP_ID}'")
        print(f"  IGENTIC_USERNAME: '{IGENTIC_USERNAME}'")
        print("To test against the live iGentic agent, update backend/.env with your valid credentials.\n")
        await verify_local_tools_fallback()
        return

    print("=" * 60)
    print("iGentic Recruiter Agent Chat Test Harness")
    print(f"Target: {IGENTIC_BASE_URL} | App: {IGENTIC_RECRUITER_APP_ID}")
    print("=" * 60)

    # Run default prompts
    for prompt in DEFAULT_PROMPTS:
        try:
            await call_igentic_recruiter_agent(prompt)
        except Exception:
            break

if __name__ == "__main__":
    asyncio.run(main())
