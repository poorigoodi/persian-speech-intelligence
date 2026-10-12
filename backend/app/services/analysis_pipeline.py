"""Orchestrates LLM analysis steps for a completed transcript."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.llm.base import LLMProvider
from app.schemas.analysis import (
    DecisionItem,
    DetailedSummary,
    ExtractedEntities,
    SentimentResult,
    TaskItem,
    TopicItem,
)
from app.services.extraction_service import ExtractionService
from app.services.sentiment_service import SentimentService
from app.services.summarization_service import SummarizationService


@dataclass
class AnalysisBundle:
    short_summary: str
    detailed_summary: DetailedSummary
    topics: list[TopicItem]
    sentiment: SentimentResult
    extracted_entities: ExtractedEntities
    action_items: list[TaskItem]
    decisions: list[DecisionItem]

    def as_db_payload(self) -> dict[str, Any]:
        return {
            "short_summary": self.short_summary,
            "detailed_summary": self.detailed_summary.model_dump(),
            "topics": [t.model_dump() for t in self.topics],
            "sentiment": self.sentiment.model_dump(),
            "extracted_entities": self.extracted_entities.model_dump(),
            "action_items": [a.model_dump() for a in self.action_items],
            "decisions": [d.model_dump() for d in self.decisions],
        }


class AnalysisPipeline:
    def __init__(self, llm: LLMProvider) -> None:
        self.summarizer = SummarizationService(llm)
        self.sentiment = SentimentService(llm)
        self.extraction = ExtractionService(llm)

    async def run(self, transcript: str) -> AnalysisBundle:
        short = await self.summarizer.short_summary(transcript)
        detailed = await self.summarizer.detailed_summary(transcript)
        topics = await self.extraction.extract_topics(transcript)
        sentiment = await self.sentiment.analyze(transcript)
        entities = await self.extraction.extract_entities(transcript)

        action_items = self.extraction.action_items_from_entities(entities)
        decisions = self.extraction.decisions_from_entities(entities)

        # Prefer explicit extraction; fall back to detailed summary lists without inventing
        if not action_items and detailed.action_items:
            action_items = [
                TaskItem(description=item, assigned_to=None, deadline=None)
                for item in detailed.action_items
                if item.strip()
            ]
        if not decisions and detailed.decisions:
            decisions = [
                DecisionItem(description=item)
                for item in detailed.decisions
                if item.strip()
            ]

        return AnalysisBundle(
            short_summary=short,
            detailed_summary=detailed,
            topics=topics,
            sentiment=sentiment,
            extracted_entities=entities,
            action_items=action_items,
            decisions=decisions,
        )
