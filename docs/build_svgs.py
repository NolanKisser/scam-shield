"""Build the README diagrams.

Sources live in docs/src/*.svg and contain a `<!--INJECT-->` marker inside <defs>.
This script replaces it with the embedded Geist fonts (so the images look the
same on every OS), the shared base styles, and the arrowhead marker, then writes
docs/<name>.svg. Run from anywhere:  python docs/build_svgs.py
"""
from __future__ import annotations

import base64
from pathlib import Path

DOCS = Path(__file__).resolve().parent
FONTS = DOCS / "fonts"


def font_face(family: str, file: str, weights: str) -> str:
    data = base64.b64encode((FONTS / file).read_bytes()).decode()
    return (f'@font-face{{font-family:"{family}";font-weight:{weights};'
            f'src:url(data:font/woff2;base64,{data}) format("woff2");}}')


BASE_CSS = """
text{font-family:Geist,"Segoe UI",system-ui,sans-serif;fill:#e2e8f0}
.mono{font-family:"Geist Mono",Consolas,Menlo,monospace}
.wire{fill:none;stroke:#5b6b84;stroke-width:1.8}
.card{fill:#162033;stroke:#2a3850}
.title{font-weight:700;fill:#f8fafc;letter-spacing:-0.02em}
.lead,.sub{fill:#a9b6ca}
.name{font-weight:600;fill:#f1f5f9}
.body{fill:#cbd5e1}
.strong{font-weight:700}
.red{fill:#f87171}.amber{fill:#fbbf24}.green{fill:#4ade80}.teal{fill:#2dd4bf}.purple{fill:#b9a5ff}
"""

MARKER = ('<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
          'markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" '
          'fill="#5b6b84"/></marker>')


def main() -> None:
    inject = (
        "<style>"
        + font_face("Geist", "Geist.woff2", "100 900")
        + font_face("Geist Mono", "GeistMono.woff2", "100 900")
        + BASE_CSS.replace("\n", "")
        + "</style>"
        + MARKER
    )
    for src in sorted((DOCS / "src").glob("*.svg")):
        text = src.read_text(encoding="utf-8")
        if "<!--INJECT-->" not in text:
            raise SystemExit(f"{src.name}: missing <!--INJECT--> marker")
        out = DOCS / src.name
        out.write_text(text.replace("<!--INJECT-->", inject), encoding="utf-8", newline="\n")
        print(f"built {out.relative_to(DOCS.parent)} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
