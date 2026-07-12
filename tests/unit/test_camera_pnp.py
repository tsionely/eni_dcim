import numpy as np

from aigp.perception.camera import PinholeCamera, body_to_cam, cam_to_body


def project(K, points_cam):
    uv = []
    for p in points_cam:
        uv.append([K[0, 0] * p[0] / p[2] + K[0, 2],
                   K[1, 1] * p[1] / p[2] + K[1, 2]])
    return np.array(uv)


def test_pnp_recovers_known_pose():
    cam = PinholeCamera(fov_deg=90.0)
    size = (640, 360)
    K = cam.matrix(*size)
    gate_w = gate_h = 1.6
    dist = 6.0

    # Gate facing the camera, centered, at 6m.
    corners_gate = np.array([
        [-gate_w / 2, -gate_h / 2, 0.0],
        [gate_w / 2, -gate_h / 2, 0.0],
        [gate_w / 2, gate_h / 2, 0.0],
        [-gate_w / 2, gate_h / 2, 0.0],
    ])
    corners_cam = corners_gate + np.array([0.0, 0.0, dist])
    corners_px = project(K, corners_cam)

    rel = cam.solve_gate_pnp(corners_px, size, gate_w, gate_h)
    assert rel is not None
    assert abs(rel.t[2] - dist) < 0.2
    assert abs(rel.t[0]) < 0.1 and abs(rel.t[1]) < 0.1
    # Gate plane normal points back at the camera (-z).
    assert rel.normal[2] < -0.9


def test_pnp_lateral_offset():
    cam = PinholeCamera(fov_deg=90.0)
    size = (640, 360)
    K = cam.matrix(*size)
    corners_gate = np.array([
        [-0.8, -0.8, 0.0], [0.8, -0.8, 0.0], [0.8, 0.8, 0.0], [-0.8, 0.8, 0.0],
    ])
    corners_cam = corners_gate + np.array([2.0, 0.0, 8.0])   # 2m to the right
    rel = cam.solve_gate_pnp(project(K, corners_cam), size, 1.6, 1.6)
    assert rel is not None
    assert rel.t[0] > 1.5


def test_degenerate_returns_none():
    cam = PinholeCamera(fov_deg=90.0)
    collinear = np.array([[0, 0], [1, 1], [2, 2], [3, 3]], dtype=np.float64)
    assert cam.solve_gate_pnp(collinear, (640, 360), 1.6, 1.6) is None


def test_body_cam_axes_roundtrip():
    v = np.array([1.0, 2.0, 3.0])
    assert np.allclose(cam_to_body(body_to_cam(v)), v)
    # Body forward = camera z.
    assert np.allclose(body_to_cam(np.array([1.0, 0.0, 0.0])), [0.0, 0.0, 1.0])
