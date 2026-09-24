# Third-party notices

This repository contains integration code, not model weights. Setup scripts download
the listed files into ignored `vendor/` directories and verify pinned hashes.
Only Hub snapshot files identified by immutable revisions are pinned there; the
face-parser Google Drive artifact and the ResNet-18 artifact do not yet have
complete provenance/license receipts tied to their exact hashes. These notices
are a starting inventory, not legal advice or a complete license audit of every
transitive package; inspect the lock files and upstream terms before
redistribution.

- **MuseTalk** — [source and MIT license](https://github.com/TMElyralab/MuseTalk), reviewed at commit `0a89dec45a0192b824e3cf4daf96c239440c5ed8`. The model-loading modules under `patches/musetalk_missing_models/` are adapted from upstream MuseTalk; the corresponding MIT notice is included at `THIRD_PARTY_LICENSES/MuseTalk-MIT.txt`. The setup script pins the MuseTalk model snapshot and verifies its UNet SHA-256.
- **musetalk-mac** — [source and MIT license](https://github.com/barnent1/musetalk-mac), pinned at commit `7fd019315127d7f31e2e7f9853547ddceabbeb6e` and patched locally for a conservative batch size and localhost-only binding. Its MIT notice is included at `THIRD_PARTY_LICENSES/musetalk-mac-MIT.txt`.
- **MLX-Audio** — [source and MIT license](https://github.com/Blaizzy/mlx-audio), package version `0.5.4`.
- **Qwen3-TTS 0.6B CustomVoice 8-bit** — [model card](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit), Apache-2.0, pinned at revision `049ef77fe8816b536193c0c25f9a214d17921282`.
- **LivePortrait** — [source and license](https://github.com/KlingAIResearch/LivePortrait), code pinned at commit `9b294b3d0536135442ea73cb01e6cb3ca7029dd3`. Its [Hub snapshot](https://huggingface.co/KwaiVGI/LivePortrait/tree/82a4fa6735ca58432b6ce39301b4b9ee066dea47) is pinned and checksummed, but the included InsightFace detector models are for non-commercial research only. The installer requires an explicit `--noncommercial-research` argument. This integration is not cleared for commercial use until a detector with suitable commercial rights replaces them.
- **SD-VAE** — [model card](https://huggingface.co/stabilityai/sd-vae-ft-mse), MIT, with a pinned Hub snapshot and verified SHA-256.
- **Whisper-tiny** — [model repository](https://huggingface.co/openai/whisper-tiny) and [official project license](https://github.com/openai/whisper/blob/main/LICENSE); pinned Hub snapshot and verified SHA-256.
- **Face parsing checkpoint** — downloaded using the Google Drive file ID in the pinned Mac-port setup, SHA-256 `468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567`. The exact file-to-model-card provenance and license have not been verified; do not claim commercial clearance or redistribute this checkpoint until resolved.
- **ResNet-18 checkpoint** — downloaded from the PyTorch model URL `https://download.pytorch.org/models/resnet18-5c106cde.pth`, SHA-256 `5c106cde386e87d4033832f2996f5493238eda96ccf559d1d62760c4de0613f8`. The model artifact's full provenance/terms have not been reviewed for this release; do not treat the hash as a license grant.
- **Optional OpenAI Images API** — [image generation documentation](https://developers.openai.com/api/docs/guides/image-generation). Avatar generation sends the prompt to OpenAI; this project does not bundle or locally run that model.

All weights and transitive dependencies retain their own terms. They are not
included in this repository and must not be mirrored or bundled without checking
their licenses. Hashes establish byte integrity only. Check `models/*.sha256`
and `models/README.md` for artifact revisions and hashes. The paid product's
proprietary buyer license covers only the project source and skill. The
face-parser and ResNet-18 artifact clearances, LivePortrait detector
restriction, and complete transitive dependency review remain
commercial-release blockers.
