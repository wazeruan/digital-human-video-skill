#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--noncommercial-research" || "$#" -ne 1 ]]; then
  cat >&2 <<'EOF'
LivePortrait's bundled InsightFace detection weights are licensed for
non-commercial research only. This installer downloads and verifies them.

For non-commercial research, rerun with:
  ./scripts/setup_liveportrait_mac.sh --noncommercial-research

Do not use this route in a commercial product. Replace the detector and its
weights with a commercially licensed alternative first.
EOF
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEIGHTS_REVISION="82a4fa6735ca58432b6ce39301b4b9ee066dea47"
cd "$ROOT"
mkdir -p vendor
if [[ ! -d vendor/LivePortrait/.git ]]; then
  git clone https://github.com/KwaiVGI/LivePortrait.git vendor/LivePortrait
fi
cd vendor/LivePortrait
git fetch --depth 1 origin 9b294b3d0536135442ea73cb01e6cb3ca7029dd3
git checkout --detach 9b294b3d0536135442ea73cb01e6cb3ca7029dd3
cd "$ROOT"

if [[ ! -x vendor/LivePortrait/.venv/bin/python ]]; then
  uv venv --python 3.11 vendor/LivePortrait/.venv
fi
uv pip install --index-strategy unsafe-best-match --python vendor/LivePortrait/.venv/bin/python -r vendor/LivePortrait/requirements_macOS.txt
uv pip install --index-strategy unsafe-best-match --python vendor/LivePortrait/.venv/bin/python tyro==0.8.14 huggingface-hub requests

mkdir -p vendor/LivePortrait/pretrained_weights
HF_HUB_DISABLE_XET=1 vendor/LivePortrait/.venv/bin/hf download KwaiVGI/LivePortrait \
  --revision "$WEIGHTS_REVISION" \
  --local-dir vendor/LivePortrait/pretrained_weights \
  --include "insightface/models/buffalo_l/*.onnx" \
  --include "liveportrait/base_models/*.pth" \
  --include "liveportrait/landmark.onnx" \
  --include "liveportrait/retargeting_models/*.pth"
(
  "$ROOT/vendor/LivePortrait/.venv/bin/python" "$ROOT/scripts/verify_model_tree.py" \
    --root "$ROOT/vendor/LivePortrait/pretrained_weights" \
    --manifest "$ROOT/models/liveportrait.sha256"
  cd vendor/LivePortrait/pretrained_weights
  shasum -a 256 --check "$ROOT/models/liveportrait.sha256"
)

echo "LivePortrait research-only setup ready: vendor/LivePortrait/.venv/bin/python"
echo "Set DIGITAL_HUMAN_MOTION_BACKEND=liveportrait in .env"
