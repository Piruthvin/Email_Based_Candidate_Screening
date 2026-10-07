from typing import Any, Dict, List, Optional, Tuple


class DetailsScorer:
    """
    Deterministic Python evaluation of structured candidate metadata against JD requirements.
    Missing attributes are omitted and remaining weights are renormalized.
    """

    DEFAULT_WEIGHTS = {
        "skills": 0.35,
        "experience": 0.25,
        "notice": 0.20,
        "location": 0.10,
        "budget": 0.10,
    }

    def compute_details_score(
        self,
        candidate_facts: Dict[str, Any],
        jd_requirements: Dict[str, Any],
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        weights = custom_weights or self.DEFAULT_WEIGHTS
        parts: Dict[str, Optional[float]] = {}

        # 1. Skills Overlap
        parts["skills"] = self._compute_skills_score(
            candidate_skills=candidate_facts.get("skills") or [],
            must_have=jd_requirements.get("must_have_skills") or [],
            nice_to_have=jd_requirements.get("nice_to_have_skills") or [],
        )

        # 2. Experience Fit
        parts["experience"] = self._compute_experience_score(
            candidate_exp=candidate_facts.get("experience_years"),
            min_exp=jd_requirements.get("experience_min_years"),
            max_exp=jd_requirements.get("experience_max_years"),
        )

        # 3. Notice Period Fit
        parts["notice"] = self._compute_notice_score(
            notice_days_max=candidate_facts.get("notice_days_max"),
        )

        # 4. Location Fit
        parts["location"] = self._compute_location_score(
            cand_location=candidate_facts.get("location"),
            cand_preferred=candidate_facts.get("preferred_locations") or [],
            jd_locations=jd_requirements.get("locations") or [],
            remote_ok=jd_requirements.get("remote_ok", False),
        )

        # 5. Budget Fit
        parts["budget"] = self._compute_budget_score(
            expected_ctc=candidate_facts.get("expected_ctc_lpa"),
            budget_max=jd_requirements.get("budget_lpa_max"),
        )

        # Renormalize weights across present factors
        present = {k: v for k, v in parts.items() if v is not None}
        if not present:
            return 0.0, {}

        w_sum = sum(weights.get(k, 0.0) for k in present)
        if w_sum <= 0:
            return 0.0, parts

        total_score = sum(weights.get(k, 0.0) * v for k, v in present.items()) / w_sum
        return round(total_score, 2), parts

    def _compute_skills_score(
        self,
        candidate_skills: List[str],
        must_have: List[str],
        nice_to_have: List[str],
    ) -> Optional[float]:
        if not must_have and not nice_to_have:
            return None

        c_set = {s.lower().strip() for s in candidate_skills if s}
        m_set = {s.lower().strip() for s in must_have if s}
        n_set = {s.lower().strip() for s in nice_to_have if s}

        m_matched = len(c_set.intersection(m_set))
        n_matched = len(c_set.intersection(n_set))

        denominator = len(m_set) + 0.5 * len(n_set)
        if denominator == 0:
            return 100.0

        numerator = m_matched + 0.5 * n_matched
        score = (numerator / denominator) * 100.0
        return round(min(100.0, max(0.0, score)), 2)

    def _compute_experience_score(
        self,
        candidate_exp: Optional[float],
        min_exp: Optional[float],
        max_exp: Optional[float],
    ) -> Optional[float]:
        if candidate_exp is None or (min_exp is None and max_exp is None):
            return None

        c_exp = float(candidate_exp)
        low = float(min_exp) if min_exp is not None else 0.0
        high = float(max_exp) if max_exp is not None else 100.0

        if low <= c_exp <= high:
            return 100.0
        elif c_exp < low:
            # -15 per year shortfall
            shortfall = low - c_exp
            return max(0.0, round(100.0 - 15.0 * shortfall, 2))
        else:
            # -15 per year overqualified
            excess = c_exp - high
            return max(0.0, round(100.0 - 15.0 * excess, 2))

    def _compute_notice_score(self, notice_days_max: Optional[int]) -> Optional[float]:
        if notice_days_max is None:
            return None

        days = int(notice_days_max)
        if days <= 0:
            return 100.0
        elif days <= 15:
            return 90.0
        elif days <= 30:
            return 70.0
        elif days <= 60:
            return 40.0
        else:
            return 20.0

    def _compute_location_score(
        self,
        cand_location: Optional[str],
        cand_preferred: List[str],
        jd_locations: List[str],
        remote_ok: bool,
    ) -> Optional[float]:
        if not jd_locations and not remote_ok:
            return None

        jd_locs = {l.lower().strip() for l in jd_locations if l}
        c_locs = {l.lower().strip() for l in cand_preferred if l}
        if cand_location:
            c_locs.add(cand_location.lower().strip())

        # Exact match or substring match
        matched = False
        for cl in c_locs:
            for jl in jd_locs:
                if cl in jl or jl in cl:
                    matched = True
                    break
            if matched:
                break

        if matched:
            return 100.0
        if remote_ok:
            return 70.0
        return 0.0

    def _compute_budget_score(
        self,
        expected_ctc: Optional[float],
        budget_max: Optional[float],
    ) -> Optional[float]:
        if expected_ctc is None or budget_max is None or budget_max <= 0:
            return None

        exp = float(expected_ctc)
        b_max = float(budget_max)

        if exp <= b_max:
            return 100.0
        elif exp <= 1.10 * b_max:
            return 60.0
        else:
            return 20.0


details_scorer = DetailsScorer()
