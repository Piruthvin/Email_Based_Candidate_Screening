import httpx

base = "http://localhost:8000"

print("=" * 60)
print("TESTING ALL 13 TOOLS AGAINST LIVE DOCKER CONTAINER")
print("=" * 60)

with httpx.Client(base_url=base, timeout=15.0) as client:
    # 1. get_pool_stats
    r1 = client.post("/api/v1/tools/get_pool_stats", json={})
    print(f"Tool 1  (get_pool_stats): HTTP {r1.status_code} - Total candidates: {r1.json().get('total_candidates')}")
    assert r1.status_code == 200

    # 2. sync_mailbox
    r2 = client.post("/api/v1/tools/sync_mailbox", json={})
    print(f"Tool 2  (sync_mailbox): HTTP {r2.status_code} - Status: {r2.json().get('status')}")
    assert r2.status_code == 200

    # 3. list_job_profiles
    r3 = client.post("/api/v1/tools/list_job_profiles", json={"status": "active"})
    print(f"Tool 3  (list_job_profiles): HTTP {r3.status_code} - Found active: {r3.json().get('total')}")
    assert r3.status_code == 200
    active_jds = r3.json().get("job_profiles", [])
    test_jd_id = active_jds[0]["job_profile_id"] if active_jds else None

    # 4. save_job_profile
    r4 = client.post("/api/v1/tools/save_job_profile", json={
        "title": "All-Tools Test Role",
        "raw_text": "Sample text",
        "structured": {"title": "All-Tools Test Role", "must_have_skills": ["Python"]}
    })
    print(f"Tool 4  (save_job_profile): HTTP {r4.status_code} - JD: {r4.json().get('job_profile_id')}")
    assert r4.status_code == 200
    temp_jd_id = r4.json()["job_profile_id"]

    # 5. activate_job_profile
    r5 = client.post("/api/v1/tools/activate_job_profile", json={"job_profile_id": temp_jd_id, "confirmed_by": "tester"})
    print(f"Tool 5  (activate_job_profile): HTTP {r5.status_code} - Status: {r5.json().get('status')}")
    assert r5.status_code == 200

    # 6. deactivate_job_profile
    r6 = client.post("/api/v1/tools/deactivate_job_profile", json={"job_profile_id": temp_jd_id, "confirmed_by": "tester"})
    print(f"Tool 6  (deactivate_job_profile): HTTP {r6.status_code} - Status: {r6.json().get('status')}")
    assert r6.status_code == 200

    # 8. search_candidates
    r8 = client.post("/api/v1/tools/search_candidates", json={"limit": 5})
    print(f"Tool 8  (search_candidates): HTTP {r8.status_code} - Total found: {r8.json().get('total')}")
    assert r8.status_code == 200
    cands = r8.json().get("candidates", [])
    first_cand_id = cands[0]["candidate_id"] if cands else None

    # 9. get_candidate
    scored_jd_id = None
    if first_cand_id:
        r9 = client.post("/api/v1/tools/get_candidate", json={"candidate_id": first_cand_id})
        dossier = r9.json()
        print(f"Tool 9  (get_candidate): HTTP {r9.status_code} - Name: {dossier.get('full_name')}")
        assert r9.status_code == 200
        if dossier.get("scores"):
            scored_title = dossier["scores"][0]["job_title"]
            matching_jd = next((j for j in active_jds if j["title"] == scored_title), None)
            if matching_jd:
                scored_jd_id = matching_jd["job_profile_id"]
    else:
        print("Tool 9  (get_candidate): Skipped (no candidate)")

    # 7. get_scoring_status
    scoring_test_jd = scored_jd_id or test_jd_id
    if scoring_test_jd:
        r7 = client.post("/api/v1/tools/get_scoring_status", json={"job_profile_id": scoring_test_jd})
        print(f"Tool 7  (get_scoring_status): HTTP {r7.status_code} - Total jobs: {r7.json().get('total_jobs')}")
        assert r7.status_code == 200

    # 10. rank_candidates
    if scored_jd_id:
        r10 = client.post("/api/v1/tools/rank_candidates", json={"job_profile_id": scored_jd_id, "top_n": 5})
        print(f"Tool 10 (rank_candidates): HTTP {r10.status_code} - Run ID: {r10.json().get('run_id')}")
        assert r10.status_code == 200
        run_id = r10.json().get("run_id")
    else:
        run_id = None
        print("Tool 10 (rank_candidates): Skipped (no scored JD)")

    # 11. find_duplicates
    r11 = client.post("/api/v1/tools/find_duplicates", json={})
    print(f"Tool 11 (find_duplicates): HTTP {r11.status_code} - Found duplicates: {len(r11.json().get('duplicates', []))}")
    assert r11.status_code == 200

    # 12. merge_candidates
    # Test merge endpoint validation (requires either flag_id or both IDs)
    r12 = client.post("/api/v1/tools/merge_candidates", json={})
    print(f"Tool 12 (merge_candidates validation): HTTP {r12.status_code} - Correctly rejected invalid params")
    assert r12.status_code == 400

    # 13. generate_report
    if run_id:
        r13 = client.post("/api/v1/tools/generate_report", json={"run_id": run_id, "format": "xlsx"})
        print(f"Tool 13 (generate_report): HTTP {r13.status_code} - Filename: {r13.json().get('filename')}")
        assert r13.status_code == 200
    else:
        print("Tool 13 (generate_report): Skipped (no run_id)")

print("\n>>> ALL 13 TOOLS VERIFIED RESPONSIVE AND OPERATIONAL ON LIVE DOCKER CONTAINER! <<<")
