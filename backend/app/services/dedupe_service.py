import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Candidate, DuplicateFlag, Resume

logger = logging.getLogger(__name__)


class DedupeService:
    """
    Four-level candidate deduplication engine:
    1. Exact resume file hash match
    2. Exact email match
    3. Exact phone match
    4. Fuzzy match (Name similarity + experience or skill match) -> flags to duplicate_flags
    """

    async def find_existing_candidate(
        self,
        db: AsyncSession,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        resume_hash: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> Tuple[Optional[Candidate], Optional[str]]:
        """
        Attempts to match candidate by authoritative identifiers:
        Returns: (candidate, match_reason)
        """
        # Level 1: Resume file hash match
        if resume_hash:
            q_res = select(Resume).where(Resume.file_hash == resume_hash)
            res_row = (await db.execute(q_res)).scalars().first()
            if res_row:
                q_cand = select(Candidate).where(Candidate.id == res_row.candidate_id, Candidate.merged_into.is_(None))
                cand = (await db.execute(q_cand)).scalars().first()
                if cand:
                    return cand, "exact_resume_hash"

        # Level 2: Exact email match
        if email:
            clean_email = email.strip().lower()
            q_email = select(Candidate).where(Candidate.email == clean_email, Candidate.merged_into.is_(None))
            cand = (await db.execute(q_email)).scalars().first()
            if cand:
                return cand, "exact_email"

        # Level 3: Exact phone match
        if phone:
            clean_phone = phone.strip()
            q_phone = select(Candidate).where(Candidate.phone == clean_phone, Candidate.merged_into.is_(None))
            cand = (await db.execute(q_phone)).scalars().first()
            if cand:
                return cand, "exact_phone"

        return None, None

    async def check_and_flag_fuzzy_duplicates(
        self,
        db: AsyncSession,
        candidate: Candidate,
    ) -> List[DuplicateFlag]:
        """
        Level 4: Identifies potential duplicate candidates based on:
        - Exact or near-identical name with matching experience or skill overlaps
        Creates rows in duplicate_flags table with status='pending'.
        """
        flags_created = []
        if not candidate.full_name or len(candidate.full_name.split()) < 2:
            return flags_created

        clean_name = candidate.full_name.strip().lower()
        # Look for candidates with same name
        q = select(Candidate).where(
            Candidate.id != candidate.id,
            Candidate.merged_into.is_(None),
            Candidate.full_name.ilike(f"%{clean_name}%"),
        )
        potential_matches = (await db.execute(q)).scalars().all()

        for match in potential_matches:
            signals: Dict[str, Any] = {"name_match": True, "name_a": candidate.full_name, "name_b": match.full_name}

            # Check phone digits match without prefix
            if candidate.phone and match.phone:
                p1 = candidate.phone[-10:]
                p2 = match.phone[-10:]
                if p1 == p2:
                    signals["phone_suffix_match"] = True

            # Check experience delta
            if candidate.experience_years is not None and match.experience_years is not None:
                diff = abs(float(candidate.experience_years) - float(match.experience_years))
                if diff <= 1.0:
                    signals["experience_similar"] = True

            # Check skills overlap
            if candidate.skills and match.skills:
                set_a = {s.lower() for s in candidate.skills}
                set_b = {s.lower() for s in match.skills}
                overlap = set_a.intersection(set_b)
                if len(overlap) >= 2:
                    signals["skills_overlap"] = list(overlap)

            # Order UUIDs to prevent duplicate reverse pairs
            cand_a, cand_b = (candidate.id, match.id) if str(candidate.id) < str(match.id) else (match.id, candidate.id)

            # Check if flag already exists
            q_flag = select(DuplicateFlag).where(
                DuplicateFlag.candidate_a == cand_a,
                DuplicateFlag.candidate_b == cand_b,
            )
            existing_flag = (await db.execute(q_flag)).scalars().first()
            if not existing_flag:
                new_flag = DuplicateFlag(
                    candidate_a=cand_a,
                    candidate_b=cand_b,
                    signals=signals,
                    status="pending",
                )
                db.add(new_flag)
                flags_created.append(new_flag)

        return flags_created


dedupe_service = DedupeService()
