"""Reply formatting and guardian alerts over SMS."""
from __future__ import annotations

import logging

from .config import settings
from .models import Verdict

log = logging.getLogger(__name__)

_EMOJI = {"HIGH": "🚩", "MEDIUM": "⚠️", "LOW": "✅"}


def format_reply(v: Verdict, simple: bool = False) -> str:
    pct = round(v.risk_score * 100)
    head = f"{_EMOJI[v.risk_level]} {v.risk_level} RISK ({pct}%)"
    if simple:  # guardian-protected users get one short, clear instruction
        return f"{head}\n{v.recommended_action}"
    lines = [head]
    if v.scam_type and v.scam_type.lower() != "none":
        lines.append(f"Looks like: {v.scam_type}")
    lines += [f"• {f.evidence}" for f in v.red_flags[:3]]
    lines.append(v.recommended_action)
    return "\n".join(lines)[:1500]  # stay within a few SMS segments


def format_guardian_alert(protected: str, v: Verdict) -> str:
    return (f"Scam Shield: {protected} just received a likely scam "
            f"({v.scam_type}, {round(v.risk_score * 100)}% risk). Consider giving them a call.\n"
            + "\n".join(f"• {f.evidence}" for f in v.red_flags[:2]))


def send_sms(to: str, body: str) -> None:
    if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_phone_number):
        log.info("[sms disabled] to %s: %s", to, body)
        return
    from twilio.rest import Client

    Client(settings.twilio_account_sid, settings.twilio_auth_token).messages.create(
        to=to, from_=settings.twilio_phone_number, body=body)


def maybe_alert_guardian(sender: str, v: Verdict) -> bool:
    guardian = settings.guardian_map().get(sender)
    if guardian and v.risk_score >= settings.guardian_alert_threshold:
        send_sms(guardian, format_guardian_alert(sender, v))
        return True
    return False


def is_protected(number: str) -> bool:
    return number in settings.guardian_map()
