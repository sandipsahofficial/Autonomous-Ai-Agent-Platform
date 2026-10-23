import re
from typing import List
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult


class TextSummarizerInput(BaseModel):
    text: str = Field(..., min_length=20, max_length=50000, description="Source text to summarize")
    max_sentences: int = Field(default=3, ge=1, le=10, description="Maximum number of sentences in output summary")


class TextSummarizerOutput(BaseModel):
    summary: str
    original_sentences_count: int
    summary_sentences_count: int
    compression_ratio: float


class TextSummarizerTool(BaseTool):
    """
    Extractive text summarizer without external API dependencies.
    Ranks sentences by term frequency and extracts top core sentences.
    """
    name = "text_summarizer"
    version = "1.0.0"
    description = "Generates a concise extractive summary from text without external network calls."
    args_schema = TextSummarizerInput
    output_schema = TextSummarizerOutput
    required_permissions = ["text:summarize"]
    timeout_seconds = 3
    max_output_size_bytes = 8192
    is_enabled = True
    requires_approval = False
    idempotent = True

    def run(self, text: str, max_sentences: int = 3) -> ToolResult:
        try:
            # Tokenize into sentences
            raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
            if not raw_sentences:
                return ToolResult(success=False, output=None, error="Input text contained no valid sentences.")

            if len(raw_sentences) <= max_sentences:
                summary = " ".join(raw_sentences)
                return ToolResult(
                    success=True,
                    output={
                        "summary": summary,
                        "original_sentences_count": len(raw_sentences),
                        "summary_sentences_count": len(raw_sentences),
                        "compression_ratio": 1.0,
                    },
                )

            # Frequency scoring for words
            words = re.findall(r"\w+", text.lower())
            stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "is", "was", "are", "were"}
            freq: dict = {}
            for w in words:
                if w not in stop_words and len(w) > 2:
                    freq[w] = freq.get(w, 0) + 1

            # Score each sentence
            scored: List[tuple] = []
            for idx, s in enumerate(raw_sentences):
                score = sum(freq.get(w, 0) for w in re.findall(r"\w+", s.lower()))
                scored.append((score, idx, s))

            # Pick top sentences and sort by original narrative appearance
            scored.sort(key=lambda item: item[0], reverse=True)
            chosen = sorted(scored[:max_sentences], key=lambda item: item[1])
            summary = " ".join(s for _, _, s in chosen)

            ratio = round(len(summary) / max(len(text), 1), 3)

            return ToolResult(
                success=True,
                output={
                    "summary": summary,
                    "original_sentences_count": len(raw_sentences),
                    "summary_sentences_count": len(chosen),
                    "compression_ratio": ratio,
                },
            )
        except Exception as exc:
            return ToolResult(success=False, output=None, error=f"Summarization error: {str(exc)}")
