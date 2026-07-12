from aigp.control.pid import PID


def test_proportional():
    pid = PID(kp=2.0)
    assert pid.update(1.0, 0.01) == 2.0


def test_integral_antiwindup():
    pid = PID(kp=0.0, ki=1.0, i_limit=0.5)
    for _ in range(100):
        out = pid.update(1.0, 0.1)
    assert out == 0.5   # integral clamped


def test_output_clamp():
    pid = PID(kp=100.0, out_limit=1.0)
    assert pid.update(5.0, 0.01) == 1.0
    assert pid.update(-5.0, 0.01) == -1.0


def test_derivative_damps():
    pid = PID(kp=1.0, kd=0.1)
    pid.update(1.0, 0.1)
    out = pid.update(0.5, 0.1)   # error decreasing -> negative derivative
    assert out < 0.5


def test_reset():
    pid = PID(kp=0.0, ki=1.0)
    pid.update(1.0, 1.0)
    pid.reset()
    assert pid.update(0.0, 1.0) == 0.0
