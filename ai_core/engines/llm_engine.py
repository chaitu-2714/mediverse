"""
MediVerse AI — LLM Engine.
Interfaces with Ollama / Llama 3.2 for text generation.
"""
from __future__ import annotations

import logging
from typing import Iterator, Optional

from config.settings import get_settings
from core.exceptions import LLMError, OllamaNotAvailableError

logger = logging.getLogger("mediverse.ai.llm")


class LLMEngine:
    """
    Ollama LLM client for medical document intelligence.
    Supports streaming and non-streaming generation.
    Never generates medical advice without retrieved context.
    """

    SYSTEM_PROMPT = """You are MediVerse AI, an expert medical knowledge assistant for healthcare professionals.

Your responses must:
1. Be grounded ONLY in the provided context from the knowledge repository
2. Cite specific source documents and page numbers when referencing information
3. Use professional medical terminology appropriate for healthcare professionals
4. Be structured, clear, and evidence-based
5. Acknowledge uncertainty when context is insufficient

IMPORTANT CONSTRAINTS:
- Never provide diagnosis, treatment recommendations, or clinical advice beyond what's in the context
- If the context does not contain sufficient information, state: "The indexed knowledge repository does not contain sufficient information to answer this question confidently."
- Never hallucinate or fabricate medical information
- Always distinguish between what is in the sources vs. your general knowledge"""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None
        self._available = False

    def initialize(self) -> None:
        """Check Ollama availability and initialize client."""
        if not self._settings.ollama_enabled:
            logger.info("Ollama disabled in configuration")
            return
        self._check_availability()

    def _get_client(self):
        """Lazy-load Ollama client."""
        if self._client is None:
            try:
                import ollama
                self._client = ollama.Client(
                    host=self._settings.ollama_base_url,
                )
            except ImportError:
                raise LLMError("ollama package not installed. Run: pip install ollama")
        return self._client

    def _check_availability(self) -> bool:
        """Verify Ollama is running and the model is available."""
        try:
            client = self._get_client()
            models = client.list()
            model_names = [m.model for m in models.models] if hasattr(models, "models") else []
            target = self._settings.ollama_model

            if any(target in name for name in model_names):
                self._available = True
                logger.info(f"Ollama available with model: {target}")
            else:
                logger.warning(
                    f"Ollama running but model '{target}' not found. "
                    f"Available: {model_names}. Run: ollama pull {target}"
                )
                self._available = len(model_names) > 0
            return self._available
        except Exception as e:
            logger.warning(f"Ollama not reachable at {self._settings.ollama_base_url}: {e}")
            self._available = False
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    def generate(
        self,
        prompt: str,
        context: str = "",
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """
        Generate a response for the given prompt and context.
        Raises OllamaNotAvailableError if Ollama is not running.
        """
        if not self._available:
            if not self._check_availability():
                raise OllamaNotAvailableError()

        system = system_prompt or self.SYSTEM_PROMPT
        full_prompt = f"{context}\n\nQuestion: {prompt}" if context else prompt

        try:
            client = self._get_client()
            response = client.chat(
                model=self._settings.ollama_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": full_prompt},
                ],
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )
            return response.message.content or ""
        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                raise OllamaNotAvailableError() from e
            raise LLMError(str(e)) from e

    def generate_streaming(
        self,
        prompt: str,
        context: str = "",
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> Iterator[str]:
        """
        Generate a streaming response. Yields text chunks as they arrive.
        """
        if not self._available:
            if not self._check_availability():
                raise OllamaNotAvailableError()

        system = system_prompt or self.SYSTEM_PROMPT
        full_prompt = f"{context}\n\nQuestion: {prompt}" if context else prompt

        try:
            client = self._get_client()
            stream = client.chat(
                model=self._settings.ollama_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": full_prompt},
                ],
                options={"temperature": temperature},
                stream=True,
            )
            for chunk in stream:
                if chunk.message and chunk.message.content:
                    yield chunk.message.content
        except Exception as e:
            if "connection" in str(e).lower():
                raise OllamaNotAvailableError() from e
            raise LLMError(str(e)) from e

    def summarize_document(self, text: str, title: str = "") -> str:
        """Generate a professional summary for a medical document."""
        prompt = (
            f"Provide a concise professional summary (3-5 sentences) of this medical document"
            f"{f' titled: {title}' if title else ''}.\n\n"
            f"Document excerpt:\n{text[:3000]}"
        )
        try:
            return self.generate(prompt, temperature=0.2)
        except Exception as e:
            logger.warning(f"Document summarization failed: {e}")
            return ""
