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

UA_IPHONE_17 = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)

UA_IPHONE_18 = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/18.0 Mobile/15E148 Safari/604.1"
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
        """Apple strips model info — detect_from_ua can only say 'iPhone'."""
        info = detect_from_ua(UA_IPHONE_17)
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
# Full waterfall: detect() with Client Hints (Android path)
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
        """Without hints, detect() behaves the same as detect_from_ua() for Android."""
        info = detect(UA_PIXEL_8)
        expected = detect_from_ua(UA_PIXEL_8)
        assert info == expected


# ---------------------------------------------------------------------------
# Full waterfall: detect() with screen signals (iOS path)
# ---------------------------------------------------------------------------

class TestDetectIPhoneResolution:
    """detect() should resolve iPhone models using screen + iOS + GPU."""

    def test_iphone_16_pro_max_unique(self):
        """440x956 @3x is unique — resolves to iPhone 16 Pro Max."""
        info = detect(
            UA_IPHONE_18,
            screen_width=440, screen_height=956, device_pixel_ratio=3.0,
        )
        assert info.brand == "Apple"
        assert info.model == "iPhone 16 Pro Max"
        assert info.confidence == "high"
        assert info.identified is True
        assert info.possible_models == ("iPhone 16 Pro Max",)

    def test_iphone_16_pro_unique(self):
        """402x874 @3x is unique — resolves to iPhone 16 Pro."""
        info = detect(
            UA_IPHONE_18,
            screen_width=402, screen_height=874, device_pixel_ratio=3.0,
        )
        assert info.model == "iPhone 16 Pro"
        assert info.confidence == "high"

    def test_iphone_393x852_narrows_with_gpu(self):
        """393x852 + A17 chip = iPhone 15 Pro."""
        info = detect(
            UA_IPHONE_17,
            screen_width=393, screen_height=852, device_pixel_ratio=3.0,
            gpu_chip="A17",
        )
        assert info.model == "iPhone 15 Pro"
        assert info.confidence == "high"
        assert info.possible_models == ("iPhone 15 Pro",)

    def test_iphone_393x852_medium_confidence_without_gpu(self):
        """393x852 without GPU → multiple candidates, medium confidence."""
        info = detect(
            UA_IPHONE_18,
            screen_width=393, screen_height=852, device_pixel_ratio=3.0,
        )
        assert info.brand == "Apple"
        assert info.confidence == "medium"
        assert len(info.possible_models) > 1
        assert info.identified is True  # medium still counts as identified

    def test_iphone_no_screen_data_falls_back(self):
        """Without screen data, iPhone falls back to medium with many candidates."""
        info = detect(UA_IPHONE_17)
        assert info.brand == "Apple"
        # Should still attempt resolution using iOS version alone
        assert info.confidence == "medium"
        assert len(info.possible_models) > 5

    def test_iphone_screen_375x667_ios17(self):
        """375x667 + iOS 17 = SE 2nd or 3rd gen only."""
        info = detect(
            UA_IPHONE_17,
            screen_width=375, screen_height=667, device_pixel_ratio=2.0,
        )
        assert info.brand == "Apple"
        possible = info.possible_models
        assert "iPhone SE (2nd gen)" in possible
        assert "iPhone SE (3rd gen)" in possible
        assert "iPhone 6" not in possible  # max iOS 12
        assert "iPhone 8" not in possible  # max iOS 16
        assert len(possible) == 2


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

    def test_possible_models_default_empty(self):
        info = DeviceInfo("Samsung", "Galaxy S22", "Android", "12", "smartphone", "high")
        assert info.possible_models == ()
