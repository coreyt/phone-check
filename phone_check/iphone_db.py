"""iPhone model database keyed by observable browser signals.

Each entry maps a combination of (screen_width, screen_height, device_pixel_ratio)
to the set of iPhone models that share those dimensions.  We then narrow
further using the iOS version reported in the User-Agent and (optionally)
a canvas-derived GPU fingerprint that identifies the Apple GPU generation.

Sources:
  - https://www.ios-resolution.com/
  - https://yesviz.com/iphones.php
  - https://iosref.com/res
  - https://iosref.com/ios
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IPhoneModel:
    name: str          # Marketing name, e.g. "iPhone 15 Pro"
    chip: str          # SoC, e.g. "A16"
    min_ios: int       # First iOS version shipped with
    max_ios: int | None  # Last supported iOS (None = still supported)


# ------------------------------------------------------------------
# Master list of iPhones (iPhone 6 and later — older ones are irrelevant
# for a BLE compatibility checker).
# ------------------------------------------------------------------

ALL_IPHONES: list[IPhoneModel] = [
    # 4.7" / 5.5" era
    IPhoneModel("iPhone 6",              "A8",   8,  12),
    IPhoneModel("iPhone 6 Plus",         "A8",   8,  12),
    IPhoneModel("iPhone 6s",             "A9",   9,  15),
    IPhoneModel("iPhone 6s Plus",        "A9",   9,  15),
    IPhoneModel("iPhone 7",              "A10",  10, 15),
    IPhoneModel("iPhone 7 Plus",         "A10",  10, 15),
    IPhoneModel("iPhone 8",              "A11",  11, 16),
    IPhoneModel("iPhone 8 Plus",         "A11",  11, 16),
    IPhoneModel("iPhone SE (2nd gen)",   "A13",  13, None),
    IPhoneModel("iPhone SE (3rd gen)",   "A15",  15, None),

    # 5.4" mini
    IPhoneModel("iPhone 12 mini",        "A14",  14, None),
    IPhoneModel("iPhone 13 mini",        "A15",  15, None),

    # 5.8" (X-series form factor)
    IPhoneModel("iPhone X",              "A11",  11, 16),
    IPhoneModel("iPhone XS",             "A12",  12, None),
    IPhoneModel("iPhone 11 Pro",         "A13",  13, None),

    # 6.1" standard
    IPhoneModel("iPhone XR",             "A12",  12, None),
    IPhoneModel("iPhone 11",             "A13",  13, None),
    IPhoneModel("iPhone 12",             "A14",  14, None),
    IPhoneModel("iPhone 12 Pro",         "A14",  14, None),
    IPhoneModel("iPhone 13",             "A15",  15, None),
    IPhoneModel("iPhone 13 Pro",         "A15",  15, None),
    IPhoneModel("iPhone 14",             "A15",  15, None),
    IPhoneModel("iPhone 14 Pro",         "A16",  16, None),
    IPhoneModel("iPhone 15",             "A16",  16, None),
    IPhoneModel("iPhone 15 Pro",         "A17",  17, None),
    IPhoneModel("iPhone 16",             "A18",  18, None),
    IPhoneModel("iPhone 16e",            "A18",  18, None),
    IPhoneModel("iPhone 16 Pro",         "A18",  18, None),

    # 6.5" / 6.7" large
    IPhoneModel("iPhone XS Max",         "A12",  12, None),
    IPhoneModel("iPhone 11 Pro Max",     "A13",  13, None),
    IPhoneModel("iPhone 12 Pro Max",     "A14",  14, None),
    IPhoneModel("iPhone 13 Pro Max",     "A15",  15, None),
    IPhoneModel("iPhone 14 Plus",        "A15",  15, None),
    IPhoneModel("iPhone 14 Pro Max",     "A16",  16, None),
    IPhoneModel("iPhone 15 Plus",        "A16",  16, None),
    IPhoneModel("iPhone 15 Pro Max",     "A17",  17, None),
    IPhoneModel("iPhone 16 Plus",        "A18",  18, None),
    IPhoneModel("iPhone 16 Pro Max",     "A18",  18, None),

    # SE 1st gen (4" screen)
    IPhoneModel("iPhone SE (1st gen)",   "A9",   9,  15),
]

# ------------------------------------------------------------------
# Screen viewport mapping: (css_width, css_height, dpr) -> model names
# Values are CSS pixels in portrait orientation.
# ------------------------------------------------------------------

_SCREEN_TO_MODELS: dict[tuple[int, int, int], list[str]] = {
    # 4.0" — 320 x 568 @ 2x
    (320, 568, 2): [
        "iPhone SE (1st gen)",
    ],
    # 4.7" — 375 x 667 @ 2x
    (375, 667, 2): [
        "iPhone 6", "iPhone 6s", "iPhone 7", "iPhone 8",
        "iPhone SE (2nd gen)", "iPhone SE (3rd gen)",
    ],
    # 5.5" — 414 x 736 @ 3x
    (414, 736, 3): [
        "iPhone 6 Plus", "iPhone 6s Plus", "iPhone 7 Plus", "iPhone 8 Plus",
    ],
    # 5.8" — 375 x 812 @ 3x
    (375, 812, 3): [
        "iPhone X", "iPhone XS", "iPhone 11 Pro",
        "iPhone 12 mini", "iPhone 13 mini",
    ],
    # 6.1" (LCD) — 414 x 896 @ 2x
    (414, 896, 2): [
        "iPhone XR", "iPhone 11",
    ],
    # 6.5" — 414 x 896 @ 3x
    (414, 896, 3): [
        "iPhone XS Max", "iPhone 11 Pro Max",
    ],
    # 6.1" (2020-2022) — 390 x 844 @ 3x
    (390, 844, 3): [
        "iPhone 12", "iPhone 12 Pro",
        "iPhone 13", "iPhone 13 Pro",
        "iPhone 14",
    ],
    # 6.7" (2020-2022) — 428 x 926 @ 3x
    (428, 926, 3): [
        "iPhone 12 Pro Max", "iPhone 13 Pro Max", "iPhone 14 Plus",
    ],
    # 6.1" (2022+) — 393 x 852 @ 3x
    (393, 852, 3): [
        "iPhone 14 Pro",
        "iPhone 15", "iPhone 15 Pro",
        "iPhone 16", "iPhone 16e",
    ],
    # 6.7" (2022+) — 430 x 932 @ 3x
    (430, 932, 3): [
        "iPhone 14 Pro Max",
        "iPhone 15 Plus", "iPhone 15 Pro Max",
        "iPhone 16 Plus",
    ],
    # 6.3" (2024) — 402 x 874 @ 3x
    (402, 874, 3): [
        "iPhone 16 Pro",
    ],
    # 6.9" (2024) — 440 x 956 @ 3x
    (440, 956, 3): [
        "iPhone 16 Pro Max",
    ],
}

# Index models by name for quick chip/iOS lookups
_MODEL_BY_NAME: dict[str, IPhoneModel] = {m.name: m for m in ALL_IPHONES}


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def resolve_iphone(
    *,
    screen_width: int | None = None,
    screen_height: int | None = None,
    device_pixel_ratio: float | None = None,
    ios_version: int | None = None,
    gpu_chip: str | None = None,
) -> list[str]:
    """Narrow down iPhone model from observable browser signals.

    Returns a list of possible model names, ideally just one.
    An empty list means we couldn't match any known iPhone.

    Parameters
    ----------
    screen_width, screen_height : CSS viewport pixels (portrait).
    device_pixel_ratio : window.devicePixelRatio.
    ios_version : Major iOS version (e.g. 17 for iOS 17.2).
    gpu_chip : Apple GPU generation string, e.g. "A16", from canvas
               fingerprinting.
    """
    # Step 1: Start with screen dimensions
    candidates: list[str] | None = None
    if screen_width and screen_height and device_pixel_ratio:
        dpr = int(device_pixel_ratio)
        # Normalise to portrait (smaller dimension first)
        w, h = sorted([screen_width, screen_height])
        key = (w, h, dpr)
        candidates = list(_SCREEN_TO_MODELS.get(key, []))

    # If no screen match, start with all known models
    if candidates is None:
        candidates = [m.name for m in ALL_IPHONES]

    # Step 2: Filter by iOS version
    if ios_version is not None:
        candidates = [
            name for name in candidates
            if _model_supports_ios(name, ios_version)
        ]

    # Step 3: Filter by GPU chip (from canvas fingerprint)
    if gpu_chip:
        chip = gpu_chip.upper().replace("APPLE ", "").strip()
        candidates = [
            name for name in candidates
            if _MODEL_BY_NAME.get(name, None) is not None
            and _MODEL_BY_NAME[name].chip.upper() == chip
        ]

    return candidates


def _model_supports_ios(name: str, ios_version: int) -> bool:
    """Could this model plausibly be running the given iOS version?"""
    model = _MODEL_BY_NAME.get(name)
    if model is None:
        return False
    # The phone must have been released before or on this iOS version
    if model.min_ios > ios_version:
        return False
    # And the iOS version must not exceed the model's support ceiling
    if model.max_ios is not None and ios_version > model.max_ios:
        return False
    return True
