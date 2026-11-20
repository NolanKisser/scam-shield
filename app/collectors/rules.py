"""Cheap pattern rules. Fast, offline, and explainable."""
from __future__ import annotations

import re

from ..models import Extracted, Signal

# (name, regex, weight, explanation)
RULES: list[tuple[str, re.Pattern[str], float, str]] = [
    ("urgency", re.compile(r"\b(urgent|immediately|within 24 ?hours|final notice|act now|today only|suspended|expires?)\b", re.I), 0.25,
     "Pressures you to act fast"),
    ("gift_cards", re.compile(r"\b(gift ?cards?|itunes card|google play card|steam card)\b", re.I), 0.6,
     "Asks for gift cards (no real business or agency does this)"),
    ("crypto_or_wire", re.compile(r"\b(bitcoin|btc|crypto|usdt|wire transfer|western union|moneygram|zelle me)\b", re.I), 0.4,
     "Asks for hard-to-reverse payment"),
    ("credential_ask", re.compile(r"\b(verify your (account|identity)|confirm your (password|pin|ssn)|login to (avoid|restore)|update (your )?payment)\b", re.I), 0.4,
     "Asks you to verify an account or payment details"),
    ("toll_or_package", re.compile(r"\b(unpaid toll|toll (balance|violation)|package (could not|couldn't) be delivered|redeliver|delivery fee)\b", re.I), 0.45,
     "Matches common fake toll/package-delivery wording"),
    ("family_emergency", re.compile(r"\b(grandma|grandpa|i'?m in (jail|trouble)|bail|don'?t tell (mom|dad|anyone))\b", re.I), 0.5,
     "Matches the 'family member in trouble' scam script"),
    ("prize", re.compile(r"\b(you('ve| have)? won|winner|claim your (prize|reward)|lottery)\b", re.I), 0.4,
     "Promises an unexpected prize"),
    ("gov_impersonation", re.compile(r"\b(irs|social security (administration|number)|ssa|medicare|arrest warrant)\b", re.I), 0.3,
     "Mentions a government agency (they rarely text first)"),
    ("wrong_number_opener", re.compile(r"^(hi|hello|hey)[,!.]?\s+(is this|are you)\b", re.I), 0.2,
     "'Wrong number' opener used in pig-butchering scams"),
]

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "is.gd", "rb.gy", "cutt.ly", "shorturl.at", "tiny.cc"}
RISKY_TLDS = {"top", "xyz", "icu", "cfd", "sbs", "click", "info", "live", "shop", "buzz", "rest", "vip"}


def check(ex: Extracted) -> list[Signal]:
    out: list[Signal] = []
    for name, rx, weight, why in RULES:
        m = rx.search(ex.text)
        if m:
            out.append(Signal(source="rules", flag=name, evidence=f'{why}: "{m.group(0)}"', weight=weight))

    for d in ex.domains:
        if d in SHORTENERS:
            out.append(Signal(source="rules", flag="url_shortener", evidence=f"Link hidden behind shortener {d}", weight=0.3))
        if d.rsplit(".", 1)[-1] in RISKY_TLDS:
            out.append(Signal(source="rules", flag="risky_tld", evidence=f"{d} uses a TLD common in scams", weight=0.25))
    return out
