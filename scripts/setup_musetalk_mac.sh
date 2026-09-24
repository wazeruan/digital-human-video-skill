#!/usr/bin/env bash
set -euo pipefail
export HF_HUB_DISABLE_XET=1

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR_DIR="$PROJECT_DIR/vendor/musetalk-mac"
REVISION="7fd019315127d7f31e2e7f9853547ddceabbeb6e"
MUSETALK_WEIGHTS_REVISION="2bcb936e2fddb4d86db4c62fd45b387d0c061571"
SD_VAE_REVISION="31f26fdeee1355a5c34592e401dd41e45d25a493"
WHISPER_REVISION="169d4a4341b33bc18d8881c4b69c2e104e1cc0af"

mkdir -p "$PROJECT_DIR/vendor"
if [[ ! -d "$VENDOR_DIR/.git" ]]; then
  git clone https://github.com/barnent1/musetalk-mac.git "$VENDOR_DIR"
fi
git -C "$VENDOR_DIR" fetch --depth 1 origin "$REVISION"
git -C "$VENDOR_DIR" checkout --detach "$REVISION"
if ! git -C "$VENDOR_DIR" apply --reverse --check "$PROJECT_DIR/patches/musetalk-mac-local.patch" 2>/dev/null; then
  git -C "$VENDOR_DIR" apply --check "$PROJECT_DIR/patches/musetalk-mac-local.patch"
  git -C "$VENDOR_DIR" apply "$PROJECT_DIR/patches/musetalk-mac-local.patch"
fi

# The pinned Mac port accidentally ignores upstream/musetalk/models/ in Git.
# Restore the two inference modules from a reviewed, MPS-safe project patch.
mkdir -p "$VENDOR_DIR/upstream/musetalk/models"
cp "$PROJECT_DIR/patches/musetalk_missing_models/__init__.py" "$VENDOR_DIR/upstream/musetalk/models/__init__.py"
cp "$PROJECT_DIR/patches/musetalk_missing_models/unet.py" "$VENDOR_DIR/upstream/musetalk/models/unet.py"
cp "$PROJECT_DIR/patches/musetalk_missing_models/vae.py" "$VENDOR_DIR/upstream/musetalk/models/vae.py"
mkdir -p "$VENDOR_DIR/upstream/data/demo_five"

if [[ ! -x "$VENDOR_DIR/.venv/bin/python" ]]; then
  uv venv --python 3.11 "$VENDOR_DIR/.venv"
fi
uv pip install --python "$VENDOR_DIR/.venv/bin/python" -r "$VENDOR_DIR/requirements-mac.txt"
uv pip install --python "$VENDOR_DIR/.venv/bin/python" fastapi uvicorn pydantic

HF_CLI="$VENDOR_DIR/.venv/bin/hf"
if [[ ! -x "$HF_CLI" ]]; then
  HF_CLI="$VENDOR_DIR/.venv/bin/huggingface-cli"
fi
if [[ ! -x "$HF_CLI" ]]; then
  echo "Hugging Face CLI is missing from the MuseTalk environment." >&2
  exit 1
fi

MODEL_DIR="$VENDOR_DIR/upstream/models"
mkdir -p "$MODEL_DIR/musetalkV15" "$MODEL_DIR/sd-vae" \
  "$MODEL_DIR/whisper" "$MODEL_DIR/face-parse-bisent"

"$HF_CLI" download TMElyralab/MuseTalk \
  --revision "$MUSETALK_WEIGHTS_REVISION" --local-dir "$MODEL_DIR" \
  --include "musetalkV15/musetalk.json" "musetalkV15/unet.pth"
"$HF_CLI" download stabilityai/sd-vae-ft-mse \
  --revision "$SD_VAE_REVISION" --local-dir "$MODEL_DIR/sd-vae" \
  --include "config.json" "diffusion_pytorch_model.bin"
"$HF_CLI" download openai/whisper-tiny \
  --revision "$WHISPER_REVISION" --local-dir "$MODEL_DIR/whisper" \
  --include "config.json" "pytorch_model.bin" "preprocessor_config.json"

"$VENDOR_DIR/.venv/bin/gdown" 154JgKpzCPW82qINcVieuPH3fZ2e0P812 \
  -O "$MODEL_DIR/face-parse-bisent/79999_iter.pth"
curl --fail --location --silent --show-error \
  https://download.pytorch.org/models/resnet18-5c106cde.pth \
  -o "$MODEL_DIR/face-parse-bisent/resnet18-5c106cde.pth"

(
  "$VENDOR_DIR/.venv/bin/python" "$PROJECT_DIR/scripts/verify_model_tree.py" \
    --root "$MODEL_DIR" \
    --manifest "$PROJECT_DIR/models/musetalk.sha256"
  cd "$MODEL_DIR"
  shasum -a 256 --check "$PROJECT_DIR/models/musetalk.sha256"
)

echo "MuseTalk macOS sidecar installed at $VENDOR_DIR"
