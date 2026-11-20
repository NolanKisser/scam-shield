"""Detect domains imitating well-known brands (usps-tolls.com, paypa1.com...)."""
from __future__ import annotations

from ..models import Extracted, Signal

# brand keyword -> the brand's real registrable domains
BRANDS: dict[str, set[str]] = {
    "usps": {"usps.com"}, "ups": {"ups.com"}, "fedex": {"fedex.com"}, "dhl": {"dhl.com"},
    "amazon": {"amazon.com"}, "paypal": {"paypal.com"}, "apple": {"apple.com"}, "icloud": {"icloud.com", "apple.com"},
    "netflix": {"netflix.com"}, "chase": {"chase.com"}, "wellsfargo": {"wellsfargo.com"},
    "bankofamerica": {"bankofamerica.com"}, "ezpass": {"e-zpassny.com", "ezpassnj.com", "ezpassva.com"},
    "fastrak": {"bayareafastrak.org"}, "sunpass": {"sunpass.com"}, "irs": {"irs.gov"}, "venmo": {"venmo.com"},
    "zelle": {"zellepay.com"}, "coinbase": {"coinbase.com"}, "microsoft": {"microsoft.com"}, "google": {"google.com"},
}

_HOMOGLYPHS = str.maketrans({"0": "o", "1": "l", "3": "e", "5": "s", "@": "a", "$": "s"})


def _levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def check(ex: Extracted) -> list[Signal]:
    out: list[Signal] = []
    for domain in ex.domains:
        label = domain.split(".")[0]
        normalized = label.translate(_HOMOGLYPHS).replace("-", "")
        for brand, real in BRANDS.items():
            if domain in real:
                break  # it's the genuine site
            contains = brand in normalized and len(brand) >= 4
            close = len(brand) >= 5 and _levenshtein(normalized, brand) <= 1
            if contains or close:
                out.append(Signal(
                    source="lookalike", flag="brand_lookalike",
                    evidence=f"{domain} imitates {brand.upper()} but isn't {' / '.join(sorted(real))}",
                    weight=0.7, floor=0.75,
                ))
                break
    return out
