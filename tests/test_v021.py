from pathlib import Path
import importlib.util, sys
import numpy as np

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "ph_v021_causal_specificity.py"
spec = importlib.util.spec_from_file_location("ph_v021", MODULE_PATH)
ph = importlib.util.module_from_spec(spec)
sys.modules["ph_v021"] = ph
spec.loader.exec_module(ph)


def test_continuous_horizon_is_estimable():
    c = ph.Cfg(trials=200)
    m = ph.Model(c, "M0_coupled_PH")
    d0, dyn0 = m.curve(12345, 0.0)
    d1, dyn1 = m.curve(12345, 0.5)
    assert dyn0 and dyn1
    assert np.isfinite(d0) and np.isfinite(d1)
    assert d1 < d0


def test_coupled_boundary_moves_both_observability_metrics():
    c = ph.Cfg()
    m = ph.Model(c, "M0_coupled_PH")
    o0, js0 = m.obs(22222, 0.0)
    o1, js1 = m.obs(22222, 0.5)
    assert o1 < o0
    assert js1 > js0


def test_common_driver_is_invariant_to_boundary_intervention():
    c = ph.Cfg()
    m = ph.Model(c, "M2_common_driver")
    o0, _ = m.obs(33333, 0.0)
    o1, _ = m.obs(33333, 0.5)
    assert abs(o1 - o0) < 1e-12
