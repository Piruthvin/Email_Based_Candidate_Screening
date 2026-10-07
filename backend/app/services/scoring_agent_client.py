import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ScoringRubricOutput(BaseModel):
    request_id: Optional[str] = None
    sub_scores: Dict[str, int]
    must_have: List[Dict[str, Any]]
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    reason: str
    confidence: str = "high"
    model: str = "scoring-v1"
    prompt_version: str = "score-v1"
    scorer_stub: Optional[bool] = None


class ScoringAgentClient:
    """
    Client for invoking the Scoring Agent.
    Operates in two modes:
    1. 'fake' (default): deterministic stub scorer for pipeline testing without credentials
    2. 'igentic': calls the real iGentic executor using SCORING_IGENTIC_* credentials
    """

    async def score_resume(
        self,
        request_id: str,
        job_profile: Dict[str, Any],
        job_text: str,
        candidate_facts: Dict[str, Any],
        resume_text: str,
    ) -> ScoringRubricOutput:
        settings = get_settings()
        mode = settings.scoring_agent_mode.lower().strip()

        if mode == "igentic":
            return await self._score_via_igentic(
                request_id=request_id,
                job_profile=job_profile,
                job_text=job_text,
                candidate_facts=candidate_facts,
                resume_text=resume_text,
            )
        else:
            return self._score_via_fake_stub(
                request_id=request_id,
                job_profile=job_profile,
                candidate_facts=candidate_facts,
                resume_text=resume_text,
            )

    def _score_via_fake_stub(
        self,
        request_id: str,
        job_profile: Dict[str, Any],
        candidate_facts: Dict[str, Any],
        resume_text: str,
    ) -> ScoringRubricOutput:
        """
        Deterministic stub scorer that evaluates overlap to produce a realistic rubric.
        Marked with scorer_stub=True.
        """
        must_have_skills = job_profile.get("must_have_skills") or []
        cand_skills = candidate_facts.get("skills") or []
        c_set = {s.lower().strip() for s in cand_skills}
        norm_resume = resume_text.lower()

        must_have_eval = []
        matched = []
        missing = []
        matched_count = 0

        for skill in must_have_skills:
            s_clean = skill.lower().strip()
            # Look in cand_skills or resume text
            if s_clean in c_set or s_clean in norm_resume:
                matched_count += 1
                matched.append(skill)
                # Extract evidence snippet from resume
                idx = norm_resume.find(s_clean)
                if idx != -1:
                    start = max(0, idx - 20)
                    end = min(len(resume_text), idx + len(skill) + 40)
                    evidence_snippet = resume_text[start:end].replace("\n", " ").strip()
                else:
                    evidence_snippet = f"Demonstrated {skill} in profile"

                must_have_eval.append({
                    "skill": skill,
                    "status": "met",
                    "evidence": evidence_snippet,
                })
            else:
                missing.append(skill)
                must_have_eval.append({
                    "skill": skill,
                    "status": "not_met",
                    "evidence": "",
                })

        total_must = max(1, len(must_have_skills))
        coverage_ratio = matched_count / total_must
        # Discreet 5-pt steps up to max 40
        raw_cov = round((coverage_ratio * 40) / 5) * 5
        must_have_coverage = min(40, max(0, raw_cov))

        # Experience relevance (max 25)
        cand_exp = candidate_facts.get("experience_years") or 0.0
        min_exp = job_profile.get("experience_min_years") or 0.0
        exp_rel = 25 if cand_exp >= min_exp else (15 if cand_exp >= min_exp * 0.7 else 5)

        # Domain relevance (max 20)
        domain_rel = 15 if coverage_ratio >= 0.5 else 10

        # Seniority fit (max 10)
        seniority = 10 if cand_exp >= 5 else 5

        # Education certs (max 5)
        edu = 5

        sub_scores = {
            "must_have_coverage": must_have_coverage,
            "experience_relevance": exp_rel,
            "domain_relevance": domain_rel,
            "seniority_fit": seniority,
            "education_certs": edu,
        }

        reason = (
            f"Candidate matches {matched_count} of {total_must} must-have skills ({', '.join(matched) if matched else 'None'}). "
            f"Relevant experience of {cand_exp} years evaluated against requirement."
        )

        return ScoringRubricOutput(
            request_id=request_id,
            sub_scores=sub_scores,
            must_have=must_have_eval,
            matched_skills=matched,
            missing_skills=missing,
            reason=reason,
            confidence="high",
            model="stub-scorer-v1",
            prompt_version="score-v1",
            scorer_stub=True,
        )

    async def _score_via_igentic(
        self,
        request_id: str,
        job_profile: Dict[str, Any],
        job_text: str,
        candidate_facts: Dict[str, Any],
        resume_text: str,
    ) -> ScoringRubricOutput:
        settings = get_settings()
        if not settings.is_scoring_igentic_configured:
            raise RuntimeError(
                "SCORING_AGENT_MODE=igentic configured, but SCORING_IGENTIC_* credentials are not fully populated."
            )

        payload_obj = {
            "request_id": request_id,
            "prompt_version": settings.scorer_prompt_version,
            "job_profile": job_profile,
            "job_text": job_text,
            "candidate_facts": candidate_facts,
            "resume_text": resume_text,
        }

        user_input_str = json.dumps(payload_obj)

        body = {
            "userInput": user_input_str,
            "UserInputType": "",
            "sessionId": "",
            "executionId": "",
            "connectionID": "",
            "isStreaming": False,
            "Username": settings.scoring_igentic_username or "",
        }

        headers = {
            "Authorization": f"Bearer {settings.scoring_igentic_bearer_token}",
            "x-api-key": settings.scoring_igentic_api_key or "",
            "x-app-id": settings.scoring_igentic_app_id or "iGentic-2.0",
            "x-username": settings.scoring_igentic_username or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        timeout = httpx.Timeout(connect=15.0, read=90.0, write=15.0, pool=15.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(settings.scoring_igentic_executor_url, json=body, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"iGentic Scoring Agent returned HTTP {resp.status_code}: {resp.text}")

            resp_json = resp.json()
            raw_text = self._extract_result_from_payload(resp_json)
            if not raw_text:
                raise ValueError("Empty response payload received from iGentic Scoring Agent executor")

            data_dict = self._unmarshal_json(raw_text)
            return ScoringRubricOutput.model_validate(data_dict)

    def _extract_result_from_payload(self, data: Any) -> str:
        """Extracts text output from iGentic response envelope."""
        if not isinstance(data, dict):
            return self._clean_termination_marker(str(data)) if data else ""

        # 1. responseData.result
        resp_data = data.get("responseData")
        if isinstance(resp_data, dict):
            res = resp_data.get("result")
            if res and str(res).strip():
                return self._clean_termination_marker(str(res))
            agent_resps = resp_data.get("agentResponses") or resp_data.get("AgentResponses")
            if isinstance(agent_resps, list) and agent_resps:
                last_msg = agent_resps[-1]
                if isinstance(last_msg, dict):
                    return self._clean_termination_marker(str(last_msg.get("Message") or last_msg.get("message") or ""))
                return self._clean_termination_marker(str(last_msg))

        # 2. Top-level Result / result / output
        for key in ("Result", "result", "output", "response"):
            val = data.get(key)
            if val is not None and str(val).strip():
                return self._clean_termination_marker(str(val))

        # 3. Top-level AgentResponses
        agent_resps = data.get("AgentResponses") or data.get("agentResponses")
        if isinstance(agent_resps, list) and agent_resps:
            last_msg = agent_resps[-1]
            if isinstance(last_msg, dict):
                return self._clean_termination_marker(str(last_msg.get("Message") or last_msg.get("message") or ""))
            return self._clean_termination_marker(str(last_msg))

        return ""

    @staticmethod
    def _clean_termination_marker(text: str) -> str:
        if not text:
            return ""
        return text.replace("TERMINATE THE PROCESS", "").replace("TERMINATE", "").strip()

    def _unmarshal_json(self, raw_output: Any) -> dict:
        """
        Defensively parses JSON from agent response:
        - Dict directly
        - Code fences ```json ... ```
        - Substring between outermost { ... }
        """
        if isinstance(raw_output, dict):
            return raw_output

        if not isinstance(raw_output, str):
            raise ValueError(f"Expected JSON string or dict, got {type(raw_output).__name__}")

        cleaned = self._clean_termination_marker(raw_output.strip())

        # Strip markdown fences
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
            if match:
                cleaned = match.group(1).strip()
            else:
                lines = [line for line in cleaned.splitlines() if not line.strip().startswith("```")]
                cleaned = "\n".join(lines).strip()

        # Try direct parse
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # Outer braces extraction
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            sub = cleaned[start_idx : end_idx + 1]
            try:
                parsed = json.loads(sub)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        return json.loads(cleaned)


scoring_agent_client = ScoringAgentClient()
