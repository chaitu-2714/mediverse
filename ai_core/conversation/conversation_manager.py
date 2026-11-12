"""
MediVerse AI — Conversation & Follow-Up Intelligence Manager.
Maintains multi-turn clinical dialogue context and reformulates follow-up queries
so that downstream semantic retrieval (ChromaDB) and online guideline search
operate on fully qualified, context-rich medical terms.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger("mediverse.ai.conversation")


@dataclass
class DialogueTurn:
    """A single turn in the medical conversation."""
    user_query: str
    assistant_answer: str
    standalone_query: str
    medical_topic: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sources_count: int = 0


@dataclass
class ContextualizedQuery:
    """Output of conversation analysis for retrieval and generation."""
    raw_query: str
    standalone_query: str
    medical_topic: str
    is_follow_up: bool
    history_turns: List[Dict[str, str]]


class ConversationManager:
    """
    Manages clinical conversation memory and handles follow-up intelligence.
    """

    FOLLOW_UP_INDICATORS = [
        r"\b(this|that|these|those)\s+(condition|disease|illness|disorder|syndrome|infection|problem|issue|patient|case)\b",
        r"\b(it|its|them|they)\b",
        r"\b(such|same)\s+(patients|cases|conditions)\b",
        r"\bwhat\s+(precautions|diet|foods|tests|treatments|complications|medicines|drugs)\b",
        r"\bhow\s+to\s+(prevent|manage|cure|treat|diagnose)\b",
        r"\bcan\s+(it|this)\s+be\b",
        r"\bwhat\s+about\b",
        r"\band\s+what\b",
        r"\bwhat\s+are\s+the\s+side\s+effects\b",
    ]

    def __init__(self, max_history: int = 10) -> None:
        self.max_history = max_history
        self._turns: List[DialogueTurn] = []
        self._current_topic: Optional[str] = None

    def reset(self) -> None:
        """Clear conversation history and reset current topic."""
        self._turns.clear()
        self._current_topic = None
        logger.info("Conversation history reset")

    @property
    def current_topic(self) -> Optional[str]:
        return self._current_topic

    @property
    def history(self) -> List[DialogueTurn]:
        return list(self._turns)

    def contextualize_query(self, user_query: str) -> ContextualizedQuery:
        """
        Analyze user query in context of prior dialogue turns.
        Reformulates follow-up queries (e.g., 'What precautions should a person with this condition follow?')
        into standalone queries (e.g., 'What precautions should a person with hypertension follow?').
        """
        query_strip = user_query.strip()
        is_follow_up = False
        standalone = query_strip
        topic = self._current_topic

        # Check if conversation history exists
        if self._turns:
            is_follow_up = self._detect_follow_up(query_strip)
            if is_follow_up and self._current_topic:
                standalone = self._reformulate_query(query_strip, self._current_topic)
                logger.info(
                    "Follow-Up Question Detected! Topic: '%s' | Original: '%s' -> Reformulated: '%s'",
                    self._current_topic,
                    query_strip,
                    standalone,
                )
            else:
                # If not an explicit follow-up, extract new candidate topic
                new_topic = self._extract_topic_heuristics(query_strip)
                if new_topic:
                    topic = new_topic
        else:
            # First turn: extract primary medical topic
            topic = self._extract_topic_heuristics(query_strip)

        # Assemble recent turns as history dicts for LLM prompt
        history_turns: List[Dict[str, str]] = []
        for turn in self._turns[-self.max_history:]:
            history_turns.append({"role": "user", "content": turn.user_query})
            history_turns.append({"role": "assistant", "content": turn.assistant_answer})

        return ContextualizedQuery(
            raw_query=query_strip,
            standalone_query=standalone,
            medical_topic=topic or "General Clinical Query",
            is_follow_up=is_follow_up,
            history_turns=history_turns,
        )

    def record_turn(
        self,
        user_query: str,
        assistant_answer: str,
        standalone_query: str,
        medical_topic: str,
        sources_count: int = 0,
    ) -> None:
        """Record completed dialogue turn and update active medical topic."""
        self._current_topic = medical_topic or self._current_topic
        turn = DialogueTurn(
            user_query=user_query,
            assistant_answer=assistant_answer,
            standalone_query=standalone_query,
            medical_topic=self._current_topic or "General Medical",
            sources_count=sources_count,
        )
        self._turns.append(turn)
        if len(self._turns) > self.max_history:
            self._turns.pop(0)

    def _detect_follow_up(self, query: str) -> bool:
        """Determines if query is anaphoric or refers to previous conversation context."""
        query_lower = query.lower()
        for pattern in self.FOLLOW_UP_INDICATORS:
            if re.search(pattern, query_lower):
                return True

        # Short elliptical questions are almost always follow-ups
        words = query_lower.split()
        if len(words) <= 7:
            if any(w in words for w in ["precautions", "diet", "foods", "causes", "treatment", "cure", "medicines", "drugs", "symptoms", "complications"]):
                return True

        return False

    def _reformulate_query(self, query: str, topic: str) -> str:
        """Replace demonstratives or append medical topic to make query standalone."""
        # Replace 'this condition', 'the condition', 'this disease', etc. with the topic
        pattern = re.compile(
            r"\b(this|that|these|the)\s+(condition|disease|illness|disorder|syndrome|problem|issue)\b",
            re.IGNORECASE,
        )
        if pattern.search(query):
            return pattern.sub(topic, query)

        # Replace pronouns 'it', 'its'
        pattern_it = re.compile(r"\b(it)\b", re.IGNORECASE)
        if pattern_it.search(query):
            return pattern_it.sub(topic, query)

        # If query asks about precautions/diet without naming condition, attach topic
        query_lower = query.lower()
        if topic.lower() not in query_lower:
            return f"{query} for {topic}"

        return query

    def _extract_topic_heuristics(self, query: str) -> str:
        """Extract core medical topic from user query."""
        clean = query.strip()
        # Common question prefixes including 'common causes of', etc.
        match = re.search(
            r"(?:what is|what are|tell me about|explain|(?:common\s+)?causes of|precautions for|(?:signs and\s+)?symptoms of|treatment for|management of)\s+([^?.,;]+)",
            clean,
            re.IGNORECASE,
        )
        if match:
            candidate = match.group(1).strip()
            # Remove trailing words like 'like', 'in humans', etc.
            candidate = re.sub(r"\b(in humans|in adults|in children|please)\b", "", candidate, flags=re.IGNORECASE).strip()
            if candidate and len(candidate.split()) <= 5:
                return candidate.title()

        # Fallback: remove stop words and take key nouns
        words = [w for w in clean.split() if w.lower() not in {"what", "is", "are", "the", "a", "an", "for", "to", "how", "can", "tell", "me", "about", "common", "causes", "of"}]
        if words:
            return " ".join(words[:4]).rstrip("?.,").title()
        return clean.title()
