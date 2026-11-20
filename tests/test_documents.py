"""Tests for PDF context extraction and report downloads."""

import pytest

from core import documents
from core.reporting import report_filename, report_to_markdown


def test_extract_pdf_text_limits_context_and_reports_truncation(monkeypatch):
    class FakePage:
        def extract_text(self):
            return "Research evidence from the uploaded report."

    class FakeReader:
        is_encrypted = False
        pages = [FakePage()]

    monkeypatch.setattr(documents, "PdfReader", lambda *args, **kwargs: FakeReader())
    monkeypatch.setattr(documents, "MAX_PDF_TEXT_CHARS", 20)

    text, truncated = documents.extract_pdf_text(b"%PDF-test")

    assert text == "Research evidence fr"
    assert truncated


def test_extract_pdf_text_rejects_encrypted_documents(monkeypatch):
    class FakeReader:
        is_encrypted = True
        pages = []

    monkeypatch.setattr(documents, "PdfReader", lambda *args, **kwargs: FakeReader())

    with pytest.raises(ValueError, match="Encrypted PDFs"):
        documents.extract_pdf_text(b"%PDF-test")


def test_report_download_contains_verdicts_sources_and_safe_filename():
    report = {
        "topic": "Renewable Energy: An Overview!",
        "created_at": "Nov 20, 2026",
        "document_name": "research-paper.pdf",
        "research_draft": "## Findings\nRenewables reduce emissions [S1].",
        "fact_checks": [
            {
                "claim": "Renewables reduce emissions",
                "verdict": "Supported",
                "confidence": 0.92,
                "evidence_url": "https://example.com/evidence",
            }
        ],
        "sources": ["https://example.com/evidence"],
    }

    markdown = report_to_markdown(report)

    assert report_filename(report["topic"]) == "renewable-energy-an-overview.md"
    assert "research-paper.pdf" in markdown
    assert "**Supported** (92% confidence)" in markdown
    assert "[S1](https://example.com/evidence)" in markdown
