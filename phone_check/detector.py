"""Core phone model detection using the device-detection waterfall.

Phase 1 (server-side): Parse User-Agent with Matomo device_detector.
Phase 2 (client hints): Merge in browser-supplied Client Hints data if available.

The detector resolves specific *models* (e.g. "Galaxy S22", "Pixel 8"),
not just make/OS.
"""

from __future__ import annotations

from dataclasses import dataclass
from device_detector import DeviceDetector


@dataclass(frozen=True)
class DeviceInfo:
    brand: str
    model: str
    os_name: str
    os_version: str
    device_type: str
    confidence: str  # "high", "medium", "low", "none"

    @property
    def identified(self) -> bool:
        """True when we resolved a specific model (not just 'iPhone')."""
        return self.confidence in ("high", "medium") and bool(self.model)


def detect_from_ua(user_agent: str) -> DeviceInfo:
    """Detect phone model from a User-Agent string (server-side Phase 1).

    Returns a DeviceInfo with whatever the UA string reveals.  For most
    Android phones this gives a concrete model; for iPhones it can only
    return 'iPhone' because Apple strips the model from the UA.
    """
    parsed = DeviceDetector(user_agent).parse()

    brand = parsed.device_brand() or ""
    model = parsed.device_model() or ""
    os_name = parsed.os_name() or ""
    os_version = parsed.os_version() or ""
    device_type = parsed.device_type() or ""

    confidence = _assess_confidence(brand, model, os_name)
    return DeviceInfo(
        brand=brand,
        model=model,
        os_name=os_name,
        os_version=os_version,
        device_type=device_type,
        confidence=confidence,
    )


def detect(
    user_agent: str,
    *,
    client_hint_model: str | None = None,
    client_hint_brand: str | None = None,
) -> DeviceInfo:
    """Full detection waterfall.

    1. Parse the UA string with device_detector.
    2. If Client Hints data was supplied by the browser, prefer it —
       it tends to be more accurate on modern Android.
    """
    info = detect_from_ua(user_agent)

    # Client Hints override: the browser's CH-UA-Model header is the most
    # reliable source for Android model names.
    if client_hint_model or client_hint_brand:
        brand = client_hint_brand or info.brand
        model = client_hint_model or info.model
        confidence = _assess_confidence(brand, model, info.os_name)
        # Bump confidence when Client Hints provided a concrete model
        if client_hint_model and confidence == "medium":
            confidence = "high"
        return DeviceInfo(
            brand=brand,
            model=model,
            os_name=info.os_name,
            os_version=info.os_version,
            device_type=info.device_type,
            confidence=confidence,
        )

    return info


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_GENERIC_MODELS = {"iPhone", "iPad", "iPod", "Android", ""}


def _assess_confidence(brand: str, model: str, os_name: str) -> str:
    """Rate how specific the identification is.

    high   – we have brand + a concrete model name (e.g. "Galaxy S22")
    medium – we have brand + a model string, but it may be a product-line
             name rather than a precise variant (e.g. "Galaxy A")
    low    – we know the OS/brand but not the model (typical for iOS)
    none   – we couldn't determine anything useful
    """
    if not brand and not model:
        return "none"
    if model in _GENERIC_MODELS:
        return "low"
    # If the model string is very short (≤3 chars) it's probably a
    # product-line abbreviation, not a real model.
    if len(model) <= 3:
        return "medium"
    return "high"
