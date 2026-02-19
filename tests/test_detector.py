"""Tests for phone_check.detector — verifies we resolve specific phone *models*."""

import pytest

from phone_check.detector import DeviceInfo, detect, detect_from_ua


# ---------------------------------------------------------------------------
# Real-world User-Agent strings
# ---------------------------------------------------------------------------

UA_SAMSUNG_S22 = (
    "Mozilla/5.0 (Linux; Android 12; SM-S901B) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

UA_PIXEL_8 = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

UA_PIXEL_7A = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 7a) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

UA_SAMSUNG_A54 = (
    "Mozilla/5.0 (Linux; Android 14; SM-A546B) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

UA_ONEPLUS_12 = (
    "Mozilla/5.0 (Linux; Android 14; CPH2583) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

UA_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)

UA_GENERIC_ANDROID = (
    "Mozilla/5.0 (Linux; Android 13) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

UA_DESKTOP = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Phase 1 (server-side): detect_from_ua
# ---------------------------------------------------------------------------

class TestDetectFromUA:
    """detect_from_ua should resolve specific phone models from UA strings."""

    def test_samsung_galaxy_s22(self):
        info = detect_from_ua(UA_SAMSUNG_S22)
        assert info.brand == "Samsung"
        assert "S22" in info.model or "Galaxy" in info.model
        assert info.os_name == "Android"
        assert info.confidence == "high"
        assert info.identified is True

    def test_pixel_8(self):
        info = detect_from_ua(UA_PIXEL_8)
        assert info.brand == "Google"
        assert "Pixel 8" in info.model
        assert info.confidence == "high"
        assert info.identified is True

    def test_pixel_7a(self):
        info = detect_from_ua(UA_PIXEL_7A)
        assert info.brand == "Google"
        assert "Pixel" in info.model
        assert info.identified is True

    def test_samsung_a54(self):
        info = detect_from_ua(UA_SAMSUNG_A54)
        assert info.brand == "Samsung"
        assert info.model  # should resolve to a specific model
        assert info.confidence == "high"
        assert info.identified is True

    def test_iphone_only_gets_generic(self):
        """Apple strips model info from the UA — we can only say 'iPhone'."""
        info = detect_from_ua(UA_IPHONE)
        assert info.brand == "Apple"
        assert info.model == "iPhone"
        assert info.confidence == "low"
        assert info.identified is False

    def test_generic_android_unidentified(self):
        info = detect_from_ua(UA_GENERIC_ANDROID)
        assert info.brand == ""
        assert info.model == ""
        assert info.confidence == "none"
        assert info.identified is False

    def test_empty_ua(self):
        info = detect_from_ua("")
        assert info.confidence == "none"
        assert info.identified is False


# ---------------------------------------------------------------------------
# Full waterfall: detect() with Client Hints
# ---------------------------------------------------------------------------

class TestDetectWithClientHints:
    """Client Hints should override/supplement UA-based detection."""

    def test_client_hint_overrides_ua(self):
        """When the browser sends a model via Client Hints, prefer it."""
        info = detect(UA_GENERIC_ANDROID, client_hint_model="Pixel 8 Pro")
        assert info.model == "Pixel 8 Pro"
        assert info.confidence in ("high", "medium")

    def test_client_hint_brand_and_model(self):
        info = detect(
            UA_GENERIC_ANDROID,
            client_hint_model="Galaxy S24 Ultra",
            client_hint_brand="Samsung",
        )
        assert info.brand == "Samsung"
        assert info.model == "Galaxy S24 Ultra"
        assert info.identified is True

    def test_client_hint_model_alone_keeps_ua_brand(self):
        """If only the model hint is sent, brand falls back to UA detection."""
        info = detect(UA_SAMSUNG_S22, client_hint_model="Galaxy S22 Ultra")
        assert info.brand == "Samsung"  # from UA
        assert info.model == "Galaxy S22 Ultra"  # from CH
        assert info.confidence == "high"

    def test_no_hints_falls_through(self):
        """Without hints, detect() behaves the same as detect_from_ua()."""
        info = detect(UA_PIXEL_8)
        expected = detect_from_ua(UA_PIXEL_8)
        assert info == expected


# ---------------------------------------------------------------------------
# DeviceInfo dataclass
# ---------------------------------------------------------------------------

class TestDeviceInfo:
    def test_identified_true_for_high(self):
        info = DeviceInfo("Samsung", "Galaxy S22", "Android", "12", "smartphone", "high")
        assert info.identified is True

    def test_identified_true_for_medium(self):
        info = DeviceInfo("Samsung", "SM-X", "Android", "12", "smartphone", "medium")
        assert info.identified is True

    def test_identified_false_for_low(self):
        info = DeviceInfo("Apple", "iPhone", "iOS", "17", "smartphone", "low")
        assert info.identified is False

    def test_identified_false_for_none(self):
        info = DeviceInfo("", "", "", "", "smartphone", "none")
        assert info.identified is False

    def test_frozen(self):
        info = DeviceInfo("Samsung", "Galaxy S22", "Android", "12", "smartphone", "high")
        with pytest.raises(AttributeError):
            info.brand = "Apple"
