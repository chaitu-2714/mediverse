"""
Unit and Integration Tests for Gemini Online LLM, Medical Guideline Search,
and Multi-Turn Follow-Up Intelligence in MediVerse AI.
"""
from __future__ import annotations

import os
import pytest
from unittest.mock import MagicMock, patch

from ai_core.engines.gemini_engine import GeminiEngine
from ai_core.engines.medical_search_engine import MedicalGuidelineSearchEngine, OnlineGuideline
from ai_core.conversation.conversation_manager import ConversationManager
from ai_core.ai_engine import get_ai_engine
from core.exceptions import GeminiAuthError, GeminiNetworkError, GeminiError
from core.models.search_result import SourceReference, AIResponse


def test_gemini_missing_api_key_raises_auth_error():
    """Scenario 6a: Missing API key raises GeminiAuthError gracefully."""
    # Ensure no key in environment for this test
    with patch.dict(os.environ, {}, clear=True):
        engine = GeminiEngine()
        assert not engine.is_available
        with pytest.raises(GeminiAuthError) as exc_info:
            engine.generate("What is hypertension?")
        assert "not configured" in str(exc_info.value).lower() or "gemini api key" in str(exc_info.value).lower()


def test_gemini_invalid_api_key_raises_auth_error():
    """Scenario 6b: Invalid API key raises GeminiAuthError rather than uncaught crash."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyInvalidFakeKey12345"}):
        engine = GeminiEngine()
        with pytest.raises(GeminiAuthError) as exc_info:
            engine.generate("What is hypertension?")
        assert "invalid" in str(exc_info.value).lower() or "api_key" in str(exc_info.value).lower()


def test_gemini_network_failure_handling():
    """Scenario 7: Network failure maps to GeminiNetworkError."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyValidDummyKeyForMocking"}):
        engine = GeminiEngine()
        with patch.object(engine, "_client") as mock_client:
            mock_client.models.generate_content.side_effect = Exception("Connection refused / network down")
            with pytest.raises(GeminiNetworkError):
                engine.generate("Test network query")


def test_medical_guideline_search_engine_live():
    """Scenario 3: Real live retrieval of peer-reviewed medical guidelines."""
    engine = MedicalGuidelineSearchEngine(timeout=10)
    results = engine.search_guidelines("hypertension WHO guideline", max_results=3)
    
    assert len(results) > 0, "PubMed / medical search should return verified guidelines"
    for item in results:
        assert isinstance(item, OnlineGuideline)
        assert item.title, "Guideline title must be present"
        assert item.url.startswith("https://"), "Guideline must provide a valid HTTPS URL"
        assert item.publication_date, "Publication date should be populated"
        # Source reference conversion check
        src = item.to_source_reference()
        assert src.source_type == "online_guideline"
        assert src.url == item.url


def test_medical_guideline_search_failure_resilience():
    """Scenario 8: Search provider failure returns empty list without crashing."""
    engine = MedicalGuidelineSearchEngine(timeout=2)
    with patch.object(engine._session, "get", side_effect=Exception("Timeout / DNS Failure")):
        results = engine.search_guidelines("sepsis treatment")
        assert results == [], "Engine should return empty list gracefully on network failure"


def test_follow_up_question_intelligence_hypertension():
    """Scenario 4: Follow-up question refers to previous medical topic ('this condition')."""
    cm = ConversationManager()
    cm.reset()

    # Turn 1
    q1 = cm.contextualize_query("What is hypertension?")
    assert "Hypertension" in q1.medical_topic
    assert not q1.is_follow_up
    cm.record_turn(
        user_query="What is hypertension?",
        assistant_answer="Hypertension is chronic high blood pressure.",
        standalone_query=q1.standalone_query,
        medical_topic=q1.medical_topic,
    )

    # Turn 2: Anaphoric follow-up
    q2 = cm.contextualize_query("What precautions should a person with this condition follow?")
    assert q2.is_follow_up, "Must detect follow-up question"
    assert "Hypertension" in q2.standalone_query, "Must reformulate 'this condition' to 'Hypertension'"
    assert "What precautions should a person with Hypertension follow?" in q2.standalone_query


def test_follow_up_question_intelligence_iron_deficiency():
    """Scenario 5: Follow-up question about diet for iron deficiency."""
    cm = ConversationManager()
    cm.reset()

    # Turn 1
    q1 = cm.contextualize_query("What are the common causes of iron deficiency?")
    assert "Iron Deficiency" in q1.medical_topic
    cm.record_turn(
        user_query="What are the common causes of iron deficiency?",
        assistant_answer="Causes include blood loss, poor diet, and malabsorption.",
        standalone_query=q1.standalone_query,
        medical_topic=q1.medical_topic,
    )

    # Turn 2: Elliptical follow-up
    q2 = cm.contextualize_query("What foods help improve iron levels?")
    assert q2.is_follow_up
    assert "Iron Deficiency" in q2.standalone_query


def test_ai_engine_provider_selection():
    """Verify runtime switching between Ollama Local and Gemini Online."""
    ai = get_ai_engine()
    ai.set_llm_provider("gemini")
    assert ai.get_llm_provider() == "gemini"

    ai.set_llm_provider("ollama")
    assert ai.get_llm_provider() == "ollama"


def test_rag_query_with_online_guideline_integration():
    """
    Scenario 2 & 10: Query execution with online guideline integration
    verifying source references, medical safety disclaimer, and model metadata.
    """
    ai = get_ai_engine()
    # Query with ollama provider (which falls back safely if local ollama daemon is offline)
    res = ai.query("What are the clinical guidelines for asthma management?", provider="ollama", online_search=True)
    
    assert isinstance(res, AIResponse)
    assert res.has_evidence is True
    assert res.online_search_used is True
    assert len(res.sources) > 0, "Online guidelines must populate sources"
    
    # Verify safety disclaimer enforcement
    assert "SAFETY DISCLAIMER" in res.answer
    assert "clinical diagnosis" in res.answer.lower()
    
    # Verify that at least one source contains a valid online HTTPS URL
    has_online_url = any(s.url and s.url.startswith("https://") for s in res.sources)
    assert has_online_url, "Must include at least one verified online reference URL"


def test_scenario_1_basic_medical_question_using_gemini():
    """Scenario 1: Basic medical question using Gemini generation with grounding mock."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyMockedKeyForTestingScenario1"}):
        engine = GeminiEngine()
        mock_response = MagicMock()
        mock_response.text = (
            "### 1. 🎯 Direct Answer\nHypertension is a chronic elevation of systemic arterial blood pressure.\n\n"
            "### 2. 🧠 Clinical Explanation\nIt is defined as systolic blood pressure >= 140 mmHg and/or diastolic >= 90 mmHg.\n\n"
            "### 3. 📋 Relevant Medical Guidelines\nWHO recommends sodium intake under 2g/day.\n\n"
            "### 4. 🛡️ Precautions & Recommendations\nRoutine monitoring and DASH dietary patterns.\n\n"
            "### 5. 📚 Source References\nWHO Guideline on Hypertension (2023) - https://www.who.int"
        )
        # Mock grounding metadata
        mock_candidate = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.web.title = "WHO Guideline for the pharmacological treatment of hypertension"
        mock_chunk.web.uri = "https://www.who.int/publications/i/item/9789240033986"
        mock_candidate.grounding_metadata.grounding_chunks = [mock_chunk]
        mock_candidate.grounding_metadata.web_search_queries = ["hypertension guidelines WHO"]
        mock_response.candidates = [mock_candidate]

        with patch.object(engine, "_client") as mock_client:
            mock_client.models.generate_content.return_value = mock_response
            out = engine.generate("What is hypertension?", enable_search_grounding=True)

            assert "Direct Answer" in out["answer"]
            assert "Clinical Explanation" in out["answer"]
            assert len(out["groundings"]) == 1
            assert out["groundings"][0].organization == "WHO"
            assert out["groundings"][0].url.startswith("https://www.who.int")
            assert out["search_queries"] == ["hypertension guidelines WHO"]


def test_scenario_9_no_relevant_sources_communicates_uncertainty():
    """Scenario 9: When no sources are retrieved, the system states uncertainty cleanly."""
    ai = get_ai_engine()
    with patch.object(ai.medical_search, "search_guidelines", return_value=[]):
        with patch.object(ai.search, "search", return_value=([], 0)):
            # Query with empty retrieved context
            res = ai.query("Extremely rare unknown biomarker XYZ999", provider="ollama", online_search=True)
            assert isinstance(res, AIResponse)
            # Sources are empty, so the system flags has_evidence as False
            assert res.has_evidence is False
            assert len(res.sources) == 0
            # Safety disclaimer is still strictly enforced
            assert "SAFETY DISCLAIMER" in res.answer



