"""FastAPI entry point: web API + Twilio SMS/voice webhooks."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse

from . import llm, notify, pipeline
from .config import settings
from .models import Verdict

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Scam Shield")
STATIC = Path(__file__).resolve().parent.parent / "static"
MAX_IMAGE_BYTES = 5 * 1024 * 1024


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


# ---------- Web API ----------

@app.post("/api/check", response_model=Verdict)
async def check(text: str = Form(""), image: UploadFile | None = File(None)) -> Verdict:
    if image is not None and image.filename:
        if image.content_type not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
            raise HTTPException(415, "Upload a PNG, JPEG, WebP or GIF screenshot")
        data = await image.read()
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Screenshot too large (max 5 MB)")
        text = (text + "\n" + await llm.transcribe_image(data, image.content_type)).strip()
    if not text.strip():
        raise HTTPException(400, "Paste a message or upload a screenshot")
    return await pipeline.analyze(text)


class DeviceMessage(BaseModel):
    """Sent by the phone app when a text arrives from a number not in contacts."""

    sender: str  # who texted the user
    body: str
    owner: str = ""  # the user's own number, used to look up their guardian


class DeviceVerdict(BaseModel):
    verdict: Verdict
    notify: bool  # should the phone show a warning notification?
    notification_text: str
    guardian_alerted: bool


@app.post("/api/device/check", response_model=DeviceVerdict)
async def device_check(msg: DeviceMessage) -> DeviceVerdict:
    # TODO before shipping: authenticate devices (per-install token) and rate-limit.
    v = await pipeline.analyze(f"[From {msg.sender}]\n{msg.body}")
    alerted = notify.maybe_alert_guardian(msg.owner, v) if msg.owner else False
    return DeviceVerdict(
        verdict=v,
        notify=v.risk_level != "LOW",
        notification_text=notify.format_reply(v, simple=notify.is_protected(msg.owner)),
        guardian_alerted=alerted,
    )


# ---------- Twilio ----------

async def _verified_form(request: Request) -> dict[str, str]:
    form = {k: str(v) for k, v in (await request.form()).items()}
    if settings.validate_twilio_signature:
        url = (settings.public_base_url.rstrip("/") + request.url.path) if settings.public_base_url else str(request.url)
        ok = RequestValidator(settings.twilio_auth_token).validate(
            url, form, request.headers.get("X-Twilio-Signature", ""))
        if not ok:
            raise HTTPException(403, "Bad Twilio signature")
    return form


def _twiml(resp) -> Response:
    return Response(str(resp), media_type="application/xml")


@app.post("/twilio/sms")
async def twilio_sms(request: Request, bg: BackgroundTasks) -> Response:
    form = await _verified_form(request)
    sender, body = form.get("From", ""), form.get("Body", "")
    v = await pipeline.analyze(body)
    bg.add_task(notify.maybe_alert_guardian, sender, v)
    out = MessagingResponse()
    out.message(notify.format_reply(v, simple=notify.is_protected(sender)))
    return _twiml(out)


@app.post("/twilio/voice")
async def twilio_voice(request: Request) -> Response:
    """Caller plays (or describes) the suspicious voicemail; Twilio records + transcribes it."""
    await _verified_form(request)
    out = VoiceResponse()
    out.say("Scam Shield. After the beep, play the suspicious voicemail or describe the call. "
            "Press pound when done. We'll text you the result.")
    out.record(max_length=120, finish_on_key="#", transcribe=True,
               transcribe_callback="/twilio/transcription", play_beep=True)
    return _twiml(out)


@app.post("/twilio/transcription")
async def twilio_transcription(request: Request, bg: BackgroundTasks) -> Response:
    form = await _verified_form(request)
    caller, text = form.get("From", ""), form.get("TranscriptionText", "")
    if form.get("TranscriptionStatus") == "completed" and text:
        v = await pipeline.analyze(f"[Voicemail transcript]\n{text}")
        bg.add_task(notify.send_sms, caller, notify.format_reply(v, simple=notify.is_protected(caller)))
        bg.add_task(notify.maybe_alert_guardian, caller, v)
    return Response(status_code=204)
