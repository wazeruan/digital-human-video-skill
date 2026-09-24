from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_model_tree.py"


def run_verifier(root: Path, manifest: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--manifest", str(manifest)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_model_inventory_matches_manifest_and_ignores_hub_cache(tmp_path):
    root = tmp_path / "models"
    root.mkdir()
    (root / "weights.bin").write_bytes(b"weights")
    (root / ".cache" / "huggingface").mkdir(parents=True)
    (root / ".cache" / "huggingface" / "metadata.json").write_text("{}")
    manifest = tmp_path / "models.sha256"
    manifest.write_text(f"{'a' * 64}  weights.bin\n")

    result = run_verifier(root, manifest)

    assert result.returncode == 0, result.stderr


def test_model_inventory_rejects_unexpected_files(tmp_path):
    root = tmp_path / "models"
    root.mkdir()
    (root / "weights.bin").write_bytes(b"weights")
    (root / "stale.onnx").write_bytes(b"old model")
    manifest = tmp_path / "models.sha256"
    manifest.write_text(f"{'a' * 64}  weights.bin\n")

    result = run_verifier(root, manifest)

    assert result.returncode == 1
    assert "unexpected file in model directory: stale.onnx" in result.stderr
