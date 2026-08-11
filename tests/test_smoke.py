from pathlib import Path
import importlib.util


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "ph_v02_full.py"
spec = importlib.util.spec_from_file_location("ph_v02_full", MODULE_PATH)
ph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ph)


def test_boundary_target_in_range():
    cfg = ph.PHConfig()
    system = ph.PHToySystem(cfg, mode="coupled")
    for h in (0.0, 0.5, 1.0):
        b = system.boundary_target(h)
        assert cfg.boundary_floor <= b <= cfg.boundary_ceil


def test_observability_proxy_is_finite():
    cfg = ph.PHConfig()
    system = ph.PHToySystem(cfg, mode="coupled")
    out = system.observability_opacity(cfg.boundary_baseline)
    assert 0.0 <= out["omega"] <= 1.0
    assert out["effective_rank"] > 0.0
    assert out["sigma_max"] >= out["sigma_min"] >= 0.0
