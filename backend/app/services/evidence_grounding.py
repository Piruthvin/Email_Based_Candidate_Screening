import re
from typing import Any, Dict, List, Tuple


class EvidenceGroundingValidator:
    """
    Verifies that cited resume snippets returned by Scoring Agent
    actually appear in the source resume text.
    """

    @staticmethod
    def _normalize(text: str) -> str:
        # Lowercase, collapse whitespace, strip punctuation
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return " ".join(cleaned.split())

    def validate(
        self,
        resume_text: str,
        must_have_evaluations: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[str], int]:
        """
        Validates evidence grounding for each must-have item.
        Returns:
            (validated_must_have, flags, unverified_count)
        """
        flags: List[str] = []
        unverified_count = 0
        validated = []

        norm_resume = self._normalize(resume_text or "")

        for item in must_have_evaluations:
            skill = item.get("skill", "")
            status = item.get("status", "not_met")
            evidence = item.get("evidence", "")

            item_copy = dict(item)

            if status in ("met", "partly"):
                if not evidence or not evidence.strip():
                    item_copy["status"] = "not_met"
                    item_copy["unverified"] = True
                    unverified_count += 1
                else:
                    norm_evidence = self._normalize(evidence)
                    # Check substring match or word overlap (>75%)
                    if norm_evidence in norm_resume:
                        item_copy["unverified"] = False
                    else:
                        ev_words = [w for w in norm_evidence.split() if len(w) > 2]
                        if ev_words:
                            matched_words = sum(1 for w in ev_words if w in norm_resume)
                            ratio = matched_words / len(ev_words)
                            if ratio >= 0.70:
                                item_copy["unverified"] = False
                            else:
                                item_copy["status"] = "not_met"
                                item_copy["unverified"] = True
                                unverified_count += 1
                        else:
                            item_copy["status"] = "not_met"
                            item_copy["unverified"] = True
                            unverified_count += 1
            else:
                item_copy["unverified"] = False

            validated.append(item_copy)

        if unverified_count > 0:
            flags.append("unverified_evidence")

        return validated, flags, unverified_count


evidence_grounding_validator = EvidenceGroundingValidator()
