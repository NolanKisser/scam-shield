"""URL blocklists: Google Safe Browsing and abuse.ch URLhaus. Both optional."""
from __future__ import annotations

import httpx

from ..config import settings
from ..models import Extracted, Signal


async def safe_browsing(ex: Extracted, client: httpx.AsyncClient) -> list[Signal]:
    if not settings.google_safe_browsing_key or not ex.urls:
        return []
    body = {
        "client": {"clientId": "scam-shield", "clientVersion": "0.1"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": u} for u in ex.urls],
        },
    }
    r = await client.post(
        "https://safebrowsing.googleapis.com/v4/threatMatches:find",
        params={"key": settings.google_safe_browsing_key}, json=body,
    )
    r.raise_for_status()
    return [
        Signal(source="safe_browsing", flag="blocklisted_url",
               evidence=f"Google Safe Browsing lists {m['threat']['url']} as {m['threatType']}",
               weight=0.95, floor=0.9)
        for m in r.json().get("matches", [])
    ]


async def urlhaus(ex: Extracted, client: httpx.AsyncClient) -> list[Signal]:
    if not settings.urlhaus_auth_key:
        return []
    out: list[Signal] = []
    for url in ex.urls[:3]:
        r = await client.post("https://urlhaus-api.abuse.ch/v1/url/",
                              data={"url": url}, headers={"Auth-Key": settings.urlhaus_auth_key})
        if r.status_code == 200 and r.json().get("query_status") == "ok":
            out.append(Signal(source="urlhaus", flag="blocklisted_url",
                              evidence=f"URLhaus lists {url} as malicious", weight=0.95, floor=0.9))
    return out
