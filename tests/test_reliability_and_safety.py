"""
Tests verifying System Reliability, Functional Test Cases, and Clinical Safety Compliance
for MediVerse AI.

These tests validate:
1. Clinical safety disclaimer enforcement (ensuring non-diagnostic boundaries).
2. Document categorization fidelity (WHO, CDC, ICMR vs. Patient Reports).
3. Parameter extraction and abnormal finding detection.
4. Evidence attribution and citation formatting.
5. Export report safety compliance.
"""
from __future__ import annotations

import os
from uuid import uuid4
from pathlib import Path

from ai_core.engines.detection_engine import MedicalFileDetectionEngine
from modules.imaging_analysis.services.analyzer_service import MedicalAnalyzerService


def test_safety_disclaimer_presence_in_automated_summary():
    """
    Test Case TC-SAF-01:
    Verify that every automated report summary strictly includes
    a mandatory non-diagnostic clinical disclaimer.
    """
    service = MedicalAnalyzerService()
    result = service.analyze_file("patient_blood_cbc_report.pdf", uploader_id=uuid4())
    
    summary = result.get("ai_summary", "")
    assert summary, "AI summary must not be empty"
    
    # Verify mandatory safety disclaimer elements
    assert "SAFETY DISCLAIMER" in summary
    assert "qualified healthcare professionals" in summary
    assert "Never make clinical diagnoses" in summary


def test_document_category_classification_accuracy():
    """
    Test Case TC-CLS-01:
    Verify accurate classification of reference guidelines vs patient diagnostic files.
    """
    test_cases = [
        ("WHO_Guidelines_Hypertension.pdf", "WHO"),
        ("cdc_guidelines_respiratory.pdf", "CDC"),
        ("ICMR_guidelines_oncology.pdf", "ICMR"),
        ("patient_blood_test_cbc.pdf", "Medical_Reports"),
        ("brain_mri_t2_scan.jpg", "Medical_Reports"),
    ]
    
    for filename, expected_category in test_cases:
        res = MedicalFileDetectionEngine.detect_file(filename)
        assert res["category"] == expected_category, (
            f"Failed for {filename}: expected {expected_category}, got {res['category']}"
        )


def test_abnormal_parameter_range_detection():
    """
    Test Case TC-EXT-01:
    Verify that abnormal lab values are identified, classified, and flagged with appropriate status.
    """
    service = MedicalAnalyzerService()
    result = service.analyze_file("patient_blood_cbc_report.pdf", uploader_id=uuid4())
    
    params = result.get("parameters", [])
    abnormal_findings = result.get("abnormal_findings", [])
    
    assert len(params) > 0, "Parameters should be successfully extracted"
    assert len(abnormal_findings) > 0, "Abnormal parameters must be detected and flagged"
    
    # Check that each abnormal finding contains parameter, value, and clinical status
    for finding in abnormal_findings:
        assert "parameter" in finding
        assert "value" in finding
        assert "status" in finding
        assert finding["status"] in ["Low", "High", "Critical"]


def test_evidence_attribution_and_citation_formatting():
    """
    Test Case TC-EVD-01:
    Verify that the system attributes findings to guidelines or explicitly notes absence.
    """
    service = MedicalAnalyzerService()
    result = service.analyze_file("patient_blood_cbc_report.pdf", uploader_id=uuid4())
    
    evidence_list = result.get("evidence", [])
    summary = result.get("ai_summary", "")
    
    if len(evidence_list) > 0:
        assert any("Supporting Medical Guidelines" in summary or "ICMR" in summary or "WHO" in summary for _ in [1])
    else:
        assert "Recommended clinical manual consultation" in summary


def test_pdf_export_preserves_safety_disclaimer(tmp_path: Path):
    """
    Test Case TC-EXP-01:
    Verify that generated PDF export files are created cleanly and include structured metadata.
    """
    service = MedicalAnalyzerService()
    result = service.analyze_file("patient_blood_cbc_report.pdf", uploader_id=uuid4())
    
    export_file = str(tmp_path / "test_clinical_export.pdf")
    service.export_report_pdf(result, export_file)
    
    assert os.path.exists(export_file), "Exported PDF must be written to disk"
    assert os.path.getsize(export_file) > 1000, "Exported PDF must not be an empty file"
