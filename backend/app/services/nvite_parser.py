import re
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup


class NViteParsedProfile:
    def __init__(
        self,
        full_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        headline: Optional[str] = None,
        current_company: Optional[str] = None,
        experience_years: Optional[float] = None,
        current_ctc_lpa: Optional[float] = None,
        expected_ctc_lpa: Optional[float] = None,
        notice_raw: Optional[str] = None,
        notice_days_max: Optional[int] = None,
        location: Optional[str] = None,
        preferred_locations: Optional[List[str]] = None,
        skills: Optional[List[str]] = None,
        education: Optional[str] = None,
        job_title: Optional[str] = None,
        answers: Optional[List[Dict[str, str]]] = None,
        is_recognized: bool = True,
    ):
        self.full_name = full_name
        self.email = email
        self.phone = phone
        self.headline = headline
        self.current_company = current_company
        self.experience_years = experience_years
        self.current_ctc_lpa = current_ctc_lpa
        self.expected_ctc_lpa = expected_ctc_lpa
        self.notice_raw = notice_raw
        self.notice_days_max = notice_days_max
        self.location = location
        self.preferred_locations = preferred_locations or []
        self.skills = skills or []
        self.education = education
        self.job_title = job_title
        self.answers = answers or []
        self.is_recognized = is_recognized

    def to_dict(self) -> Dict[str, Any]:
        return {
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "headline": self.headline,
            "current_company": self.current_company,
            "experience_years": self.experience_years,
            "current_ctc_lpa": self.current_ctc_lpa,
            "expected_ctc_lpa": self.expected_ctc_lpa,
            "notice_raw": self.notice_raw,
            "notice_days_max": self.notice_days_max,
            "location": self.location,
            "preferred_locations": self.preferred_locations,
            "skills": self.skills,
            "education": self.education,
            "job_title": self.job_title,
            "answers": self.answers,
            "is_recognized": self.is_recognized,
        }


class NViteParser:
    """
    Parser for Naukri NVite and email applications.
    Extracts structured fields from HTML or plain-text email bodies.
    """

    @staticmethod
    def parse_notice_days(raw: Optional[str]) -> Optional[int]:
        if not raw:
            return None
        text = raw.lower().strip()
        if "immediate" in text or "serving" in text and "0" in text:
            return 0
        if "15 day" in text or "15day" in text:
            return 15
        if "1 month" in text or "30 day" in text or "30day" in text:
            return 30
        if "2 month" in text or "60 day" in text or "60day" in text:
            return 60
        if "3 month" in text or "90 day" in text or "90day" in text:
            return 90

        match = re.search(r"(\d+)\s*(?:day|days|d)", text)
        if match:
            return int(match.group(1))

        match_month = re.search(r"(\d+)\s*(?:month|months|m)", text)
        if match_month:
            return int(match_month.group(1)) * 30

        return None

    @staticmethod
    def parse_ctc(raw: Optional[str]) -> Optional[float]:
        if not raw:
            return None
        # Handle "18.5 LPA", "20.0 Lakhs", "15,00,000", etc.
        text = raw.replace(",", "").strip()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lpa|lakh|lakhs|lac|lacs)?", text, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if val > 10000:  # Absolute INR like 1800000
                return round(val / 100000.0, 2)
            return round(val, 2)
        return None

    @staticmethod
    def parse_experience(raw: Optional[str]) -> Optional[float]:
        if not raw:
            return None
        text = raw.strip()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:year|years|yr|yrs)?", text, re.IGNORECASE)
        if match:
            return round(float(match.group(1)), 1)
        return None

    @staticmethod
    def normalize_phone(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        cleaned = re.sub(r"[^\d+]", "", raw.strip())
        if cleaned.startswith("0"):
            cleaned = "+91" + cleaned[1:]
        elif not cleaned.startswith("+") and len(cleaned) == 10:
            cleaned = "+91" + cleaned
        return cleaned

    def parse(self, html_content: Optional[str], text_content: Optional[str] = None, subject: Optional[str] = None) -> NViteParsedProfile:
        content = html_content or text_content or ""
        soup = BeautifulSoup(content, "html.parser")

        extracted: Dict[str, Any] = {}
        answers: List[Dict[str, str]] = []

        # 1. Check for table rows (common Naukri table layout)
        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                key = cells[0].get_text(separator=" ", strip=True).lower()
                val = cells[1].get_text(separator=" ", strip=True)
                self._map_key_val(key, val, extracted)

        # 2. Check for paragraph or list item lines with strong/b tags: <p><strong>Key:</strong> Value</p>
        for elem in soup.find_all(["p", "li"]):
            # Ignore parent containers that wrap other blocks
            if elem.find(["table", "ul", "ol"]):
                continue
            strong = elem.find(["strong", "b"])
            if strong:
                key_text = strong.get_text(separator=" ", strip=True).lower().rstrip(":")
                # Value is text after the strong tag
                val_text = elem.get_text(separator=" ", strip=True)
                strong_raw = strong.get_text(strip=True)
                if strong_raw in val_text:
                    val_text = val_text.replace(strong_raw, "", 1).strip().lstrip(":- ")
                if key_text and val_text:
                    if "?" in key_text or "question" in key_text or len(key_text.split()) > 3:
                        answers.append({"question": key_text, "answer": val_text})
                    else:
                        self._map_key_val(key_text, val_text, extracted)

        # 3. Fallback extraction via regex on plain text
        full_text = soup.get_text(separator="\n", strip=True)
        if not extracted.get("full_name"):
            name_m = re.search(r"(?:Candidate Name|Name)\s*[:\-]?\s*([A-Za-z\s]{2,40})", full_text, re.IGNORECASE)
            if name_m:
                extracted["full_name"] = name_m.group(1).strip()

        if not extracted.get("email"):
            email_m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", full_text)
            if email_m:
                extracted["email"] = email_m.group(0).strip().lower()

        if not extracted.get("phone"):
            phone_m = re.search(r"(?:\+?91[\-\s]?)?[6-9]\d{9}", full_text)
            if phone_m:
                extracted["phone"] = self.normalize_phone(phone_m.group(0))

        # Check job title from subject or extracted text
        job_title = extracted.get("job_title")
        if not job_title and subject:
            subj_m = re.search(r"for\s+([^-\|:]+?)\s*(?:-|–|\||$)", subject, re.IGNORECASE)
            if subj_m:
                job_title = subj_m.group(1).strip()

        full_name = extracted.get("full_name")
        if not full_name:
            if subject and "-" in subject:
                parts = subject.split("-")
                candidate_candidate = parts[-1].strip()
                if len(candidate_candidate.split()) <= 4:
                    full_name = candidate_candidate

        is_recognized = bool(full_name or extracted.get("email") or extracted.get("phone"))

        # Split skills
        skills_raw = extracted.get("skills", "")
        if isinstance(skills_raw, str):
            skills = [s.strip() for s in re.split(r"[,;|]", skills_raw) if s.strip()]
        elif isinstance(skills_raw, list):
            skills = skills_raw
        else:
            skills = []

        # Split preferred locations
        pref_loc_raw = extracted.get("preferred_locations", "")
        if isinstance(pref_loc_raw, str):
            preferred_locations = [l.strip() for l in re.split(r"[,;|/]", pref_loc_raw) if l.strip()]
        else:
            preferred_locations = []

        return NViteParsedProfile(
            full_name=full_name or "Unknown Applicant",
            email=extracted.get("email"),
            phone=extracted.get("phone"),
            headline=extracted.get("headline"),
            current_company=extracted.get("current_company"),
            experience_years=self.parse_experience(extracted.get("experience_years")),
            current_ctc_lpa=self.parse_ctc(extracted.get("current_ctc_lpa")),
            expected_ctc_lpa=self.parse_ctc(extracted.get("expected_ctc_lpa")),
            notice_raw=extracted.get("notice_raw"),
            notice_days_max=self.parse_notice_days(extracted.get("notice_raw")),
            location=extracted.get("location"),
            preferred_locations=preferred_locations,
            skills=skills,
            education=extracted.get("education"),
            job_title=job_title,
            answers=answers,
            is_recognized=is_recognized,
        )

    def _map_key_val(self, key: str, val: str, target: Dict[str, Any]) -> None:
        key = key.lower().strip()
        val = val.strip()
        if not val:
            return

        # CTC checks must precede generic 'exp' check to prevent 'expected' matching 'exp'
        if "current ctc" in key or "current annual" in key:
            target["current_ctc_lpa"] = val
        elif "expected ctc" in key or "expected annual" in key:
            target["expected_ctc_lpa"] = val
        elif "name" in key and "company" not in key:
            target["full_name"] = val
        elif "email" in key:
            target["email"] = val.lower()
        elif "phone" in key or "contact" in key or "mobile" in key:
            target["phone"] = self.normalize_phone(val)
        elif "designation" in key or "title" in key or "headline" in key:
            target["headline"] = val
        elif "company" in key or "employer" in key:
            target["current_company"] = val
        elif ("experience" in key or "exp" in key) and "expected" not in key:
            target["experience_years"] = val
        elif "notice" in key:
            target["notice_raw"] = val
        elif "preferred location" in key:
            target["preferred_locations"] = val
        elif "location" in key or "city" in key:
            target["location"] = val
        elif "skill" in key:
            target["skills"] = val
        elif "education" in key or "qualification" in key:
            target["education"] = val
        elif "position" in key or "job posting" in key:
            target["job_title"] = val


nvite_parser = NViteParser()
