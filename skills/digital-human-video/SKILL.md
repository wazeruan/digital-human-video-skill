---
name: digital-human-video
description: Build short Chinese digital-human videos with local TTS, avatar motion, and an optional FastAPI service. Use when setting up, running, or improving this project's Apple-Silicon pipeline; not for general video editing.
---

# Digital Human Video

Use the repository's pipeline to turn an authorized portrait and a short Chinese line into an MP4. Favor a cached avatar motion loop for repeated short lines; use audio-driven lip sync only when that exact mode is requested and the avatar/model combination has been visually checked.

## Workflow

1. Locate the project root and read its README, .env.example, and third-party notices before running setup. Confirm Apple Silicon/macOS before suggesting MLX or MPS commands.
2. Keep the actual face image, voice recordings, generated videos, downloaded model weights, API keys, and .env local. Never commit or upload them. This is a one-user local preview: keep the unauthenticated FastAPI service and MuseTalk sidecar on 127.0.0.1; do not expose them through a proxy, tunnel, or public bind.
3. Use an image-generation tool only when a new avatar or image edit is requested. Preserve supplied identity traits, ask before sending a private reference to an external service, and keep a generated face edit non-destructive.
4. Generate or upload the avatar once, select a motion mode explicitly, and cache preprocessing by avatar and model settings. For local Chinese voice, use the configured Qwen3-TTS MLX backend. The current input limit is 20 grapheme clusters, including punctuation.
5. Choose loop mode when timing does not need to match audio. It reuses a pre-generated LivePortrait clip and does not animate from the speech waveform. Choose musetalk mode only when approximate audio-driven mouth motion is requested; verify the particular face style because cartoon mouths can deform.
6. Run the fake demo before installing model weights. For a real render, follow the project's pinned setup scripts and checksum manifests; keep MuseTalk and LivePortrait in separate environments. Run one render at a time on a 24GB Mac. Only install LivePortrait with `--noncommercial-research` when the use is genuinely non-commercial; this project has no commercially cleared replacement detector.
7. Inspect the exported MP4 for face identity, mouth shape, eye direction, loop seam, audio, duration, and resolution. Say exactly what the chosen mode synchronizes; do not imply word-level lip sync for a loop.
8. When changing code, preserve user data and unrelated edits. Run the documented checks and report what was exercised on actual hardware versus only simulated.

## Release and commercial checks

Before packaging, inspect the current third-party notices and model terms. The public repository must not ship local face/avatar media or model weights. LivePortrait's own license flags InsightFace detection models as non-commercial research only; commercial users must replace them with a commercially licensed detector or obtain permission. Never describe the bundled LivePortrait setup as commercially cleared until that dependency is resolved.

The proprietary purchaser license at `BUYER-LICENSE.txt` allows only the purchasing customer to use and privately modify the project and skill; it prohibits sharing, resale, and redistribution. It does not grant rights to models, third-party code, inputs, identities, voices, or generated outputs. Include it in every paid skill package, and do not present the product as commercially cleared until the third-party asset and dependency blockers are resolved.
