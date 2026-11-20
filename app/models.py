"""Data shapes shared across the pipeline."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Channel(str, Enum):
    SMS = "sms"
    VOICEMAIL = "voicemail"
    WEB = "web"
    SCREENSHOT = "screenshot"


class Extracted(BaseModel):
    """Entities pulled out of the raw message text."""

    text: str
    urls: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    phone_numbers: list[str] = Field(default_factory=list)
    money_amounts: list[str] = Field(default_factory=list)


class Signal(BaseModel):
    """One piece of evidence from a collector.

    weight: how suspicious this is on its own (0-1).
    floor:  if set, the final score can never drop below this
            (used for hard evidence such as a blocklist hit).
    """

    source: str
    flag: str
    evidence: str
    weight: float = 0.0
    floor: float | None = None


class RedFlag(BaseModel):
    flag: str
    evidence: str


class LLMVerdict(BaseModel):
    """Structured output requested from Claude."""

    risk_score: float  # 0.0 (safe) .. 1.0 (certain scam)
    scam_type: str  # e.g. "toll payment", "grandparent", "none"
    red_flags: list[RedFlag]
    recommended_action: str
    plain_language_summary: str


class Verdict(BaseModel):
    """Final result returned to users."""

    risk_score: float
    risk_level: str  # LOW / MEDIUM / HIGH
    scam_type: str
    red_flags: list[RedFlag]
    recommended_action: str
    summary: str
    signals: list[Signal]
    extracted: Extracted
    llm_used: bool
