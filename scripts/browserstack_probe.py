#!/usr/bin/env python3
"""BrowserStack calibration script for canvas hash → GPU chip mapping.

Launches Safari on real iPhone devices via BrowserStack, navigates to the
/probe page, and reads the canvas fingerprint results.  Maps each hash to
the known GPU chip for that device (from iphone_db) and merges new entries
into the authoritative canvas_hashes.json file.

Usage:
    export BROWSERSTACK_USERNAME=...
    export BROWSERSTACK_ACCESS_KEY=...
    python scripts/browserstack_probe.py --url https://your-app.onrender.com

    # Preview without writing:
    python scripts/browserstack_probe.py --url https://your-app.onrender.com --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Add project root to path so we can import iphone_db
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# BrowserStack device configs: (device_name, os_version, chip)
# Device names must match BrowserStack's real device inventory.
DEVICE_CONFIGS = [
    ("iPhone 16 Pro Max", "18", "A18"),
    ("iPhone 16 Pro", "18", "A18"),
    ("iPhone 16", "18", "A18"),
    ("iPhone 15 Pro Max", "17", "A17"),
    ("iPhone 15 Pro", "17", "A17"),
    ("iPhone 15", "17", "A16"),
    ("iPhone 14 Pro Max", "16", "A16"),
    ("iPhone 14 Pro", "16", "A16"),
    ("iPhone 14", "16", "A15"),
    ("iPhone 13 Pro Max", "15", "A15"),
    ("iPhone 13 Pro", "15", "A15"),
    ("iPhone 13", "15", "A15"),
    ("iPhone 12 Pro Max", "15", "A14"),
    ("iPhone 12 Pro", "15", "A14"),
    ("iPhone 12", "15", "A14"),
    ("iPhone 11 Pro Max", "15", "A13"),
    ("iPhone 11 Pro", "15", "A13"),
    ("iPhone 11", "15", "A13"),
    ("iPhone XS Max", "15", "A12"),
    ("iPhone XS", "15", "A12"),
    ("iPhone XR", "15", "A12"),
    ("iPhone SE 2022", "16", "A15"),
    ("iPhone SE 2020", "15", "A13"),
]

DATA_FILE = PROJECT_ROOT / "phone_check" / "data" / "canvas_hashes.json"


def probe_device(
    url: str,
    device_name: str,
    os_version: str,
    username: str,
    access_key: str,
) -> dict | None:
    """Open the probe page on a BrowserStack device, return results JSON."""
    options = webdriver.ChromeOptions()
    bstack_options = {
        "osVersion": os_version,
        "deviceName": device_name,
        "realMobile": "true",
        "userName": username,
        "accessKey": access_key,
        "browserName": "safari",
    }
    options.set_capability("bstack:options", bstack_options)

    driver = None
    try:
        driver = webdriver.Remote(
            command_executor="https://hub-cloud.browserstack.com/wd/hub",
            options=options,
        )
        driver.get(f"{url.rstrip('/')}/probe")

        # Wait for results to appear (the probe auto-runs on load)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "results"))
        )
        # Give it a moment to finish rendering
        time.sleep(2)

        results_text = driver.find_element(By.ID, "results").text
        if results_text and results_text != "Running...":
            return json.loads(results_text)
        return None
    except Exception as e:
        print(f"  Error probing {device_name}: {e}", file=sys.stderr)
        return None
    finally:
        if driver:
            driver.quit()


def load_data_file() -> dict:
    """Load the authoritative canvas hashes JSON."""
    try:
        return json.loads(DATA_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"version": 1, "canvas_version": "v1", "hashes": {}}


def save_data_file(data: dict) -> None:
    """Write the authoritative canvas hashes JSON."""
    DATA_FILE.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe iPhones on BrowserStack for canvas hash calibration"
    )
    parser.add_argument("--url", required=True, help="Base URL of the deployed app")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print results without writing to file"
    )
    args = parser.parse_args()

    username = os.environ.get("BROWSERSTACK_USERNAME")
    access_key = os.environ.get("BROWSERSTACK_ACCESS_KEY")
    if not username or not access_key:
        print(
            "Error: Set BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY env vars",
            file=sys.stderr,
        )
        sys.exit(1)

    data = load_data_file()
    hashes = data["hashes"]
    new_count = 0

    for device_name, os_version, chip in DEVICE_CONFIGS:
        print(f"Probing {device_name} (iOS {os_version})...")
        result = probe_device(args.url, device_name, os_version, username, access_key)

        if not result:
            print(f"  No result for {device_name}")
            continue

        canvas_hash = result.get("canvas_hash")
        if not canvas_hash:
            print(f"  No canvas hash from {device_name}")
            continue

        if canvas_hash in hashes:
            print(f"  Hash {canvas_hash} already mapped to {hashes[canvas_hash]}")
        else:
            print(f"  New hash {canvas_hash} -> {chip}")
            hashes[canvas_hash] = chip
            new_count += 1

    if new_count == 0:
        print("\nNo new hashes discovered.")
        return

    if args.dry_run:
        print(f"\nDry run: would add {new_count} new hash(es):")
        print(json.dumps(data, indent=2))
    else:
        save_data_file(data)
        print(f"\nWrote {new_count} new hash(es) to {DATA_FILE}")


if __name__ == "__main__":
    main()
