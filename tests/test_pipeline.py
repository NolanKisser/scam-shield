"""Offline tests: network collectors and Claude are stubbed out."""
import pytest

from app import collectors, llm, pipeline
from app.collectors import lookalike, rules
from app.extract import extract
from app.models import LLMVerdict

SCAM = "USPS: Your package could not be delivered due to an unpaid fee. Pay $1.99 within 24 hours: https://usps-redelivery-help.top/track"
LEGIT = "Your Chase verification code is 482913. Don't share it with anyone. Chase will never call to ask for it."


def test_extract_finds_url_domain_money():
    ex = extract(SCAM)
    assert ex.domains == ["usps-redelivery-help.top"]
    assert "$1.99" in ex.money_amounts


def test_extract_ignores_email_domain():
    assert extract("email me at jane@example.com").domains == []


def test_lookalike_flags_fake_but_not_real():
    assert lookalike.check(extract("go to usps-redelivery-help.top"))
    assert lookalike.check(extract("sign in at paypa1.com"))
    assert not lookalike.check(extract("track at https://tools.usps.com/go"))


def test_rules_hit_scam_and_skip_legit():
    flags = {s.flag for s in rules.check(extract(SCAM))}
    assert {"toll_or_package", "urgency", "risky_tld"} <= flags
    assert rules.check(extract(LEGIT)) == []


@pytest.fixture
def offline(monkeypatch):
    async def no_network(ex, client):
        return []
    monkeypatch.setattr(collectors.domain_age, "check", no_network)
    monkeypatch.setattr(collectors.reputation, "safe_browsing", no_network)
    monkeypatch.setattr(collectors.reputation, "urlhaus", no_network)


@pytest.mark.asyncio
async def test_rules_only_scores(offline):
    scam = await pipeline.analyze(SCAM, use_llm=False)
    legit = await pipeline.analyze(LEGIT, use_llm=False)
    assert scam.risk_level == "HIGH"
    assert legit.risk_level == "LOW"


@pytest.mark.asyncio
async def test_floor_beats_llm(offline, monkeypatch):
    """A lookalike domain keeps the score high even if the LLM is fooled."""
    async def fooled(text, signals):
        return LLMVerdict(risk_score=0.05, scam_type="none", red_flags=[],
                          recommended_action="ok", plain_language_summary="fine")
    monkeypatch.setattr(llm, "judge", fooled)
    v = await pipeline.analyze(SCAM)
    assert v.llm_used and v.risk_score >= 0.75
