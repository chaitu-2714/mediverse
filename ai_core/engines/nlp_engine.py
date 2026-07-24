"""
MediVerse AI — NLP Engine.
Medical entity recognition, keyword extraction, text cleaning using spaCy + NLTK + KeyBERT.
"""
from __future__ import annotations

import logging
import re
import string
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("mediverse.ai.nlp")


@dataclass
class NLPResult:
    """Output of the NLP processing pipeline."""
    clean_text: str
    language: str = "en"
    sentences: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    medical_entities: dict[str, list[str]] = field(default_factory=dict)
    word_count: int = 0
    char_count: int = 0


class NLPEngine:
    """
    Medical NLP pipeline using spaCy + NLTK + KeyBERT.
    Performs:
    - Text cleaning and normalization
    - Language detection
    - Sentence segmentation
    - Medical entity recognition
    - Keyword extraction
    """

    def __init__(self) -> None:
        self._nlp = None          # spaCy model (lazy-loaded)
        self._kw_model = None     # KeyBERT model (lazy-loaded)
        self._stopwords: set[str] = set()
        self._initialized = False

    def initialize(self) -> None:
        """Load NLP models. Called once during app startup."""
        if self._initialized:
            return

        self._load_spacy()
        self._load_nltk()
        self._load_keybert()
        self._initialized = True
        logger.info("NLP Engine initialized")

    def _load_spacy(self) -> None:
        try:
            import spacy
            # Try medical model first, fall back to general English
            for model_name in ["en_core_sci_sm", "en_core_web_sm", "en_core_web_md"]:
                try:
                    self._nlp = spacy.load(model_name)
                    logger.info(f"spaCy model loaded: {model_name}")
                    return
                except OSError:
                    continue
            logger.warning("No spaCy model found. Run: python -m spacy download en_core_web_sm")
            self._nlp = None
        except ImportError:
            logger.warning("spaCy not installed — entity recognition disabled")
            self._nlp = None

    def _load_nltk(self) -> None:
        try:
            import nltk
            for resource in ["stopwords", "punkt", "punkt_tab"]:
                try:
                    nltk.download(resource, quiet=True)
                except Exception:
                    pass
            from nltk.corpus import stopwords
            self._stopwords = set(stopwords.words("english"))
            logger.info("NLTK resources loaded")
        except Exception as e:
            logger.warning(f"NLTK load warning: {e}")

    def _load_keybert(self) -> None:
        try:
            from keybert import KeyBERT
            self._kw_model = KeyBERT()
            logger.info("KeyBERT model loaded")
        except Exception as e:
            logger.warning(f"KeyBERT not available: {e}. Keyword extraction will use fallback.")
            self._kw_model = None

    def process(self, text: str, max_keywords: int = 20) -> NLPResult:
        """
        Run the full NLP pipeline on input text.
        Returns an NLPResult with all extracted information.
        """
        if not self._initialized:
            self.initialize()

        clean = self.clean_text(text)
        language = self.detect_language(clean)
        sentences = self.segment_sentences(clean)
        entities = self.extract_entities(clean)
        keywords = self.extract_keywords(clean, max_keywords)

        return NLPResult(
            clean_text=clean,
            language=language,
            sentences=sentences,
            keywords=keywords,
            medical_entities=entities,
            word_count=len(clean.split()),
            char_count=len(clean),
        )

    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove control characters
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # Remove excessive punctuation
        text = re.sub(r"([.!?]){3,}", r"\1", text)
        # Normalize quotes
        text = text.replace("\u2019", "'").replace("\u2018", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        return text.strip()

    def detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        try:
            from langdetect import detect
            return detect(text[:1000]) if len(text) > 20 else "en"
        except Exception:
            return "en"

    def segment_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        if self._nlp:
            try:
                # Process in chunks to avoid memory issues
                chunk_size = 100_000
                sentences = []
                for i in range(0, len(text), chunk_size):
                    chunk = text[i: i + chunk_size]
                    doc = self._nlp(chunk)
                    sentences.extend([s.text.strip() for s in doc.sents if s.text.strip()])
                return sentences
            except Exception as e:
                logger.warning(f"spaCy sentence segmentation failed: {e}")

        # Fallback: simple sentence splitting
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    def extract_entities(self, text: str) -> dict[str, list[str]]:
        """
        Extract named entities from text.
        Returns a dict: {entity_label: [entity_texts]}.
        """
        entities: dict[str, list[str]] = {}
        if not self._nlp:
            return entities

        try:
            chunk_size = 100_000
            for i in range(0, min(len(text), 500_000), chunk_size):
                chunk = text[i: i + chunk_size]
                doc = self._nlp(chunk)
                for ent in doc.ents:
                    label = ent.label_
                    txt = ent.text.strip()
                    if len(txt) < 2:
                        continue
                    if label not in entities:
                        entities[label] = []
                    if txt not in entities[label]:
                        entities[label].append(txt)
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")

        return entities

    def extract_keywords(self, text: str, n: int = 20) -> list[str]:
        """Extract top-N keywords using KeyBERT, with NLTK fallback."""
        if self._kw_model:
            try:
                text_sample = text[:10000]  # Limit input for performance
                results = self._kw_model.extract_keywords(
                    text_sample,
                    keyphrase_ngram_range=(1, 3),
                    stop_words="english",
                    top_n=n,
                    diversity=0.7,
                )
                return [kw for kw, _ in results]
            except Exception as e:
                logger.warning(f"KeyBERT keyword extraction failed: {e}")

        # Fallback: frequency-based extraction
        return self._frequency_keywords(text, n)

    def _frequency_keywords(self, text: str, n: int) -> list[str]:
        """Simple TF-based keyword extraction as fallback."""
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        words = [w for w in words if w not in self._stopwords]
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:n]]

    def remove_stopwords(self, text: str) -> str:
        """Remove common stopwords from text."""
        words = text.split()
        filtered = [w for w in words if w.lower() not in self._stopwords]
        return " ".join(filtered)
