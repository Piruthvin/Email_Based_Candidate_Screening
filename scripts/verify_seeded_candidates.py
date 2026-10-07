"""
Verification Script for Seeded Candidates via the Tool API
Tests:
1. Health & Readiness probes
2. Listing candidates & pagination (offset, limit)
3. Candidate search with filters:
   - Skill-based filtering (e.g. PySpark, React, Docker, Python)
   - Experience range filtering (Freshers <= 1y, Senior >= 8y)
   - Notice period filtering (<= 15 days)
   - Location filtering (Bengaluru, Hyderabad, Chennai)
4. Candidate dossier retrieval (get_candidate by ID and by Name)
5. Verification of resume presence, applications, and serialization integrity
"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def main():
    print("=" * 70)
    print("Testing Candidate Retrieval & Filtering through Application Tool API")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Health & Readiness
        resp_h = await client.get("/health")
        resp_r = await client.get("/ready")
        print(f"[*] /health: {resp_h.status_code} -> {resp_h.json()}")
        print(f"[*] /ready:  {resp_r.status_code} -> {resp_r.json()}")
        assert resp_h.status_code == 200, "Health check failed"
        assert resp_r.status_code == 200, "Readiness check failed"

        # 2. Pagination test: search_candidates
        print("\n--- Test 1: Candidate Listing & Pagination (limit=5, offset=0) ---")
        resp = await client.post("/api/v1/tools/search_candidates", json={"limit": 5, "offset": 0})
        assert resp.status_code == 200, f"Error: {resp.text}"
        data = resp.json()
        print(f"Total candidates in pool: {data['total']}, returned in page: {len(data['candidates'])}")
        for c in data["candidates"]:
            print(f"  - {c['full_name']:<22} | {c['current_company'] or 'N/A':<18} | Exp: {c['experience_years']}y | CTC: {c['current_ctc_lpa']} LPA")

        # 3. Skill-based Filtering: PySpark
        print("\n--- Test 2: Skill Filter: ['PySpark'] ---")
        resp = await client.post("/api/v1/tools/search_candidates", json={
            "filters": {"skills": ["PySpark"]},
            "limit": 10
        })
        assert resp.status_code == 200
        pyspark_data = resp.json()
        print(f"Matched PySpark Candidates: {pyspark_data['total']}")
        for c in pyspark_data["candidates"]:
            print(f"  - {c['full_name']} ({c['headline']}) -> Skills: {c['skills']}")
            assert any("PySpark" in s for s in c["skills"]), "PySpark not in skills"

        # 4. Skill-based Filtering: React
        print("\n--- Test 3: Skill Filter: ['React'] ---")
        resp = await client.post("/api/v1/tools/search_candidates", json={
            "filters": {"skills": ["React"]},
            "limit": 10
        })
        assert resp.status_code == 200
        react_data = resp.json()
        print(f"Matched React Candidates: {react_data['total']}")
        for c in react_data["candidates"]:
            print(f"  - {c['full_name']} | Exp: {c['experience_years']}y | Skills: {c['skills']}")

        # 5. Experience Filter: Freshers (<= 1.0 years)
        print("\n--- Test 4: Experience Filter: <= 1.0 years (Freshers) ---")
        resp = await client.post("/api/v1/tools/search_candidates", json={
            "filters": {"experience_max_years": 1.0},
            "limit": 10
        })
        assert resp.status_code == 200
        fresher_data = resp.json()
        print(f"Matched Freshers (<= 1.0y): {fresher_data['total']}")
        for c in fresher_data["candidates"]:
            print(f"  - {c['full_name']:<22} | Exp: {c['experience_years']}y | Role: {c['headline']}")
            assert float(c["experience_years"]) <= 1.0, f"Candidate {c['full_name']} has > 1.0y exp"

        # 6. Experience Filter: Senior / Principal (>= 8.0 years)
        print("\n--- Test 5: Experience Filter: >= 8.0 years (Senior/Principal/Architects) ---")
        resp = await client.post("/api/v1/tools/search_candidates", json={
            "filters": {"experience_min_years": 8.0},
            "limit": 10
        })
        assert resp.status_code == 200
        senior_data = resp.json()
        print(f"Matched Senior Candidates (>= 8.0y): {senior_data['total']}")
        for c in senior_data["candidates"]:
            print(f"  - {c['full_name']:<24} | Exp: {c['experience_years']}y | Current: {c['current_company']}")
            assert float(c["experience_years"]) >= 8.0, f"Candidate {c['full_name']} has < 8.0y exp"

        # 7. Notice Period Filter: Immediate / <= 15 days
        print("\n--- Test 6: Notice Period Filter: <= 15 Days ---")
        resp = await client.post("/api/v1/tools/search_candidates", json={
            "filters": {"notice_days_max": 15},
            "limit": 10
        })
        assert resp.status_code == 200
        quick_data = resp.json()
        print(f"Matched Candidates with Notice <= 15 Days: {quick_data['total']}")
        for c in quick_data["candidates"]:
            print(f"  - {c['full_name']:<22} | Notice: {c['notice_days_max']} days | Location: {c['location']}")
            assert c["notice_days_max"] <= 15

        # 8. Location Filter: Bengaluru
        print("\n--- Test 7: Location Filter: 'Bengaluru' ---")
        resp = await client.post("/api/v1/tools/search_candidates", json={
            "filters": {"location": "Bengaluru"},
            "limit": 10
        })
        assert resp.status_code == 200
        blr_data = resp.json()
        print(f"Matched Candidates in/preferred Bengaluru: {blr_data['total']}")
        for c in blr_data["candidates"][:5]:
            print(f"  - {c['full_name']:<22} | Loc: {c['location']}")

        # 9. Individual Candidate Dossier Retrieval by Name: "Preeti Chadha"
        print("\n--- Test 8: Get Candidate Dossier by Name: 'Preeti Chadha' ---")
        resp = await client.post("/api/v1/tools/get_candidate", json={"name": "Preeti Chadha"})
        assert resp.status_code == 200, f"Error: {resp.text}"
        preeti = resp.json()
        print(f"Retrieved Dossier for: {preeti['full_name']}")
        print(f"  - Email: {preeti['email']}")
        print(f"  - Phone: {preeti['phone']}")
        print(f"  - Current Title: {preeti['headline']}")
        print(f"  - Experience: {preeti['experience_years']} years")
        print(f"  - Current CTC: {preeti['current_ctc_lpa']} LPA")
        print(f"  - Education: {preeti['education']}")
        print(f"  - Resume Available: {preeti['resume_available']}")
        print(f"  - Applications Count: {len(preeti['applications'])}")
        assert preeti["resume_available"] is True
        assert len(preeti["applications"]) > 0

        # 10. Individual Candidate Dossier Retrieval by ID
        print("\n--- Test 9: Get Candidate Dossier by Candidate ID ---")
        cand_id = preeti["candidate_id"]
        resp = await client.post("/api/v1/tools/get_candidate", json={"candidate_id": cand_id})
        assert resp.status_code == 200
        by_id_data = resp.json()
        assert by_id_data["full_name"] == "Preeti Chadha"
        print(f"Successfully verified dossier retrieval by ID: {cand_id}")

        # 11. Disambiguation check (Searching ambiguous partial name e.g. "Varma")
        print("\n--- Test 10: Disambiguation Check on Name 'Varma' ---")
        resp = await client.post("/api/v1/tools/get_candidate", json={"name": "Varma"})
        assert resp.status_code == 200
        disam_data = resp.json()
        print(f"Disambiguation flag: {disam_data['disambiguation']}")
        if disam_data["disambiguation"]:
            print(f"Disambiguation candidates found: {len(disam_data['candidates'])}")
            for m in disam_data["candidates"]:
                print(f"  - Candidate: {m['full_name']} ({m['email']})")

    print("\n" + "=" * 70)
    print("ALL API VERIFICATION TESTS PASSED CLEANLY WITH ZERO ERRORS!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
