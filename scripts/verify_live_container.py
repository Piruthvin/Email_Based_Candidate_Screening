import httpx

base = "http://localhost:8000"

# 1. Verify OpenAPI paths
res = httpx.get(f"{base}/openapi.json")
assert res.status_code == 200, "OpenAPI fetch failed"
paths = res.json()["paths"]
print("Checking OpenAPI paths:")
for p in [
    "/api/v1/tools/list_job_profiles",
    "/api/v1/tools/activate_job_profile",
    "/api/v1/tools/deactivate_job_profile"
]:
    assert p in paths, f"Missing path {p} in OpenAPI!"
    print(f"  FOUND: {p}")

# 2. Save a fresh draft JD
import uuid
uid = uuid.uuid4().hex[:6]
jd_payload = {
    "title": f"Live Docker Test Role - Senior Cloud Architect {uid}",
    "raw_text": f"Senior Cloud Architect {uid} with 8+ years in AWS/GCP and Kubernetes",
    "structured": {
        "title": f"Senior Cloud Architect {uid}",
        "must_have_skills": ["AWS", "Kubernetes"],
        "experience_min_years": 8.0,
        "budget_lpa_max": 45.0,
        "notice_days_max": 30
    }
}
resp_save = httpx.post(f"{base}/api/v1/tools/save_job_profile", json=jd_payload)
assert resp_save.status_code == 200
saved_jd = resp_save.json()
print(f"Saved Draft JD: {saved_jd['job_profile_id']}")

# 3. List job profiles to identify the draft JD
resp_list = httpx.post(f"{base}/api/v1/tools/list_job_profiles", json={"status": "draft"})
assert resp_list.status_code == 200
draft_jds = resp_list.json()["job_profiles"]
target_jd = next((j for j in draft_jds if j["job_profile_id"] == saved_jd["job_profile_id"]), None)
assert target_jd is not None, "Target JD not found in draft list!"
print(f"Identified JD via list_job_profiles: ID={target_jd['job_profile_id']}, Title={target_jd['title']}, Status={target_jd['status']}")

real_id = target_jd["job_profile_id"]

# 4. Activate the JD
resp_act = httpx.post(f"{base}/api/v1/tools/activate_job_profile", json={"job_profile_id": real_id, "confirmed_by": "recruiter_docker_test"})
assert resp_act.status_code == 200
act_data = resp_act.json()
assert act_data["status"] == "active"
print(f"Activated JD: ID={act_data['job_profile_id']}, Status={act_data['status']}, Queued={act_data['scoring_jobs_queued']}")

# 5. Verify it appears in active list
resp_list_active = httpx.post(f"{base}/api/v1/tools/list_job_profiles", json={"status": "active"})
assert any(j["job_profile_id"] == real_id for j in resp_list_active.json()["job_profiles"])
print("Verified JD appears in active list.")

# 6. Deactivate the JD
resp_deact = httpx.post(f"{base}/api/v1/tools/deactivate_job_profile", json={
    "job_profile_id": real_id,
    "confirmed_by": "recruiter_docker_test",
    "reason": "Role filled"
})
assert resp_deact.status_code == 200
deact_data = resp_deact.json()
assert deact_data["status"] == "inactive"
print(f"Deactivated JD: ID={deact_data['job_profile_id']}, Status={deact_data['status']}, Cancelled={deact_data['cancelled_scoring_jobs']}")

# 7. Verify it appears in inactive list
resp_list_inactive = httpx.post(f"{base}/api/v1/tools/list_job_profiles", json={"status": "inactive"})
assert any(j["job_profile_id"] == real_id for j in resp_list_inactive.json()["job_profiles"])
print("Verified JD appears in inactive list.")

# 8. Reactivate the JD
resp_react = httpx.post(f"{base}/api/v1/tools/activate_job_profile", json={"job_profile_id": real_id, "confirmed_by": "recruiter_docker_test"})
assert resp_react.status_code == 200
assert resp_react.json()["status"] == "active"
print("Verified JD successfully reactivated.")

print("\n>>> ALL LIVE CONTAINER TOOL LIFECYCLE CHECKS PASSED SUCCESSFULLY! <<<")
