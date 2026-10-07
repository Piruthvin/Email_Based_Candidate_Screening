import hashlib
import io
import logging
import re
from typing import Optional, Tuple
from pypdf import PdfReader
import docx

logger = logging.getLogger(__name__)


class ResumeService:
    """
    Handles resume processing: text extraction, hashing, and blind PII redaction.
    """

    @staticmethod
    def compute_sha256(content_bytes: bytes) -> str:
        return hashlib.sha256(content_bytes).hexdigest()

    def extract_text(self, file_bytes: bytes, file_name: str) -> Tuple[str, str]:
        """
        Extracts text from PDF or DOCX binary bytes.
        Returns: (extracted_text, text_quality) where quality is 'ok', 'ocr', or 'low'.
        """
        lower_name = file_name.lower()
        text = ""
        quality = "ok"

        if lower_name.endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(file_bytes))
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    pages_text.append(page_text)
                text = "\n".join(pages_text).strip()

                if len(text) < 50:
                    quality = "low"
            except Exception as e:
                logger.warning("PDF extraction failed for %s: %s", file_name, e)
                quality = "low"

        elif lower_name.endswith((".docx", ".doc")):
            try:
                doc = docx.Document(io.BytesIO(file_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                text = "\n".join(paragraphs).strip()
                if len(text) < 50:
                    quality = "low"
            except Exception as e:
                logger.warning("DOCX extraction failed for %s: %s", file_name, e)
                quality = "low"
        else:
            # Fallback to UTF-8 decoded text
            try:
                text = file_bytes.decode("utf-8", errors="ignore").strip()
                quality = "ok" if len(text) >= 50 else "low"
            except Exception:
                quality = "low"

        return text, quality

    def redact_pii(
        self,
        resume_text: str,
        candidate_name: Optional[str] = None,
        candidate_email: Optional[str] = None,
        candidate_phone: Optional[str] = None,
    ) -> str:
        """
        Redacts personal identifiable information (PII) for blind scoring:
        - Names, Emails, Phone numbers
        - Marital status, Gender, Date of Birth, Physical addresses
        """
        if not resume_text:
            return ""

        redacted = resume_text

        # 1. Redact explicit candidate values if supplied
        if candidate_email:
            redacted = re.sub(re.escape(candidate_email), "[REDACTED_EMAIL]", redacted, flags=re.IGNORECASE)

        if candidate_phone:
            # Also clean variations of phone number
            digits = re.sub(r"\D", "", candidate_phone)
            if len(digits) >= 10:
                redacted = re.sub(re.escape(candidate_phone), "[REDACTED_PHONE]", redacted, flags=re.IGNORECASE)
                redacted = re.sub(re.escape(digits[-10:]), "[REDACTED_PHONE]", redacted, flags=re.IGNORECASE)

        if candidate_name and len(candidate_name.split()) >= 1:
            for part in candidate_name.split():
                if len(part) > 2 and part.lower() not in {"the", "and", "developer", "engineer"}:
                    redacted = re.sub(r"\b" + re.escape(part) + r"\b", "[REDACTED_NAME]", redacted, flags=re.IGNORECASE)

        # 2. General Regex PII redaction
        # Emails
        redacted = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[REDACTED_EMAIL]", redacted)

        # Phone numbers (Indian and international styles)
        redacted = re.sub(r"(?:\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,5}[\s.-]?\d{4,5}", "[REDACTED_PHONE]", redacted)

        # URLs / LinkedIn / GitHub profiles
        redacted = re.sub(r"https?://(?:www\.)?linkedin\.com/in/[\w-]+", "[REDACTED_LINKEDIN]", redacted, flags=re.IGNORECASE)
        redacted = re.sub(r"https?://(?:www\.)?github\.com/[\w-]+", "[REDACTED_GITHUB]", redacted, flags=re.IGNORECASE)

        # Demographic / Protected Attributes
        redacted = re.sub(r"(?i)\b(date of birth|dob)\b\s*[:\-]?\s*[\d\w\s,/-]+", "[REDACTED_DOB]", redacted)
        redacted = re.sub(r"(?i)\b(marital status)\b\s*[:\-]?\s*\w+", "[REDACTED_MARITAL_STATUS]", redacted)
        redacted = re.sub(r"(?i)\b(gender|sex)\b\s*[:\-]?\s*\w+", "[REDACTED_GENDER]", redacted)
        redacted = re.sub(r"(?i)\b(father'?s? name|mother'?s? name)\b\s*[:\-]?\s*[\w\s]+", "[REDACTED_FAMILY]", redacted)
        redacted = re.sub(r"(?i)\b(religion|caste|nationality)\b\s*[:\-]?\s*\w+", "[REDACTED_DEMOGRAPHIC]", redacted)

        return redacted


resume_service = ResumeService()
