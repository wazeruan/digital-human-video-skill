from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


FORBIDDEN_SUFFIXES = {
    ".ckpt",
    ".gguf",
    ".mp3",
    ".mp4",
    ".mov",
    ".onnx",
    ".pkl",
    ".pt",
    ".pth",
    ".safetensors",
    ".sqlite",
    ".sqlite3",
    ".wav",
}
SECRET_PATTERNS = (
    re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{24,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)
APPROVED_SAMPLE_IMAGES: set[str] = set()


def tracked_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [root / Path(raw.decode()) for raw in result.stdout.split(b"\0") if raw]


def historical_paths(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        _, separator, path = line.partition(" ")
        if separator and path:
            paths.add(path)
    return paths


def audit(root: Path, *, release: bool, commercial: bool = False) -> list[str]:
    errors: list[str] = []
    paths = tracked_paths(root)
    for path in paths:
        relative = path.relative_to(root).as_posix()
        parts = {part.casefold() for part in Path(relative).parts}
        if parts.intersection({"vendor", "data", "outputs", ".venv"}):
            errors.append(f"runtime or generated directory is tracked: {relative}")
        if relative == ".env" or (
            Path(relative).name.startswith(".env.")
            and Path(relative).name != ".env.example"
        ):
            errors.append(f"environment secret file is tracked: {relative}")
        if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            errors.append(f"model, audio, or video binary is tracked: {relative}")
        if not path.is_file() or path.stat().st_size > 10 * 1024 * 1024:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                errors.append(f"possible credential in tracked text: {relative}")
                break

    if release:
        if not (root / "LICENSE").is_file():
            errors.append("release requires a root LICENSE chosen by the rights holder")
        if not (root / "skills/digital-human-video/BUYER-LICENSE.txt").is_file():
            errors.append("paid release requires a buyer license included with the skill")
        all_paths = {
            path.relative_to(root).as_posix()
            for path in paths
        } | historical_paths(root)
        if "examples/avatar.png" in all_paths:
            errors.append(
                "Git history contains legacy examples/avatar.png without a complete provenance receipt; "
                "publish from a reviewed clean history instead of pushing this history"
            )
        unreviewed_images = sorted(
            path
            for path in all_paths
            if Path(path).suffix.casefold()
            in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp", ".tif", ".tiff"}
            and path not in APPROVED_SAMPLE_IMAGES
        )
        if unreviewed_images:
            errors.append(
                "release history contains image assets without an explicit allowlisted provenance receipt: "
                + ", ".join(unreviewed_images)
            )
        historical_hazards = sorted(
            path
            for path in all_paths
            if Path(path).suffix.casefold() in FORBIDDEN_SUFFIXES
            or {part.casefold() for part in Path(path).parts}.intersection(
                {"vendor", "data", "outputs", ".venv"}
            )
            or path == ".env"
            or (Path(path).name.startswith(".env.") and Path(path).name != ".env.example")
        )
        if historical_hazards:
            errors.append(
                "release history contains generated, model, media, or environment files: "
                + ", ".join(historical_hazards[:12])
            )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout
        if status:
            errors.append("release requires a clean, reviewed Git worktree")
    if commercial:
        clearance = root / "COMMERCIAL_CLEARANCE.md"
        if not clearance.is_file():
            errors.append("commercial release requires an owner-reviewed COMMERCIAL_CLEARANCE.md")
        else:
            first_line = next(
                (line.strip() for line in clearance.read_text(encoding="utf-8").splitlines() if line.strip()),
                "",
            )
            if first_line != "Status: CLEARED":
                errors.append("commercial release is blocked until COMMERCIAL_CLEARANCE.md is explicitly cleared")
        buyer_license = root / "skills/digital-human-video/BUYER-LICENSE.txt"
        if not buyer_license.is_file() or "draft" in buyer_license.read_text(encoding="utf-8").casefold():
            errors.append("commercial release requires a final, reviewed buyer license")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check source files for release hazards.")
    parser.add_argument("--release", action="store_true", help="also enforce final release gates")
    parser.add_argument("--commercial", action="store_true", help="require commercial clearance as well")
    args = parser.parse_args()
    if args.commercial and not args.release:
        parser.error("--commercial requires --release")
    root = Path(__file__).resolve().parents[1]
    errors = audit(root, release=args.release, commercial=args.commercial)
    if errors:
        print("Release audit failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Source hygiene audit passed." if not args.release else "Release audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
