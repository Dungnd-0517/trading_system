from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SentimentResult:
    score: float
    impact: Literal["LOW", "MEDIUM", "HIGH_RISK_HALT"]
    summary: str


def validate_sentiment(score: float, impact: str, summary: str) -> SentimentResult:
    if not -1.0 <= score <= 1.0:
        raise ValueError("sentiment score must be between -1 and 1")
    if impact not in {"LOW", "MEDIUM", "HIGH_RISK_HALT"}:
        raise ValueError("unsupported impact level")
    return SentimentResult(score, impact, summary.strip())