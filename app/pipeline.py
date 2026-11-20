"""extract -> collect signals -> Claude -> blend into a final verdict."""
from __future__ import annotations

from . import collectors, llm
from .extract import extract
from .models import LLMVerdict, RedFlag, Signal, Verdict

LLM_WEIGHT = 0.6  # share of the final score from Claude when it's available


def heuristic_score(signals: list[Signal]) -> float:
    """Noisy-OR: each signal independently raises suspicion."""
    p_clean = 1.0
    for s in signals:
        p_clean *= 1.0 - s.weight
    return 1.0 - p_clean


def blend(signals: list[Signal], v: LLMVerdict | None) -> float:
    h = heuristic_score(signals)
    score = h if v is None else (1 - LLM_WEIGHT) * h + LLM_WEIGHT * v.risk_score
    floors = [s.floor for s in signals if s.floor is not None]
    return round(max([score, *floors]), 3)


def level(score: float) -> str:
    return "HIGH" if score >= 0.7 else "MEDIUM" if score >= 0.4 else "LOW"


async def analyze(text: str, use_llm: bool = True) -> Verdict:
    ex = extract(text)
    signals = await collectors.collect(ex)
    v = await llm.judge(text, signals) if use_llm else None
    score = blend(signals, v)

    if v is not None:
        flags, scam_type = v.red_flags, v.scam_type
        action, summary = v.recommended_action, v.plain_language_summary
    else:  # rules-only fallback so the service still answers if Claude is down
        flags = [RedFlag(flag=s.flag, evidence=s.evidence) for s in signals]
        scam_type = "unknown" if signals else "none"
        action = ("Don't click links or reply. Contact the company using its official app or website."
                  if score >= 0.4 else "No obvious red flags, but stay cautious with links.")
        summary = f"{len(signals)} warning sign(s) found."

    return Verdict(
        risk_score=score, risk_level=level(score), scam_type=scam_type, red_flags=flags,
        recommended_action=action, summary=summary, signals=signals, extracted=ex,
        llm_used=v is not None,
    )
