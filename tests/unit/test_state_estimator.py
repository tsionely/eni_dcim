import numpy as np

from aigp.core.messages import ImuSample
from aigp.core.params import ParamSet
from aigp.estimation.attitude_filter import GRAVITY, yaw_from_quat
from aigp.estimation.state_estimator import StateEstimator


def make_estimator():
    return StateEstimator(ParamSet.load("config/params_default.json"))


def feed_stationary(est, gyro, seconds=5.0, hz=200.0):
    accel = np.array([0.0, 0.0, -GRAVITY])   # level, at rest
    n = int(seconds * hz)
    for i in range(n):
        est.predict(ImuSample(ts_ns=int(i * 1e9 / hz), accel=accel, gyro=gyro))


def test_dead_zgyro_pin_cannot_drift_yaw():
    # estimation.gyro_z_dead (default): the pinned z channel is REPLACED by
    # the reconstructed yaw rate, so even an uncalibrated pin value must
    # produce zero yaw drift.
    est = make_estimator()
    feed_stationary(est, gyro=np.array([0.0, 0.0, -0.5]))
    assert abs(yaw_from_quat(est.attitude.q)) < 0.05


def test_dead_zgyro_yaw_follows_commanded_rate():
    est = make_estimator()
    est.set_cmd_yaw_rate(0.5)
    # Pin value on the wire is irrelevant; commanded yaw drives the estimate.
    feed_stationary(est, gyro=np.array([0.0, 0.0, 0.013]), seconds=2.0)
    assert 0.8 < yaw_from_quat(est.attitude.q) < 1.2


def test_live_zgyro_bias_subtraction_and_inverted_tracking():
    # With gyro_z_dead=false the raw channel is used: bias subtraction must
    # stop drift, and true rotation must be tracked THROUGH the sim's
    # sign-inverted reporting (estimation.gyro_sign=-1, phase2k finding).
    params = ParamSet.load("config/params_default.json").patch(
        {"estimation.gyro_z_dead": False})
    bias = np.array([0.0, 0.0, -0.5])

    drifting = StateEstimator(params)
    feed_stationary(drifting, gyro=bias)
    assert abs(yaw_from_quat(drifting.attitude.q)) > 1.0   # ~2.5 rad of drift

    calibrated = StateEstimator(params)
    calibrated.set_gyro_bias(bias)
    feed_stationary(calibrated, gyro=bias)
    assert abs(yaw_from_quat(calibrated.attitude.q)) < 0.05

    est = StateEstimator(params)
    # True +0.5 rad/s arrives as -0.5 on the wire (inverted reporting).
    feed_stationary(est, gyro=np.array([0.0, 0.0, -0.5]), seconds=2.0)
    assert 0.8 < yaw_from_quat(est.attitude.q) < 1.2


def _det(ts_ns, t_cam, center=(320.0, 180.0)):
    from aigp.core.messages import GateDetection, RelPose
    return GateDetection(
        ts_ns=ts_ns, corners_px=np.zeros((4, 2)), center_px=center,
        image_size=(640, 360),
        rel_pose=RelPose(t=np.array(t_cam, dtype=float),
                         normal=np.array([0.0, 0.0, -1.0])),
        confidence=1.0)


def _tick(est, ts_ns):
    est.predict(ImuSample(ts_ns=ts_ns, gyro=np.zeros(3),
                          accel=np.array([0.0, 0.0, -GRAVITY])))


def test_gate_lock_rejects_other_gate_mid_track():
    """R2 (phase3a): several gates in frame — a fix 40m away must NOT
    replace a locked 6m gate (the largest-ring heuristic switched targets
    mid-commit, 1.8m -> 46m)."""
    est = make_estimator()
    ts = 0
    for i in range(30):                      # lock onto a ~6m gate
        ts = int(i * 0.02e9)
        _tick(est, ts)
        est.update_vision(_det(ts, [0.0, 0.0, 6.0]))
    assert est.state.gate_rel is not None
    d0 = est.state.gate_rel.distance
    assert 5.0 < d0 < 7.0
    # A far gate flashes in for a few frames.
    for i in range(5):
        ts += int(0.02e9)
        _tick(est, ts)
        est.update_vision(_det(ts, [5.0, 0.0, 45.0], center=(100.0, 200.0)))
    assert est.state.gate_rel.distance < 8.0, "lock jumped to the far gate"


def test_gate_lock_relocks_after_sustained_loss():
    """After relock_s without an accepted fix, a new target wins."""
    est = make_estimator()
    ts = 0
    for i in range(30):
        ts = int(i * 0.02e9)
        _tick(est, ts)
        est.update_vision(_det(ts, [0.0, 0.0, 6.0]))
    # Silence (no fixes) for 1.4s > relock_s, then a different gate appears.
    for i in range(70):
        ts += int(0.02e9)
        _tick(est, ts)
    ts += int(0.02e9)
    _tick(est, ts)
    est.update_vision(_det(ts, [3.0, 1.0, 14.0]))
    gr = est.state.gate_rel
    assert gr is not None and gr.distance > 10.0, "did not relock to the new gate"


def test_relock_distance_sanity_rejects_far_gate():
    """Milestone autopsy: after losing a ~1m gate mid-attempt, the relock
    accepted a 27m gate off to the side and the drone chased it into
    hangar steel. Relock must hold out for a sane-distance candidate."""
    est = make_estimator()
    ts = 0
    for i in range(30):                      # lock a ~2m gate
        ts = int(i * 0.02e9)
        _tick(est, ts)
        est.update_vision(_det(ts, [0.0, 0.0, 2.0]))
    # Sustained loss (> relock_s), then a FAR gate appears.
    for i in range(80):
        ts += int(0.02e9)
        _tick(est, ts)
    ts += int(0.02e9)
    _tick(est, ts)
    est.update_vision(_det(ts, [18.0, -10.0, 17.0]))
    gr = est._gate_rel
    assert gr is None or np.linalg.norm(gr.t) < 10, "relocked onto the far gate"
    # A sane-distance candidate IS accepted.
    ts += int(0.02e9)
    _tick(est, ts)
    est.update_vision(_det(ts, [1.0, 0.5, 4.0]))
    assert est._gate_rel is not None and np.linalg.norm(est._gate_rel.t) < 6


def test_relock_escape_hatch_is_time_based():
    """If only far candidates exist, the TIME-based hatch (2.5s) re-locks —
    but not sooner: a count-based hatch opened in 0.11s at the real sim's
    224Hz fix rate and sent every phase4b flight chasing a far gate into
    hangar steel."""
    est = make_estimator()
    ts = 0
    for i in range(30):
        ts = int(i * 0.02e9)
        _tick(est, ts)
        est.update_vision(_det(ts, [0.0, 0.0, 2.0]))
    for i in range(80):
        ts += int(0.02e9)
        _tick(est, ts)
    # 1s of far-gate fixes at 50Hz: must still be REJECTED (< 2.5s).
    for i in range(50):
        ts += int(0.02e9)
        _tick(est, ts)
        est.update_vision(_det(ts, [5.0, 0.0, 20.0]))
    assert est._gate_rel is None or np.linalg.norm(est._gate_rel.t) < 10
    # After 2.5s+ of consistent far fixes: accepted.
    for i in range(100):
        ts += int(0.02e9)
        _tick(est, ts)
        est.update_vision(_det(ts, [5.0, 0.0, 20.0]))
    assert est._gate_rel is not None and np.linalg.norm(est._gate_rel.t) > 10
