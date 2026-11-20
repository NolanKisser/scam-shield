"""Domain age via RDAP (free, no key). Brand-new domains are a strong scam signal."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..models import Extracted, Signal


async def _registered(client: httpx.AsyncClient, domain: str) -> datetime | None:
    r = await client.get(f"https://rdap.org/domain/{domain}", follow_redirects=True)
    if r.status_code != 200:
        return None
    for ev in r.json().get("events", []):
        if ev.get("eventAction") == "registration":
            return datetime.fromisoformat(ev["eventDate"].replace("Z", "+00:00"))
    return None


async def check(ex: Extracted, client: httpx.AsyncClient) -> list[Signal]:
    out: list[Signal] = []
    now = datetime.now(timezone.utc)
    for domain in ex.domains[:3]:
        try:
            reg = await _registered(client, domain)
        except (httpx.HTTPError, ValueError):
            continue
        if not reg:
            continue
        days = (now - reg).days
        if days < 30:
            out.append(Signal(source="domain_age", flag="new_domain",
                              evidence=f"{domain} was registered {days} day(s) ago", weight=0.6, floor=0.6))
        elif days < 180:
            out.append(Signal(source="domain_age", flag="young_domain",
                              evidence=f"{domain} is only {days} days old", weight=0.25))
    return out
