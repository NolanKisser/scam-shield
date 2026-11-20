"""Pull URLs, domains, phone numbers and money amounts out of message text."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from .models import Extracted

# Matches http(s) links and bare domains like "usps-redelivery.com/abc"
_URL_RE = re.compile(
    r"\b((?:https?://)?(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s<>\"']*)?)",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
_MONEY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?")

# Things the URL regex catches that aren't links
_NOT_DOMAINS = {"e.g", "i.e", "a.m", "p.m"}


def registrable_domain(host: str) -> str:
    """Naive eTLD+1 (good enough for a hackathon; swap in tldextract later)."""
    host = host.lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in {"co", "com", "org", "gov", "ac"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def extract(text: str) -> Extracted:
    urls: list[str] = []
    domains: list[str] = []
    for m in _URL_RE.finditer(text):
        raw = m.group(1).rstrip(".,;:!?)")
        if raw.lower() in _NOT_DOMAINS or "@" in text[max(0, m.start() - 1) : m.start()]:
            continue  # skip emails' domain part
        url = raw if raw.lower().startswith("http") else f"http://{raw}"
        host = urlparse(url).hostname or ""
        if not host or "." not in host:
            continue
        urls.append(url)
        d = registrable_domain(host)
        if d not in domains:
            domains.append(d)

    phones = list(dict.fromkeys(m.group(0).strip() for m in _PHONE_RE.finditer(text)))
    money = list(dict.fromkeys(m.group(0) for m in _MONEY_RE.finditer(text)))
    return Extracted(text=text, urls=urls, domains=domains, phone_numbers=phones, money_amounts=money)
