# Release status and checklist

## Current status

This checkout is a locally tested MVP source candidate, not a fully validated
real-model release or commercially cleared product. The root `LICENSE` and
skill buyer-license draft identify `wazeruan`; the buyer terms allow private
modification and prohibit sharing, resale, and redistribution. The terms still
need legal review before sale. A public source preview must use a sanitized,
fresh-history snapshot; the original local history stays untouched.

A development checkout used to prepare publication may contain generated or
personal avatar assets in its current tree or older commits. Removing images
from the latest tree is not enough: a public push could still publish prior
versions. Publish only from a clean-history snapshot that excludes all local
face/avatar images and media. The release audit rejects image and model/media
assets in both the current tree and reachable history.

## Before making a public GitHub repository

1. Keep the project-specific proprietary notice and the separate purchaser
   terms at `skills/digital-human-video/BUYER-LICENSE.txt` with the paid skill.
   A public repository does not grant non-buyers rights to use, modify, or resell
   the software or skill.
2. Create a clean publication snapshot/history containing only reviewed files.
   Keep the existing local history intact; do not force-push or rewrite it as a
   shortcut. Exclude all local face/avatar images, personal media, credentials,
   generated videos, local databases, and model weights.
3. Review every media asset intentionally included in the candidate snapshot
   and its provenance records, all third-party notices, patches, pinned model
   revisions, dependency lock files, and the exact files in the skill archive.
   The initial source-only snapshot should contain no example media. Do not
   infer a license for an asset from its presence in a development checkout.
4. Run `uv run --frozen python scripts/release_audit.py --release` from a clean
   reviewed publication checkout. Run a dedicated secret/history scanner before
   pushing; the local audit checks risky historical filenames but does not
   replace a complete secret scan.
5. Publish only after verifying the resulting GitHub repository visibility and
   contents. Public visibility is not an open-source grant; keep the repository
   and buyer license terms consistent.

## Before selling or distributing the skill

1. Have counsel review the buyer-license draft, and ensure the same terms appear
   in the checkout/download flow and package.
2. Do not bundle model weights or customer/creator face, voice, or motion assets.
   Buyers must obtain rights to their own inputs and comply with each model's
   terms.
3. The included LivePortrait path downloads InsightFace detector weights
   designated for non-commercial research. Do not advertise that path as
   commercially cleared. Replace that detector with a commercially licensed
   alternative or remove/disable LivePortrait from commercial instructions.
4. Resolve exact source/license provenance for the face-parser and ResNet-18
   checkpoints, and lock every dependency in the MuseTalk and LivePortrait
   sidecar environments. `THIRD_PARTY_NOTICES.md` is an inventory, not legal
   advice or a complete clearance certificate.
5. Verify installation and render quality on a clean 24GB Apple Silicon Mac.
   CI tests fake media flows on Linux and a small Apple Silicon runner; it does
   not validate the full-size memory budget, model downloads, real TTS, lip
   sync, LivePortrait, or final video quality.

The tagged/manual paid-release workflow additionally requires
`scripts/release_audit.py --release --commercial`. It will not package a paid
candidate unless an owner-reviewed `COMMERCIAL_CLEARANCE.md` starts with
`Status: CLEARED` and the buyer license is no longer marked as a draft.

## Local checks

```bash
uv sync --frozen --extra test
uv run --frozen pytest
uv run --frozen python scripts/release_audit.py
scripts/package_skill.sh /tmp/digital-human-video.zip
unzip -t /tmp/digital-human-video.zip
```

The service is a local single-user preview, not a public SaaS. Keep the API and
model sidecar bound to `127.0.0.1`; adding public access requires authentication,
quotas, tenant isolation, retention/deletion controls, and a separate security
review.
