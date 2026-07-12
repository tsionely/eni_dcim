import numpy as np

from aigp.estimation.attitude_filter import (
    GRAVITY,
    MahonyFilter,
    quat_normalize,
    quat_rotate,
    quat_rotate_inv,
)


def test_quat_identity_rotation():
    q = np.array([1.0, 0.0, 0.0, 0.0])
    v = np.array([1.0, 2.0, 3.0])
    assert np.allclose(quat_rotate(q, v), v)
    assert np.allclose(quat_rotate_inv(q, v), v)


def test_quat_yaw_90():
    # 90 deg yaw about z (NED down): body x maps to world y.
    q = quat_normalize(np.array([np.cos(np.pi / 4), 0.0, 0.0, np.sin(np.pi / 4)]))
    v = quat_rotate(q, np.array([1.0, 0.0, 0.0]))
    assert np.allclose(v, [0.0, 1.0, 0.0], atol=1e-9)


def test_level_hover_stays_level():
    f = MahonyFilter(kp=2.0)
    accel = np.array([0.0, 0.0, -GRAVITY])   # level: specific force straight up
    gyro = np.zeros(3)
    for _ in range(500):
        f.update(gyro, accel, 0.004)
    down_body = quat_rotate_inv(f.q, np.array([0.0, 0.0, 1.0]))
    assert np.allclose(down_body, [0.0, 0.0, 1.0], atol=1e-3)


def test_accel_corrects_gyro_drift():
    f = MahonyFilter(kp=2.0)
    # Biased gyro tries to roll; accelerometer says level.
    gyro = np.array([0.05, 0.0, 0.0])
    accel = np.array([0.0, 0.0, -GRAVITY])
    for _ in range(2000):
        f.update(gyro, accel, 0.004)
    down_body = quat_rotate_inv(f.q, np.array([0.0, 0.0, 1.0]))
    # Correction bounds the drift instead of integrating it away.
    assert abs(down_body[1]) < 0.1
    assert down_body[2] > 0.99


def test_gravity_body_when_rolled():
    f = MahonyFilter(kp=5.0)
    # Static 30-degree roll. Gravity in body frame is (0, G sin, G cos);
    # the accelerometer measures specific force f = -g_body at rest.
    roll = np.radians(30)
    g_body_true = np.array([0.0, GRAVITY * np.sin(roll), GRAVITY * np.cos(roll)])
    accel = -g_body_true
    for _ in range(3000):
        f.update(np.zeros(3), accel, 0.004)
    assert np.allclose(f.gravity_body(), g_body_true, atol=0.2)
