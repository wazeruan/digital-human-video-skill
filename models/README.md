# Model downloads and integrity

No model weights are included in this repository. The setup scripts download
only the files this pipeline uses, pin Hugging Face snapshots to immutable
revisions, and verify each listed file against the SHA-256 manifests here.
The hashes were checked against the downloaded files on 2026-09-22; a failed
verification stops installation before inference. Setup also checks that each
model directory contains exactly the manifest-listed files (apart from the
Hugging Face local metadata cache), refusing stale or unexpected weights. A
matching hash proves byte integrity, not source provenance, license, or
commercial-use rights.

- `musetalk.sha256`: MuseTalk 1.5, SD-VAE, Whisper-tiny, face parser, and
  ResNet-18 dependencies used by the pinned macOS sidecar. The Hub revisions
  and external download locations are declared in `scripts/setup_musetalk_mac.sh`.
  The face-parser artifact's exact model-card provenance/license and the
  ResNet-18 artifact's release terms are unresolved; commercial use is blocked.
- `liveportrait.sha256`: human LivePortrait checkpoints and the two InsightFace
  detection models from Hub revision
  `82a4fa6735ca58432b6ce39301b4b9ee066dea47`.

The LivePortrait installer requires an explicit `--noncommercial-research`
acknowledgement because its InsightFace detection weights are restricted to
non-commercial research. This pipeline does not provide a replacement detector
or commercial clearance for that route. Do not use those weights in a paid
deployment.

These manifests cover model files only, not the Python dependencies in each
sidecar environment. The setup scripts still need a separately pinned,
hash-verified dependency lock before claiming bit-for-bit reproducibility.
Never commit downloaded weights.
