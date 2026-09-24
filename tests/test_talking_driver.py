"""Pure-template checks; no model weights or GPU are required."""
import importlib.util
import pickle
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
Rotation = pytest.importorskip("scipy.spatial.transform").Rotation
spec = importlib.util.spec_from_file_location(
    "prepare_talking_driver", Path(__file__).parents[1] / "scripts/prepare_talking_driver.py"
)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def template(count=40):
    motions = []
    for i in range(count):
        motions.append({
            "exp": np.full((1, 21, 3), i / count, dtype=np.float32),
            "R": Rotation.from_euler("xyz", [i, i / 2, i / 3], degrees=True).as_matrix()[None],
            "t": np.full((1, 3), i / count, dtype=np.float32),
            "scale": np.array([[1 + i / count]], dtype=np.float32),
        })
    return {"motion": motions, "n_frames": count, "output_fps": 25,
            "c_lip_lst": [np.array([[abs(i - 10) / count]]) for i in range(count)],
            "c_eyes_lst": [np.ones((1, 2)) for _ in range(count)]}


def test_driver_loop_matches_pose_and_restrains_eyes(tmp_path):
    source, output = tmp_path / "source.pkl", tmp_path / "nested/result.pkl"
    original = template()
    source.write_bytes(pickle.dumps(original))
    driver.prepare(source, output, frames=24)
    result = pickle.loads(output.read_bytes())
    assert result["n_frames"] == len(result["motion"]) == 24
    assert result["output_fps"] == 25
    assert len(result["c_lip_lst"]) == len(result["c_eyes_lst"]) == 24
    first, last = result["motion"][0], result["motion"][-1]
    for key in ("exp", "R", "t", "scale"):
        np.testing.assert_allclose(first[key], last[key], atol=1e-6)
        np.testing.assert_allclose(first[key], original["motion"][10][key], atol=1e-6)
    for motion in result["motion"]:
        rotation = motion["R"][0]
        np.testing.assert_allclose(rotation @ rotation.T, np.eye(3), atol=1e-6)
        assert np.linalg.det(rotation) == pytest.approx(1, abs=1e-6)
        for eye in (11, 13, 15, 16, 18):
            np.testing.assert_allclose(motion["exp"][:, eye, [0, 2]], first["exp"][:, eye, [0, 2]])
    assert not np.allclose(result["motion"][12]["exp"][:, 6], first["exp"][:, 6])
    assert source.read_bytes() == pickle.dumps(original)


@pytest.mark.parametrize("frames", [0, 23, 41])
def test_driver_rejects_invalid_frame_bounds(tmp_path, frames):
    source, output = tmp_path / "source.pkl", tmp_path / "output.pkl"
    source.write_bytes(pickle.dumps(template()))
    with pytest.raises(ValueError, match="frames must be between"):
        driver.prepare(source, output, frames=frames)
    assert not output.exists()


def test_driver_can_use_all_input_frames(tmp_path):
    source, output = tmp_path / "source.pkl", tmp_path / "output.pkl"
    source.write_bytes(pickle.dumps(template()))
    driver.prepare(source, output, frames=40)
    assert len(pickle.loads(output.read_bytes())["motion"]) == 40


@pytest.mark.parametrize("ratios", ["legacy", "missing"])
def test_legacy_ratio_templates_are_loadable(tmp_path, ratios):
    data = template()
    for key in ("c_lip_lst", "c_eyes_lst"):
        values = data.pop(key)
        if ratios == "legacy":
            data[key.replace("c_", "c_d_")] = values
    source, output = tmp_path / "source.pkl", tmp_path / "out.pkl"
    source.write_bytes(pickle.dumps(data))
    driver.prepare(source, output, frames=24, start_frame=4)
    result = pickle.loads(output.read_bytes())
    assert len(result["c_lip_lst"]) == len(result["c_eyes_lst"]) == 24
    if ratios == "legacy":
        np.testing.assert_array_equal(result["c_lip_lst"][0], data["c_d_lip_lst"][4])
        np.testing.assert_array_equal(result["c_eyes_lst"][0], data["c_d_eyes_lst"][4])
    else:
        np.testing.assert_array_equal(result["c_lip_lst"][0], np.zeros((1, 1)))
        np.testing.assert_array_equal(result["c_eyes_lst"][0], np.ones((1, 2)))


def test_explicit_start_and_separate_mouth_face_strength(tmp_path):
    source, output = tmp_path / "source.pkl", tmp_path / "out.pkl"
    data = template()
    source.write_bytes(pickle.dumps(data))
    driver.prepare(source, output, frames=24, start_frame=3,
                   mouth_strength=1.0, face_strength=0.0, smoothing_radius=0)
    result = pickle.loads(output.read_bytes())
    np.testing.assert_allclose(result["motion"][0]["exp"], data["motion"][3]["exp"])
    mid = result["motion"][11]["exp"]
    np.testing.assert_allclose(mid[:, [6, 12, 14, 17, 19, 20]],
                               data["motion"][14]["exp"][:, [6, 12, 14, 17, 19, 20]])
    np.testing.assert_allclose(mid[:, [0, 1, 11, 13]],
                               data["motion"][3]["exp"][:, [0, 1, 11, 13]])
    np.testing.assert_allclose(result["motion"][-1]["exp"], data["motion"][3]["exp"])


@pytest.mark.parametrize("options", [
    {"start_frame": -1}, {"start_frame": 17}, {"smoothing_radius": -1},
    {"mouth_strength": -0.1}, {"mouth_strength": 2.1},
    {"face_strength": -0.1}, {"face_strength": 2.1},
    {"mouth_strength": float("nan")},
])
def test_invalid_driver_controls_fail_without_output(tmp_path, options):
    source, output = tmp_path / "source.pkl", tmp_path / "out.pkl"
    source.write_bytes(pickle.dumps(template()))
    with pytest.raises(ValueError):
        driver.prepare(source, output, frames=24, **options)
    assert not output.exists()
