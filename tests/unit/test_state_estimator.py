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


def test_gyro_bias_subtraction_stops_yaw_drift():
    bias = np.array([0.0, 0.0, -0.5])   # the frozen-channel artifact magnitude

    drifting = make_estimator()
    feed_stationary(drifting, gyro=bias)
    assert abs(yaw_from_quat(drifting.attitude.q)) > 1.0   # ~2.5 rad of drift

    calibrated = make_estimator()
    calibrated.set_gyro_bias(bias)
    feed_stationary(calibrated, gyro=bias)
    assert abs(yaw_from_quat(calibrated.attitude.q)) < 0.05


def test_true_rotation_still_tracked_without_bias():
    est = make_estimator()
    # True rotation (no bias set): +0.5 rad/s for 2s -> yaw ~ +1 rad.
    feed_stationary(est, gyro=np.array([0.0, 0.0, 0.5]), seconds=2.0)
    assert 0.8 < yaw_from_quat(est.attitude.q) < 1.2
