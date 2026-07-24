"""
Unit tests for next-generation AI Medical Report & Imaging Analysis modules.
"""
from __future__ import annotations

import os
from uuid import uuid4
from ai_core.engines.detection_engine import MedicalFileDetectionEngine
from modules.imaging_analysis.services.analyzer_service import MedicalAnalyzerService
from modules.imaging_analysis.ui.anatomy_navigator import AnatomyNavigatorWidget
from modules.imaging_analysis.ui.terminology_explorer import TerminologyExplorerPanel
from modules.imaging_analysis.services.voice_assistant import VoiceAssistantService

def test_file_category_detection():
    res_who = MedicalFileDetectionEngine.detect_file("WHO_Malaria_Guidelines.pdf")
    assert res_who["category"] == "WHO"
    assert "WHO" in res_who["display_label"]

    res_cdc = MedicalFileDetectionEngine.detect_file("cdc_sepsis_report.pdf")
    assert res_cdc["category"] == "CDC"
    assert "CDC" in res_cdc["display_label"]

    res_icmr = MedicalFileDetectionEngine.detect_file("ethical_icmr_guideline.pdf")
    assert res_icmr["category"] == "ICMR"

    res_mri = MedicalFileDetectionEngine.detect_file("brain_mri_scan.png")
    assert res_mri["category"] == "Medical_Reports"
    assert "Scan" in res_mri["display_label"]


def test_analyzer_parameter_extraction():
    service = MedicalAnalyzerService()
    
    result_cbc = service.analyze_file("patient_blood_cbc_report.pdf", uploader_id=uuid4())
    assert result_cbc["category"] == "Medical_Reports"
    assert result_cbc["metadata"]["modality"] == "Hematology"
    
    parameters = result_cbc["parameters"]
    assert any(p["name"] == "Hemoglobin (Hb)" for p in parameters)
    
    abnormal = result_cbc["abnormal_findings"]
    assert len(abnormal) > 0
    assert any(a["parameter"] == "Hemoglobin (Hb)" and a["status"] == "Low" for a in abnormal)

    result_mri = service.analyze_file("patient_brain_mri.jpg", uploader_id=uuid4())
    assert result_mri["is_image"] is True
    assert result_mri["metadata"]["body_part"] == "Brain"
    assert result_mri["heatmap_overlay"] is not None


def test_premium_features(qapp):
    # 1. Test Anatomy Navigator
    anatomy = AnatomyNavigatorWidget()
    assert "Brain" in anatomy.organs
    assert "Lungs" in anatomy.organs
    
    anatomy.highlight_organ("Lungs")
    assert anatomy.highlighted_organ == "Lungs"

    anatomy.highlight_organ("invalid_organ")
    assert anatomy.highlighted_organ is None

    # 2. Test Terminology Explorer dictionary
    panel = TerminologyExplorerPanel()
    assert "hemoglobin" in panel.CLINICAL_DICTIONARY
    assert "creatinine" in panel.CLINICAL_DICTIONARY
    
    # 3. Test Voice Assistant Service and intents
    voice = VoiceAssistantService()
    
    # Catch signals to confirm voice command triggers
    triggered_commands = []
    voice.command_executed.connect(lambda cmd, payload: triggered_commands.append(cmd))
    
    res = voice.process_command("Explain this report.")
    assert "report" in res
    assert "explain_report" in triggered_commands
    
    res_graphs = voice.process_command("Show graphs please.")
    assert "graphs" in res_graphs or "chart" in res_graphs
    assert "show_graphs" in triggered_commands
