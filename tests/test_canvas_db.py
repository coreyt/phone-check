"""Tests for phone_check.canvas_db — hash storage and lookup."""

import json

import pytest

from phone_check import canvas_db


@pytest.fixture(autouse=True)
def _reset_cache(tmp_path, monkeypatch):
    """Isolate each test with fresh files and cleared cache."""
    data_file = tmp_path / "canvas_hashes.json"
    data_file.write_text(json.dumps({
        "version": 1,
        "canvas_version": "v1",
        "hashes": {"abc123": "A16"},
    }))
    runtime_file = tmp_path / "runtime.json"

    monkeypatch.setattr(canvas_db, "_DATA_FILE", data_file)
    monkeypatch.setattr(canvas_db, "_RUNTIME_FILE", runtime_file)
    monkeypatch.setattr(canvas_db, "_cache", None)


class TestLoadHashes:
    def test_loads_from_file(self):
        result = canvas_db.load_hashes()
        assert result == {"abc123": "A16"}

    def test_caches_after_first_load(self):
        first = canvas_db.load_hashes()
        second = canvas_db.load_hashes()
        assert first is second


class TestLookupChip:
    def test_known_hash(self):
        assert canvas_db.lookup_chip("abc123") == "A16"

    def test_unknown_hash(self):
        assert canvas_db.lookup_chip("unknown") is None


class TestRecordObservation:
    def test_records_new_observation(self):
        canvas_db.record_observation("def456", "A15")
        runtime = canvas_db.get_runtime_observations()
        assert runtime["def456"] == "A15"

    def test_skips_known_hash(self):
        canvas_db.record_observation("abc123", "A16")
        runtime = canvas_db.get_runtime_observations()
        assert "abc123" not in runtime

    def test_skips_duplicate_runtime(self):
        canvas_db.record_observation("def456", "A15")
        canvas_db.record_observation("def456", "A14")  # should not overwrite
        runtime = canvas_db.get_runtime_observations()
        assert runtime["def456"] == "A15"


class TestGetRuntimeObservations:
    def test_empty_when_no_file(self):
        assert canvas_db.get_runtime_observations() == {}

    def test_returns_recorded_data(self):
        canvas_db.record_observation("xyz789", "A17")
        result = canvas_db.get_runtime_observations()
        assert result == {"xyz789": "A17"}
