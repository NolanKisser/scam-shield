"""Run every collector in parallel, each with its own timeout."""
from __future__ import annotations

import asyncio
import logging

import httpx

from ..config import settings
from ..models import Extracted, Signal
from . import domain_age, lookalike, reputation, rules

log = logging.getLogger(__name__)


async def _guard(name: str, coro) -> list[Signal]:
    try:
        return await asyncio.wait_for(coro, timeout=settings.collector_timeout_s)
    except Exception as e:  # a slow or broken collector must never sink the verdict
        log.warning("collector %s skipped: %r", name, e)
        return []


async def collect(ex: Extracted) -> list[Signal]:
    signals = rules.check(ex) + lookalike.check(ex)
    async with httpx.AsyncClient(timeout=settings.collector_timeout_s) as client:
        results = await asyncio.gather(
            _guard("domain_age", domain_age.check(ex, client)),
            _guard("safe_browsing", reputation.safe_browsing(ex, client)),
            _guard("urlhaus", reputation.urlhaus(ex, client)),
        )
    for r in results:
        signals.extend(r)
    return signals
