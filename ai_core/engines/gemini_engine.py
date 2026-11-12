"""
MediVerse AI — Gemini Online LLM Engine.
Interfaces with Google's Gemini models via the official Google Gen AI SDK.
Features:
- Configurable model selection (e.g. gemini-2.5-flash, gemini-2.0-flash)
- Dynamic Google Search grounding for real-time medical guideline retrieval
- Grounding metadata extraction (web search queries, verified sources, URLs)
- Context-grounded synthesis (Local KB + Online Guidelines)
- Strict non-diagnostic safety boundaries
- Resilient error handling (Auth, Rate limits, Network disconnects, Timeouts)
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional, List, Dict, Any

from config.settings import get_settings
from core.exceptions import (
    GeminiError,
    GeminiAuthError,
    GeminiNetworkError,
    GeminiRateLimitError,
)
from core.models.search_result import SourceReference

logger = logging.getLogger("mediverse.ai.gemini")


class GeminiEngine:
    """
    Dedicated online LLM service for Google Gemini.
    Provides structured, evidence-grounded medical dialogue synthesis.
    """

    SYSTEM_INSTRUCTION = """You are MediVerse AI, an advanced Clinical Knowledge Intelligence assistant.
Your mission is to provide accurate, evidence-grounded medical explanations for healthcare professionals and medical students.

STRUCTURE YOUR RESPONSE STRICTLY AS FOLLOWS:
### 1. 🎯 Direct Answer
A concise, direct, clinical summary answering the user's specific question.

### 2. 🧠 Clinical Explanation
In-depth pathophysiological or clinical explanation using precise medical terminology.

### 3. 📋 Relevant Medical Guidelines
Summarize key recommendations from trusted health authorities (WHO, CDC, ICMR, or PubMed consensus).
Clearly state which organization or guideline published each recommendation.

### 4. 🛡️ Precautions & Recommendations
Evidence-based lifestyle, preventive, or monitoring precautions relevant to the condition.

### 5. 📚 Source References
List cited evidence with:
- Source Title
- Issuing Organization (WHO, CDC, ICMR, or PubMed)
- Publication Date (if available)
- Clickable URL link (if available)

CRITICAL MEDICAL SAFETY RULES:
- Never provide a final diagnosis. Automated analysis does not substitute for clinical examination.
- Never prescribe medication or specific drug dosages.
- Never recommend discontinuing prescribed therapies.
- Advise users to seek urgent emergency care for acute symptoms (chest pain, severe dyspnea, acute neurological deficit).
- Never fabricate medical papers, guideline titles, or URLs. Only cite verified evidence provided in the context or discovered via Google Search grounding.
- Clearly distinguish between:
  [Local Knowledge Base]: Information retrieved from indexed hospital documents.
  [Medical Guidelines]: Information from official guidelines (WHO/CDC/ICMR/PubMed).
  [AI Synthesis]: General medical knowledge synthesis by Gemini.
"""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None
        self._available = False
        self._active_model = self._settings.gemini_model

    def initialize(self) -> bool:
        """Verify API key configuration and initialize Google GenAI client."""
        return self._check_availability()

    def _get_api_key(self) -> Optional[str]:
        """Resolve Gemini API key from settings or environment securely."""
        key = self._settings.gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if key and len(key.strip()) > 5:
            return key.strip()
        return None

    def _check_availability(self) -> bool:
        """Verify API key is configured and can be loaded."""
        api_key = self._get_api_key()
        if not api_key:
            logger.info("Gemini Online LLM: No API key found in GEMINI_API_KEY")
            self._available = False
            self._client = None
            return False

        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            self._available = True
            logger.info("Gemini Online LLM client initialized successfully (model: %s)", self._active_model)
            return True
        except ImportError:
            logger.error("google-genai package not installed. Run: pip install google-genai")
            self._available = False
            return False
        except Exception as e:
            logger.warning("Failed to initialize Gemini client: %s", e)
            self._available = False
            return False

    @property
    def is_available(self) -> bool:
        if not self._available or self._client is None:
            self._check_availability()
        api_key = self._get_api_key()
        return bool(api_key and self._available)

    def set_model(self, model_name: str) -> None:
        """Update active Gemini model (e.g. gemini-3.5-flash, gemini-3.8-flash)."""
        self._active_model = model_name
        logger.info("Active Gemini model set to: %s", model_name)

    def generate(
        self,
        prompt: str,
        context: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None,
        enable_search_grounding: bool = True,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generate response from Gemini.
        Returns dictionary with:
        - answer: str
        - groundings: list of SourceReference (from Google Search Grounding)
        - search_queries: list of str
        - model_used: str
        """
        api_key = self._get_api_key()
        if not api_key:
            raise GeminiAuthError(
                "Gemini API Key is not configured. Please add GEMINI_API_KEY to your .env file."
            )

        if not self._client:
            self._check_availability()
            if not self._client:
                raise GeminiAuthError("Could not initialize Gemini client. Please check your API key.")

        from google.genai import types, errors

        # Build prompt with context and conversation history
        full_content = self._assemble_prompt_content(prompt, context, conversation_history)

        # Configure tools (Search Grounding)
        tools = []
        if enable_search_grounding and self._settings.gemini_search_grounding:
            tools.append({"google_search": {}})

        config = types.GenerateContentConfig(
            system_instruction=self.SYSTEM_INSTRUCTION,
            temperature=temperature,
            tools=tools if tools else None,
        )

        try:
            logger.info("Calling Gemini API (%s) with search_grounding=%s", self._active_model, bool(tools))
            
            def _call_with_retry(cfg):
                last_exc = None
                for attempt in range(3):
                    try:
                        return self._client.models.generate_content(
                            model=self._active_model,
                            contents=full_content,
                            config=cfg,
                        )
                    except errors.APIError as ae:
                        last_exc = ae
                        msg_str = str(ae).lower()
                        if "503" in msg_str or "unavailable" in msg_str or "high demand" in msg_str:
                            logger.warning("Gemini 503 server spike on attempt %d; retrying in %ds...", attempt + 1, (attempt + 1) * 2)
                            time.sleep((attempt + 1) * 2)
                            continue
                        raise ae
                raise last_exc

            try:
                response = _call_with_retry(config)
            except errors.APIError as ge:
                # If Google Search Grounding triggers a 429 quota exhaustion (common on free-tier keys),
                # retry without search grounding tool so retrieved PubMed/WHO guidelines in context still synthesize
                msg_lower = str(ge).lower()
                if tools and ("resource_exhausted" in msg_lower or "429" in msg_lower or "quota" in msg_lower):
                    logger.warning(
                        "Search grounding quota exhausted on API tier; retrying with contextual medical guidelines without search tool."
                    )
                    fallback_config = types.GenerateContentConfig(
                        system_instruction=self.SYSTEM_INSTRUCTION,
                        temperature=temperature,
                        tools=None,
                    )
                    response = _call_with_retry(fallback_config)
                else:
                    raise ge



            # Extract generated text
            answer_text = response.text or ""

            # Extract grounding metadata (search queries & web references)
            grounding_sources: List[SourceReference] = []
            search_queries: List[str] = []

            if response.candidates and response.candidates[0].grounding_metadata:
                gm = response.candidates[0].grounding_metadata
                
                # Queries executed by Google Search
                if hasattr(gm, "web_search_queries") and gm.web_search_queries:
                    search_queries = list(gm.web_search_queries)

                # Web grounding chunks cited by Gemini
                if hasattr(gm, "grounding_chunks") and gm.grounding_chunks:
                    for idx, chunk in enumerate(gm.grounding_chunks):
                        web = getattr(chunk, "web", None)
                        if web:
                            title = getattr(web, "title", "Medical Web Reference") or "Medical Web Reference"
                            uri = getattr(web, "uri", "") or ""
                            org = self._infer_web_org(uri, title)
                            
                            grounding_sources.append(
                                SourceReference(
                                    document_id=f"grounding-{idx+1}",
                                    document_title=title,
                                    category=org,
                                    page_number=1,
                                    chunk_index=idx,
                                    chunk_text=f"Official Web Reference grounded by Google Search: '{title}' ({uri})",
                                    similarity_score=0.92,
                                    url=uri,
                                    organization=org,
                                    source_type="grounding",
                                )
                            )

            return {
                "answer": answer_text,
                "groundings": grounding_sources,
                "search_queries": search_queries,
                "model_used": self._active_model,
            }

        except errors.APIError as e:
            logger.error("Gemini APIError: code=%s, msg=%s", getattr(e, "code", None), str(e))
            msg = str(e)
            if "API_KEY_INVALID" in msg or "401" in msg or "403" in msg:
                raise GeminiAuthError(f"Invalid Gemini API key: {msg}") from e
            elif "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                raise GeminiRateLimitError(f"Gemini API rate limit reached: {msg}") from e
            else:
                raise GeminiError(f"Gemini API error ({getattr(e, 'code', 'error')}): {msg}") from e
        except Exception as e:
            err_str = str(e).lower()
            if "connection" in err_str or "timeout" in err_str or "nodename" in err_str:
                logger.error("Gemini network connection error: %s", e)
                raise GeminiNetworkError("Failed to reach Gemini API servers. Please check your internet connection.") from e
            logger.error("Unexpected Gemini error: %s", e)
            raise GeminiError(str(e)) from e

    def _assemble_prompt_content(
        self,
        prompt: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Assembles prompt with local knowledge base context and conversation history."""
        sections = []

        if conversation_history:
            history_text = "── RECENT CONVERSATION HISTORY ──\n"
            for turn in conversation_history[-4:]:  # Keep last 4 turns for context
                role = "User" if turn.get("role") == "user" else "Assistant"
                history_text += f"{role}: {turn.get('content', '')}\n"
            sections.append(history_text)

        if context and context.strip():
            sections.append(f"── RETRIEVED MEDICAL CONTEXT & GUIDELINES ──\n{context}\n")

        sections.append(f"── CURRENT CLINICAL QUESTION ──\n{prompt}")
        return "\n\n".join(sections)

    def _infer_web_org(self, url: str, title: str) -> str:
        """Identify authoritative medical organizations from URL or title."""
        url_lower = url.lower()
        title_lower = title.lower()
        if "who.int" in url_lower or "world health organization" in title_lower:
            return "WHO"
        elif "cdc.gov" in url_lower or "centers for disease control" in title_lower:
            return "CDC"
        elif "icmr.nic.in" in url_lower or "icmr.org.in" in url_lower:
            return "ICMR"
        elif "pubmed" in url_lower or "ncbi.nlm.nih.gov" in url_lower:
            return "PubMed"
        elif "nih.gov" in url_lower:
            return "NIH"
        elif "mayoclinic.org" in url_lower:
            return "Mayo Clinic"
        return "Medical Web Reference"
