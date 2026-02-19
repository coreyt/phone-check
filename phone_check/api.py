"""FastAPI application for phone model detection."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel

from phone_check.detector import DeviceInfo, detect

app = FastAPI(title="phone-check", version="0.1.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class IdentifyRequest(BaseModel):
    user_agent: str
    client_hint_model: str | None = None
    client_hint_brand: str | None = None


class IdentifyResponse(BaseModel):
    brand: str
    model: str
    os_name: str
    os_version: str
    device_type: str
    confidence: str
    identified: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the client-side detection page."""
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(html_path.read_text())


@app.post("/api/identify", response_model=IdentifyResponse)
async def identify_device(body: IdentifyRequest):
    """Identify a phone model from a User-Agent string.

    Optionally accepts Client Hints (model, brand) gathered by the
    browser's JavaScript for higher accuracy on modern Android.
    """
    info: DeviceInfo = detect(
        body.user_agent,
        client_hint_model=body.client_hint_model,
        client_hint_brand=body.client_hint_brand,
    )
    return IdentifyResponse(
        brand=info.brand,
        model=info.model,
        os_name=info.os_name,
        os_version=info.os_version,
        device_type=info.device_type,
        confidence=info.confidence,
        identified=info.identified,
    )


@app.get("/api/identify", response_model=IdentifyResponse)
async def identify_device_auto(request: Request):
    """Auto-detect the requesting device from its User-Agent header.

    Handy for quick browser-based testing: just open this URL on a phone.
    Also reads Sec-CH-UA-Model / Sec-CH-UA-Full-Version-List Client Hints
    headers when the browser sends them.
    """
    ua = request.headers.get("user-agent", "")
    ch_model = request.headers.get("sec-ch-ua-model") or None
    # Strip quotes that browsers wrap around Client Hints values
    if ch_model:
        ch_model = ch_model.strip('"')

    info: DeviceInfo = detect(ua, client_hint_model=ch_model)
    return IdentifyResponse(
        brand=info.brand,
        model=info.model,
        os_name=info.os_name,
        os_version=info.os_version,
        device_type=info.device_type,
        confidence=info.confidence,
        identified=info.identified,
    )
