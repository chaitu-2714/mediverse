"""
MediVerse AI — Voice AI Assistant Service.
Leverages PySide6's QtTextToSpeech engine for localized spoken answers
and interprets clinical voice commands.
"""
from __future__ import annotations

import logging
from PySide6.QtCore import QObject, Signal
from PySide6.QtTextToSpeech import QTextToSpeech

logger = logging.getLogger("mediverse.modules.imaging_analysis.services.voice")


class VoiceAssistantService(QObject):
    """Clinical Voice AI command parser and audio feedback service."""
    command_executed = Signal(str, dict) # command_id, action_payload

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        try:
            self.tts = QTextToSpeech()
            logger.info("Local QtTextToSpeech engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize QTextToSpeech engine: {e}")
            self.tts = None

    def speak(self, text: str) -> None:
        """Speaks the response text aloud through system speakers."""
        if not self.tts:
            return
            
        logger.info(f"Speaking: '{text}'")
        # Strip markdown syntax for natural voice synthesis
        clean_text = text.replace("**", "").replace("*", "").replace("#", "")
        # Limit spoken text to first 250 characters to avoid lengthy speech loops
        if len(clean_text) > 250:
            clean_text = clean_text[:240] + ". Please check the summary card for complete details."
            
        self.tts.say(clean_text)

    def process_command(self, query: str) -> str:
        """Parses natural voice command syntax and maps actions."""
        q = query.lower().strip()
        logger.info(f"Voice Command Ingested: '{q}'")

        if "explain" in q and ("report" in q or "file" in q):
            self.command_executed.emit("explain_report", {})
            return "Sure, explaining the active medical report. Please review the highlighted parameters list in the findings panel."

        elif "explain" in q and "scan" in q:
            self.command_executed.emit("explain_scan", {})
            return "Understood. The image viewer displays the scanned body part. Toggling the AI heatmap and bounding boxes now."

        elif "abnormal" in q or "findings" in q or "outlier" in q:
            self.command_executed.emit("highlight_abnormal", {})
            return "Highlighting all parameters outside normal reference ranges in red status indicator cells."

        elif "graph" in q or "chart" in q:
            self.command_executed.emit("show_graphs", {})
            return "Displaying comparative visual chart models on the active metrics."

        elif "mri" in q:
            self.command_executed.emit("open_mri", {})
            return "Loading diagnostic brain MRI scan workspace."

        elif "x-ray" in q or "xray" in q:
            self.command_executed.emit("open_xray", {})
            return "Loading chest X-Ray radiology workspace."

        elif "compare" in q:
            self.command_executed.emit("compare_previous", {})
            return "Opening comparative trend charts to display progression metrics across previous history logs."

        elif "read" in q and "aloud" in q:
            self.command_executed.emit("read_aloud", {})
            return "Reading report findings summary card details aloud now."

        elif "export" in q or "download" in q:
            self.command_executed.emit("export_report", {})
            return "Triggering report compiler. Compile export download panels are launching."

        elif "summary" in q:
            self.command_executed.emit("generate_summary", {})
            return "Compiling clinical summary nodes from indexed RAG references."

        else:
            # Fallback natural explanation intent
            return f"Understood command: '{query}'. Let me check the clinical database or guidelines matching your search."
