"""Build a restrained, seam-eased loop from a trusted LivePortrait template.

Run with the LivePortrait virtual environment. Pickle input must be trusted.
Eye keypoint x/z motion is suppressed; vertical blink motion remains.
These are latent controls, not a guarantee of gaze direction on every avatar.
"""
import argparse
import copy
import pickle
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


def prepare(source: Path, output: Path, frames: int = 72, *, start_frame=None,
            mouth_strength=0.65, face_strength=0.65, smoothing_radius=2):
    with source.open("rb") as handle:
        data = pickle.load(handle)
    if frames < 24 or frames > len(data["motion"]):
        raise ValueError("frames must be between 24 and the input frame count")
    lip_values = data.get("c_lip_lst", data.get("c_d_lip_lst"))
    if lip_values is None:
        # Legacy expression templates contain no measured ratios. These
        # placeholders only satisfy CLI loading; retargeting MUST stay off.
        lip_values = [np.zeros((1, 1), dtype=np.float32) for _ in data["motion"]]
    data["c_lip_lst"] = lip_values
    data["c_eyes_lst"] = data.get("c_eyes_lst", data.get("c_d_eyes_lst",
        [np.ones((1, 2), dtype=np.float32) for _ in data["motion"]]))
    lips = np.asarray(lip_values).reshape(len(data["motion"]), -1).mean(1)
    # Start with a relatively closed mouth so relative motion can open it.
    start = int(np.argmin(lips[:min(100, len(lips) - frames + 1)])) if start_frame is None else start_frame
    if start < 0 or start + frames > len(data["motion"]):
        raise ValueError("start frame is outside available motion")
    if smoothing_radius < 0 or not 0 <= mouth_strength <= 2 or not 0 <= face_strength <= 2:
        raise ValueError("invalid smoothing radius or motion strength")
    motions = copy.deepcopy(data["motion"][start:start + frames])
    original = copy.deepcopy(motions)
    baseline = original[0]
    for i, motion in enumerate(motions):
        window = original[max(0, i - smoothing_radius):min(frames, i + smoothing_radius + 1)]
        exp = np.mean([m["exp"] for m in window], axis=0) - baseline["exp"]
        gains = np.full((1, 21, 1), face_strength, dtype=np.float32)
        gains[:, [6, 12, 14, 17, 19, 20], :] = mouth_strength
        exp *= gains
        for eye in (11, 13, 15, 16, 18):
            exp[:, eye, 0] = 0
            exp[:, eye, 2] = 0
        # Smoothly return to the same neutral pose at both loop boundaries.
        edge = min(i / 10, (frames - 1 - i) / 10, 1)
        envelope = 0.5 - 0.5 * np.cos(np.pi * edge)
        motion["exp"] = (baseline["exp"] + exp * envelope).astype(np.float32)
        r0 = baseline["R"][0]
        delta = Rotation.from_matrix(motion["R"][0] @ r0.T).as_rotvec()
        motion["R"] = (Rotation.from_rotvec(delta * 0.2 * envelope).as_matrix() @ r0)[None].astype(np.float32)
        motion["t"] = (baseline["t"] + (motion["t"] - baseline["t"]) * 0.15 * envelope).astype(np.float32)
        motion["scale"] = baseline["scale"].copy()
    result = dict(data, motion=motions, n_frames=frames)
    for key in ("c_eyes_lst", "c_lip_lst"):
        result[key] = data[key][start:start + frames]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        pickle.dump(result, handle)
    print(f"Saved {frames} frames from offset {start} to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--frames", type=int, default=72)
    parser.add_argument("--start-frame", type=int)
    parser.add_argument("--mouth-strength", type=float, default=0.65)
    parser.add_argument("--face-strength", type=float, default=0.65)
    parser.add_argument("--smoothing-radius", type=int, default=2)
    args = parser.parse_args()
    prepare(args.source, args.output, args.frames, start_frame=args.start_frame,
            mouth_strength=args.mouth_strength, face_strength=args.face_strength,
            smoothing_radius=args.smoothing_radius)
