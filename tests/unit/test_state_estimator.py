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
