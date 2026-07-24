import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("run_final_meter_ledger.py")


def load_module():
    spec = importlib.util.spec_from_file_location("final_meter_ledger", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_signed_plane_prefers_unit_normal():
    ledger = load_module()
    assert ledger.signed_plane((0.0, 0.0, 2.0), (0.0, 0.0, -1.0)) == 2.0


def test_signed_plane_falls_back_to_camera_depth():
    ledger = load_module()
    assert ledger.signed_plane((1.0, 2.0, 3.0), (2.0, 0.0, 0.0)) == 3.0
