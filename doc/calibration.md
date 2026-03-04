# Canvas Hash Calibration System

## Why canvas hashing is needed

Starting with iOS 12.2, Safari returns the generic string `"Apple GPU"` from the `WEBGL_debug_renderer_info` extension instead of the specific chip name (e.g. `"Apple A16 GPU"`). This means we can't directly identify the GPU generation on modern iPhones via WebGL.

However, different Apple GPU generations render anti-aliased graphics with subtly different sub-pixel patterns. By drawing a deterministic canvas scene and hashing the pixel output, we get a fingerprint that's unique to each GPU generation. This hash can then be mapped back to a chip name (e.g. `"A16"`) to narrow down the iPhone model.

## How canvas hashing works

1. A 67x67 canvas draws a fixed scene: diagonal lines, circles, a bezier curve, and text
2. The rendered pixels are exported via `canvas.toDataURL()`
3. An FNV-1a hash of the data URL produces a compact hex string
4. The server looks up this hash in the calibration database to find the GPU chip

**Hash stability warning:** Changing the canvas drawing code (dimensions, shapes, colors, text) will invalidate all existing hashes. The `canvas_version` field in `canvas_hashes.json` tracks this — bump it if you change the drawing.

## Architecture

```
Browser (iPhone)                    Server
┌─────────────────┐                ┌─────────────────────────┐
│ Draw canvas      │   POST        │                         │
│ Hash pixels      │──────────────>│ detect()                │
│ Send canvas_hash │   /identify   │   ├─ gpu_chip? use it   │
│ + gpu_chip?      │               │   └─ canvas_hash?       │
└─────────────────┘                │       └─ lookup_chip()  │
                                   │           ├─ found: use  │
                                   │           └─ not found   │
                                   │                         │
                                   │ Passive calibration:    │
                                   │ if gpu_chip AND hash:   │
                                   │   record_observation()  │
                                   └─────────────────────────┘
```

## Calibration database

### Authoritative file: `phone_check/data/canvas_hashes.json`

```json
{
  "version": 1,
  "canvas_version": "v1",
  "hashes": {
    "a1b2c3d4": "A16",
    "e5f6a7b8": "A17"
  }
}
```

This file is checked into the repo and deployed with the app. It's the source of truth for hash→chip lookups.

### Runtime observations: `/tmp/canvas_hashes_runtime.json`

When a device sends both a `gpu_chip` (from WebGL on older iOS) and a `canvas_hash`, the server records the mapping in this temp file. On Render's free tier, this file is ephemeral — it resets on each deploy.

## Passive calibration

Passive calibration happens automatically when:
1. A device visits the app and sends both `gpu_chip` and `canvas_hash`
2. The `gpu_chip` was obtained via WebGL (older iOS or non-Apple browsers)
3. The `canvas_hash` is not already in the authoritative file

This is most useful for devices running iOS versions before 12.2, which still expose the GPU chip via WebGL.

## BrowserStack probe (active calibration)

For systematic calibration across iPhone models:

### Setup

```bash
pip install -r scripts/requirements.txt
export BROWSERSTACK_USERNAME=your_username
export BROWSERSTACK_ACCESS_KEY=your_key
```

### Running

```bash
# Preview what would be recorded
python scripts/browserstack_probe.py --url https://your-app.onrender.com --dry-run

# Run and write results
python scripts/browserstack_probe.py --url https://your-app.onrender.com
```

The script:
1. Opens Safari on each iPhone device in BrowserStack's real device cloud
2. Navigates to `/probe` which auto-runs the canvas fingerprint
3. Reads the results from the page
4. Maps each hash to the known GPU chip for that device
5. Merges new entries into `phone_check/data/canvas_hashes.json`

### Committing results

After running the probe:
```bash
git add phone_check/data/canvas_hashes.json
git commit -m "Add canvas hash calibration data from BrowserStack"
git push
```

## Diagnostics

### `/api/calibration` endpoint

Returns the current state of both the authoritative and runtime hash databases:

```json
{
  "authoritative_count": 5,
  "authoritative": {"a1b2c3d4": "A16", ...},
  "runtime_count": 2,
  "runtime": {"x9y8z7w6": "A15", ...}
}
```

### Merging runtime observations

If runtime observations accumulate (e.g. from passive calibration), you can merge them into the authoritative file:

1. Visit `/api/calibration` to see runtime observations
2. Verify the mappings look correct
3. Manually add confirmed entries to `phone_check/data/canvas_hashes.json`
4. Commit and deploy
