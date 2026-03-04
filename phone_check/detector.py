"""Core phone model detection using the device-detection waterfall.

Phase 1 (server-side): Parse User-Agent with Matomo device_detector.
Phase 2 (client hints): Merge in browser-supplied Client Hints data (Android).
Phase 3 (iPhone resolution): Combine screen dimensions, iOS version, and
         canvas GPU fingerprint to narrow down the specific iPhone model.

The detector resolves specific *models* (e.g. "Galaxy S22", "Pixel 8",
"iPhone 15 Pro"), not just make/OS.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from device_detector import DeviceDetector

from phone_check.canvas_db import lookup_chip
from phone_check.iphone_db import resolve_iphone


@dataclass(frozen=True)
class DeviceInfo:
    brand: str
    model: str
    os_name: str
    os_version: str
    device_type: str
    confidence: str  # "high", "medium", "low", "none"
    # When multiple models match (common for iPhones), list them here.
    possible_models: tuple[str, ...] = ()

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
    screen_width: int | None = None,
    screen_height: int | None = None,
    device_pixel_ratio: float | None = None,
    gpu_chip: str | None = None,
    canvas_hash: str | None = None,
) -> DeviceInfo:
    """Full detection waterfall.

    1. Parse the UA string with device_detector.
    2. For Android: if Client Hints data was supplied, prefer it.
    3. For iOS: combine screen dimensions, iOS version from the UA,
       and an optional GPU chip identifier from canvas fingerprinting
       to narrow down the specific iPhone model.
    """
    info = detect_from_ua(user_agent)

    # --- Android path: Client Hints override ---
    if client_hint_model or client_hint_brand:
        brand = client_hint_brand or info.brand
        model = client_hint_model or info.model
        confidence = _assess_confidence(brand, model, info.os_name)
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

    # --- iOS path: screen + iOS version + GPU chip resolution ---
    if _is_ios(info):
        return _resolve_iphone_model(info, screen_width, screen_height,
                                     device_pixel_ratio, gpu_chip, canvas_hash)

    return info


# ---------------------------------------------------------------------------
# iPhone resolution
# ---------------------------------------------------------------------------

def _resolve_iphone_model(
    info: DeviceInfo,
    screen_width: int | None,
    screen_height: int | None,
    device_pixel_ratio: float | None,
    gpu_chip: str | None,
    canvas_hash: str | None = None,
) -> DeviceInfo:
    """Use screen/iOS/GPU signals to narrow the iPhone model."""
    ios_major = _parse_ios_major(info.os_version)

    # Canvas hash fallback: if no direct GPU chip but we have a canvas hash,
    # try to resolve the chip from the calibration database.
    if not gpu_chip and canvas_hash:
        resolved_chip = lookup_chip(canvas_hash)
        if resolved_chip:
            gpu_chip = resolved_chip

    candidates = resolve_iphone(
        screen_width=screen_width,
        screen_height=screen_height,
        device_pixel_ratio=device_pixel_ratio,
        ios_version=ios_major,
        gpu_chip=gpu_chip,
    )

    if len(candidates) == 1:
        return DeviceInfo(
            brand="Apple",
            model=candidates[0],
            os_name=info.os_name,
            os_version=info.os_version,
            device_type=info.device_type,
            confidence="high",
            possible_models=tuple(candidates),
        )
    elif len(candidates) > 1:
        # Pick the most recent model as the "best guess" — it's the
        # most statistically likely device still in active use.
        return DeviceInfo(
            brand="Apple",
            model=candidates[-1],
            os_name=info.os_name,
            os_version=info.os_version,
            device_type=info.device_type,
            confidence="medium",
            possible_models=tuple(candidates),
        )
    else:
        # No screen data or no match — fall back to the generic result
        return info


def _is_ios(info: DeviceInfo) -> bool:
    return info.os_name.lower() in ("ios", "mac")


_IOS_MAJOR_RE = re.compile(r"^(\d+)")


def _parse_ios_major(os_version: str) -> int | None:
    m = _IOS_MAJOR_RE.match(os_version)
    return int(m.group(1)) if m else None


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
