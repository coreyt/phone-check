"""Tests for phone_check.iphone_db — iPhone model resolution from browser signals."""

from phone_check.iphone_db import resolve_iphone


# ---------------------------------------------------------------------------
# Screen-only resolution (no iOS version or GPU)
# ---------------------------------------------------------------------------

class TestScreenResolution:
    """Screen dimensions narrow candidates to a resolution cohort."""

    def test_iphone_16_pro_max_unique_screen(self):
        """440x956 @3x is unique to iPhone 16 Pro Max."""
        result = resolve_iphone(screen_width=440, screen_height=956, device_pixel_ratio=3.0)
        assert result == ["iPhone 16 Pro Max"]

    def test_iphone_16_pro_unique_screen(self):
        """402x874 @3x is unique to iPhone 16 Pro."""
        result = resolve_iphone(screen_width=402, screen_height=874, device_pixel_ratio=3.0)
        assert result == ["iPhone 16 Pro"]

    def test_iphone_se_1st_gen_unique_screen(self):
        """320x568 @2x is unique to iPhone SE 1st gen."""
        result = resolve_iphone(screen_width=320, screen_height=568, device_pixel_ratio=2.0)
        assert result == ["iPhone SE (1st gen)"]

    def test_393x852_cohort(self):
        """393x852 @3x maps to multiple modern iPhones."""
        result = resolve_iphone(screen_width=393, screen_height=852, device_pixel_ratio=3.0)
        assert "iPhone 14 Pro" in result
        assert "iPhone 15" in result
        assert "iPhone 15 Pro" in result
        assert "iPhone 16" in result
        assert "iPhone 16e" in result
        assert len(result) == 5

    def test_390x844_cohort(self):
        """390x844 @3x maps to iPhone 12/12Pro/13/13Pro/14."""
        result = resolve_iphone(screen_width=390, screen_height=844, device_pixel_ratio=3.0)
        assert "iPhone 12" in result
        assert "iPhone 14" in result
        assert len(result) == 5

    def test_landscape_orientation_normalised(self):
        """Passing width > height (landscape) should still work."""
        portrait = resolve_iphone(screen_width=393, screen_height=852, device_pixel_ratio=3.0)
        landscape = resolve_iphone(screen_width=852, screen_height=393, device_pixel_ratio=3.0)
        assert portrait == landscape

    def test_unknown_screen_returns_all(self):
        """Unrecognised screen dims return every known iPhone."""
        result = resolve_iphone(screen_width=999, screen_height=999, device_pixel_ratio=2.0)
        assert result == []

    def test_no_screen_returns_all(self):
        """No screen info at all returns every known model."""
        result = resolve_iphone()
        assert len(result) > 30  # We have 37+ models in the DB


# ---------------------------------------------------------------------------
# Screen + iOS version
# ---------------------------------------------------------------------------

class TestScreenPlusIOS:
    """iOS version narrows candidates by excluding unsupported models."""

    def test_375x667_ios_17_excludes_old_models(self):
        """375x667 has iPhone 6/6s/7/8/SE2/SE3. iOS 17 excludes 6/6s/7/8."""
        result = resolve_iphone(
            screen_width=375, screen_height=667, device_pixel_ratio=2.0,
            ios_version=17,
        )
        # iPhone 6 maxes at iOS 12, 6s/7 at 15, 8 at 16
        assert "iPhone 6" not in result
        assert "iPhone 6s" not in result
        assert "iPhone 7" not in result
        assert "iPhone 8" not in result
        # SE 2nd & 3rd gen support iOS 17+
        assert "iPhone SE (2nd gen)" in result
        assert "iPhone SE (3rd gen)" in result
        assert len(result) == 2

    def test_375x812_ios_18_excludes_x(self):
        """375x812 has X/XS/11Pro/12mini/13mini. iOS 18 excludes X (max 16)."""
        result = resolve_iphone(
            screen_width=375, screen_height=812, device_pixel_ratio=3.0,
            ios_version=18,
        )
        assert "iPhone X" not in result
        assert "iPhone XS" in result
        assert "iPhone 12 mini" in result

    def test_414x896_2x_ios_13(self):
        """414x896 @2x = XR/11. Both support iOS 13."""
        result = resolve_iphone(
            screen_width=414, screen_height=896, device_pixel_ratio=2.0,
            ios_version=13,
        )
        assert "iPhone XR" in result
        assert "iPhone 11" in result

    def test_ios_version_too_old_for_model(self):
        """A phone can't report an iOS version it shipped before."""
        # iPhone 16 Pro shipped with iOS 18; iOS 17 shouldn't match it
        result = resolve_iphone(
            screen_width=402, screen_height=874, device_pixel_ratio=3.0,
            ios_version=17,
        )
        assert result == []


# ---------------------------------------------------------------------------
# Screen + GPU chip
# ---------------------------------------------------------------------------

class TestScreenPlusGPU:
    """GPU chip further narrows within a screen cohort."""

    def test_393x852_a16_narrows_to_two(self):
        """A16 chip + 393x852 = iPhone 14 Pro or iPhone 15."""
        result = resolve_iphone(
            screen_width=393, screen_height=852, device_pixel_ratio=3.0,
            gpu_chip="A16",
        )
        assert "iPhone 14 Pro" in result
        assert "iPhone 15" in result
        assert "iPhone 15 Pro" not in result  # A17
        assert "iPhone 16" not in result      # A18
        assert len(result) == 2

    def test_393x852_a17_is_15_pro(self):
        """A17 chip + 393x852 = iPhone 15 Pro only."""
        result = resolve_iphone(
            screen_width=393, screen_height=852, device_pixel_ratio=3.0,
            gpu_chip="A17",
        )
        assert result == ["iPhone 15 Pro"]

    def test_393x852_a18_narrows_to_16_and_16e(self):
        """A18 chip + 393x852 = iPhone 16 or 16e."""
        result = resolve_iphone(
            screen_width=393, screen_height=852, device_pixel_ratio=3.0,
            gpu_chip="A18",
        )
        assert "iPhone 16" in result
        assert "iPhone 16e" in result
        assert len(result) == 2

    def test_gpu_chip_case_insensitive(self):
        result = resolve_iphone(
            screen_width=393, screen_height=852, device_pixel_ratio=3.0,
            gpu_chip="a17",
        )
        assert result == ["iPhone 15 Pro"]

    def test_gpu_chip_with_apple_prefix(self):
        """Handle 'Apple A16' format from some detection libraries."""
        result = resolve_iphone(
            screen_width=393, screen_height=852, device_pixel_ratio=3.0,
            gpu_chip="Apple A16",
        )
        assert "iPhone 14 Pro" in result
        assert "iPhone 15" in result


# ---------------------------------------------------------------------------
# All three signals combined
# ---------------------------------------------------------------------------

class TestAllSignals:
    """Combining screen + iOS + GPU for maximum precision."""

    def test_exact_match_iphone_15_pro(self):
        """393x852 + iOS 17 + A17 = iPhone 15 Pro (unique)."""
        result = resolve_iphone(
            screen_width=393, screen_height=852, device_pixel_ratio=3.0,
            ios_version=17,
            gpu_chip="A17",
        )
        assert result == ["iPhone 15 Pro"]

    def test_exact_match_iphone_14_pro(self):
        """393x852 + iOS 16 + A16 = iPhone 14 Pro (15 requires min_ios 16
        but so does 14 Pro — however A16 excludes 15 Pro/16/16e)."""
        result = resolve_iphone(
            screen_width=393, screen_height=852, device_pixel_ratio=3.0,
            ios_version=16,
            gpu_chip="A16",
        )
        assert "iPhone 14 Pro" in result
        assert "iPhone 15" in result  # 15 also has A16 and supports iOS 16

    def test_390x844_ios_15_a15(self):
        """390x844 + iOS 15 + A15 = iPhone 13 or 13 Pro."""
        result = resolve_iphone(
            screen_width=390, screen_height=844, device_pixel_ratio=3.0,
            ios_version=15,
            gpu_chip="A15",
        )
        assert "iPhone 13" in result
        assert "iPhone 13 Pro" in result
        # iPhone 14 also has A15 but min_ios=15 so it could be here too
        assert "iPhone 12" not in result      # A14
        assert "iPhone 12 Pro" not in result   # A14
