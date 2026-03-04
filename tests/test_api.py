"""Tests for the FastAPI endpoints."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from phone_check import canvas_db
from phone_check.api import app


UA_PIXEL_8 = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

UA_SAMSUNG_S22 = (
    "Mozilla/5.0 (Linux; Android 12; SM-S901B) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

UA_IPHONE_18 = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/18.0 Mobile/15E148 Safari/604.1"
)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_post_identify_pixel(client):
    resp = await client.post("/api/identify", json={"user_agent": UA_PIXEL_8})
    assert resp.status_code == 200
    data = resp.json()
    assert data["brand"] == "Google"
    assert "Pixel 8" in data["model"]
    assert data["confidence"] == "high"
    assert data["identified"] is True
    assert "possible_models" in data


@pytest.mark.anyio
async def test_post_identify_samsung(client):
    resp = await client.post("/api/identify", json={"user_agent": UA_SAMSUNG_S22})
    assert resp.status_code == 200
    data = resp.json()
    assert data["brand"] == "Samsung"
    assert data["identified"] is True


@pytest.mark.anyio
async def test_post_identify_with_client_hints(client):
    resp = await client.post("/api/identify", json={
        "user_agent": UA_SAMSUNG_S22,
        "client_hint_model": "Galaxy S22 Ultra",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "Galaxy S22 Ultra"


@pytest.mark.anyio
async def test_post_identify_iphone_with_screen(client):
    """iPhone + screen dimensions should resolve to specific model(s)."""
    resp = await client.post("/api/identify", json={
        "user_agent": UA_IPHONE_18,
        "screen_width": 402,
        "screen_height": 874,
        "device_pixel_ratio": 3.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["brand"] == "Apple"
    assert data["model"] == "iPhone 16 Pro"
    assert data["confidence"] == "high"
    assert data["possible_models"] == ["iPhone 16 Pro"]


@pytest.mark.anyio
async def test_post_identify_iphone_with_gpu(client):
    """iPhone + screen + GPU chip should narrow further."""
    resp = await client.post("/api/identify", json={
        "user_agent": UA_IPHONE_18,
        "screen_width": 393,
        "screen_height": 852,
        "device_pixel_ratio": 3.0,
        "gpu_chip": "A18",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["brand"] == "Apple"
    assert set(data["possible_models"]) == {"iPhone 16", "iPhone 16e"}


@pytest.mark.anyio
async def test_get_identify_uses_request_ua(client):
    resp = await client.get(
        "/api/identify",
        headers={"User-Agent": UA_PIXEL_8},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["brand"] == "Google"
    assert "Pixel 8" in data["model"]


@pytest.mark.anyio
async def test_get_identify_reads_client_hint_header(client):
    resp = await client.get(
        "/api/identify",
        headers={
            "User-Agent": UA_SAMSUNG_S22,
            "Sec-CH-UA-Model": '"Galaxy S22 Ultra"',
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "Galaxy S22 Ultra"


@pytest.mark.anyio
async def test_post_identify_iphone_with_canvas_hash(client, tmp_path, monkeypatch):
    """Canvas hash should be accepted in the request body."""
    # Set up a known canvas hash mapping
    data_file = tmp_path / "canvas_hashes.json"
    data_file.write_text(json.dumps({
        "version": 1, "canvas_version": "v1",
        "hashes": {"deadbeef": "A18"},
    }))
    monkeypatch.setattr(canvas_db, "_DATA_FILE", data_file)
    monkeypatch.setattr(canvas_db, "_cache", None)

    resp = await client.post("/api/identify", json={
        "user_agent": UA_IPHONE_18,
        "screen_width": 393,
        "screen_height": 852,
        "device_pixel_ratio": 3.0,
        "canvas_hash": "deadbeef",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["brand"] == "Apple"
    # Canvas hash resolved to A18, which narrows candidates
    assert set(data["possible_models"]) == {"iPhone 16", "iPhone 16e"}


@pytest.mark.anyio
async def test_passive_calibration_records_observation(client, tmp_path, monkeypatch):
    """When both gpu_chip and canvas_hash are present, record the mapping."""
    data_file = tmp_path / "canvas_hashes.json"
    data_file.write_text(json.dumps({
        "version": 1, "canvas_version": "v1", "hashes": {},
    }))
    runtime_file = tmp_path / "runtime.json"
    monkeypatch.setattr(canvas_db, "_DATA_FILE", data_file)
    monkeypatch.setattr(canvas_db, "_RUNTIME_FILE", runtime_file)
    monkeypatch.setattr(canvas_db, "_cache", None)

    resp = await client.post("/api/identify", json={
        "user_agent": UA_IPHONE_18,
        "screen_width": 393,
        "screen_height": 852,
        "device_pixel_ratio": 3.0,
        "gpu_chip": "A18",
        "canvas_hash": "cafe1234",
    })
    assert resp.status_code == 200

    runtime = json.loads(runtime_file.read_text())
    assert runtime["cafe1234"] == "A18"


@pytest.mark.anyio
async def test_probe_endpoint(client):
    resp = await client.get("/probe")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Canvas Probe" in resp.text


@pytest.mark.anyio
async def test_calibration_endpoint(client, tmp_path, monkeypatch):
    data_file = tmp_path / "canvas_hashes.json"
    data_file.write_text(json.dumps({
        "version": 1, "canvas_version": "v1",
        "hashes": {"abc": "A16"},
    }))
    monkeypatch.setattr(canvas_db, "_DATA_FILE", data_file)
    monkeypatch.setattr(canvas_db, "_RUNTIME_FILE", tmp_path / "runtime.json")
    monkeypatch.setattr(canvas_db, "_cache", None)

    resp = await client.get("/api/calibration")
    assert resp.status_code == 200
    data = resp.json()
    assert data["authoritative_count"] == 1
    assert data["authoritative"]["abc"] == "A16"
    assert data["runtime_count"] == 0


@pytest.mark.anyio
async def test_index_returns_html(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Phone Check" in resp.text
