#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT="${1:-$ROOT/dist/digital-human-video.zip}"
if [[ "$OUTPUT" != /* ]]; then
  OUTPUT="$PWD/$OUTPUT"
fi
if [[ -e "$OUTPUT" ]]; then
  echo "Output already exists: $OUTPUT; move it aside before packaging." >&2
  exit 2
fi
mkdir -p "$(dirname "$OUTPUT")"
(
  cd "$ROOT/skills"
  zip -qr "$OUTPUT" digital-human-video
)
echo "$OUTPUT"
