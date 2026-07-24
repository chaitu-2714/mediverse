"""
MediVerse AI — Medical File Detection Engine.
Internal AI service to auto-detect category and metadata labels for ingested files.
"""
from __future__ import annotations

import os

class MedicalFileDetectionEngine:
    """Auto-detects categories and display labels for uploaded clinical files."""

    @staticmethod
    def detect_file(file_path: str) -> dict[str, str]:
        filename = os.path.basename(file_path).lower()
        ext = os.path.splitext(filename)[1].lower()

        # Category and label mappings based on filename patterns
        if any(w in filename for w in ["who", "hand_hygiene", "malaria"]):
            return {
                "category": "WHO",
                "display_label": "WHO Clinical Guideline (PDF)"
            }
        elif any(w in filename for w in ["cdc", "sepsis", "infection_control"]):
            return {
                "category": "CDC",
                "display_label": "CDC Clinical Guideline (PDF)"
            }
        elif any(w in filename for w in ["icmr", "ethical"]):
            return {
                "category": "ICMR",
                "display_label": "ICMR Research Ethics Guideline"
            }
        elif any(w in filename for w in ["book", "textbook", "manual"]):
            return {
                "category": "Medical_Books",
                "display_label": "Reference Medical Book"
            }
        elif any(w in filename for w in ["sop", "protocol", "procedure"]):
            return {
                "category": "Hospital_SOPs",
                "display_label": "Hospital SOP Document"
            }
        elif any(w in filename for w in ["paper", "research", "study", "trial", "evaluation"]):
            return {
                "category": "Research_Papers",
                "display_label": "Clinical Research Publication"
            }
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".dcm", ".dicom"] or any(w in filename for w in ["scan", "xray", "imaging", "mri"]):
            return {
                "category": "Medical_Reports",
                "display_label": "Medical Scan / Diagnostic Image"
            }
        else:
            return {
                "category": "Medical_Reports",
                "display_label": "Patient Clinical Report"
            }
