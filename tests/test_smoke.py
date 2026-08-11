from pathlib import Path
import sys

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
import ph_v02_full as ph


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
    assert out["sigma_min"] >= 0.0
    assert out["condition_number"] >= 1.0
