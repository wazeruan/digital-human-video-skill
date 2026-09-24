#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ ! -f "$ROOT/skills/digital-human-video/SKILL.md" ]]; then
  echo "Digital Human Video skill is missing from this checkout." >&2
  exit 1
fi
SKILLS_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
DESTINATION="$SKILLS_ROOT/digital-human-video"

if [[ -e "$DESTINATION" ]]; then
  echo "Skill already exists at $DESTINATION; move it aside before installing." >&2
  exit 2
fi

mkdir -p "$SKILLS_ROOT"
cp -R "$ROOT/skills/digital-human-video" "$DESTINATION"
echo "Installed digital-human-video at $DESTINATION"
