from __future__ import annotations

import argparse
import sys
from pathlib import Path


def manifest_paths(manifest: Path) -> set[str]:
    paths: set[str] = set()
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"invalid manifest entry on line {line_number}")
        digest, relative_path = parts
        if len(digest) != 64 or any(char not in "0123456789abcdefABCDEF" for char in digest):
            raise ValueError(f"invalid SHA-256 digest on line {line_number}")
        paths.add(Path(relative_path).as_posix())
    return paths


def actual_paths(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
        if ".cache" not in path.relative_to(root).parts
    }


def verify(root: Path, manifest: Path) -> list[str]:
    if root.is_symlink() or not root.is_dir():
        return [f"model root must be a real directory: {root}"]
    expected = manifest_paths(manifest)
    actual = actual_paths(root)
    errors = [f"missing required model file: {item}" for item in sorted(expected - actual)]
    errors.extend(f"unexpected file in model directory: {item}" for item in sorted(actual - expected))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Require an exact model-file inventory.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        errors = verify(args.root, args.manifest)
    except (OSError, ValueError) as exc:
        print(f"Model inventory verification failed: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("Model inventory verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Model inventory matches the manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
