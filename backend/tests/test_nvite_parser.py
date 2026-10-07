import os
import pytest
from app.services.nvite_parser import nvite_parser

def test_parse_nvite_sample_1():
    fixture_path = os.path.join("..", "test-fixtures", "nvite_sample_1.html")
    if not os.path.exists(fixture_path):
        fixture_path = os.path.join("test-fixtures", "nvite_sample_1.html")
    
    with open(fixture_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    parsed = nvite_parser.parse(html_content=html_content, subject="Application received for Senior Python Developer - Rahul Sharma")
    
    assert parsed.is_recognized is True
    assert parsed.full_name == "Rahul Sharma"
    assert parsed.email == "rahul.sharma.dev@gmail.com"
    assert parsed.phone == "+919876543210"
    assert parsed.experience_years == 6.5
    assert parsed.current_ctc_lpa == 18.5
    assert parsed.expected_ctc_lpa == 24.0
    assert parsed.notice_days_max == 15
    assert "FastAPI" in parsed.skills
    assert "PostgreSQL" in parsed.skills
    assert len(parsed.answers) >= 2


def test_parse_nvite_sample_2():
    fixture_path = os.path.join("..", "test-fixtures", "nvite_sample_2.html")
    if not os.path.exists(fixture_path):
        fixture_path = os.path.join("test-fixtures", "nvite_sample_2.html")
        
    with open(fixture_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    parsed = nvite_parser.parse(html_content=html_content, subject="Candidate Response for Lead Data Engineer")

    assert parsed.is_recognized is True
    assert parsed.full_name == "Priya Patel"
    assert parsed.email == "priya.patel.data@outlook.com"
    assert parsed.phone == "+919123456789"
    assert parsed.experience_years == 7.0
    assert parsed.current_ctc_lpa == 20.0
    assert parsed.expected_ctc_lpa == 26.0
    assert parsed.notice_days_max == 30
    assert "PySpark" in parsed.skills
    assert "Airflow" in parsed.skills


def test_parse_notice_curve_cases():
    assert nvite_parser.parse_notice_days("Immediate") == 0
    assert nvite_parser.parse_notice_days("Serving notice, 15 days left") == 15
    assert nvite_parser.parse_notice_days("1 Month") == 30
    assert nvite_parser.parse_notice_days("60 days") == 60
    assert nvite_parser.parse_notice_days("3 Months") == 90
    assert nvite_parser.parse_notice_days(None) is None


def test_unrecognized_email():
    junk_html = "<html><body><h1>Random Newsletter</h1><p>Check out these discounts today!</p></body></html>"
    parsed = nvite_parser.parse(html_content=junk_html, subject="Weekly Newsletter")
    assert parsed.is_recognized is False
