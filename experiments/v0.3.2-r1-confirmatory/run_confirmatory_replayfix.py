from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BASE_CONFIRMATORY = HERE / "run_confirmatory.py"
FROZEN_DIR = HERE / "frozen"

_spec = importlib.util.spec_from_file_location("ph_v032_r1_confirmatory_frozen", BASE_CONFIRMATORY)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load frozen Confirmatory implementation: {BASE_CONFIRMATORY}")
mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = mod
_spec.loader.exec_module(mod)


def repaired_reconstruct_pilot_freeze(freeze: dict):
    # Technical replay repair only:
    # provenance is byte-exact on committed Pilot artifacts;
    # floating-point recomputation is compared at 1e-12 tolerance.
    frozen_files = {
        "standardization.json": FROZEN_DIR / "standardization.json",
        "calibrated_thresholds.json": FROZEN_DIR / "calibrated_thresholds.json",
        "m10_frozen_from_fresh_tuning.json": FROZEN_DIR / "m10_frozen_from_fresh_tuning.json",
    }
    for name, path in frozen_files.items():
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        want = freeze["pilot_artifact_members"][name]
        if got != want:
            raise RuntimeError(f"frozen Pilot artifact mismatch: {name}: {got} != {want}")

    std_ref = json.loads(frozen_files["standardization.json"].read_text(encoding="utf-8"))
    thresholds_ref = json.loads(frozen_files["calibrated_thresholds.json"].read_text(encoding="utf-8"))
    m10_ref = json.loads(frozen_files["m10_frozen_from_fresh_tuning.json"].read_text(encoding="utf-8"))

    r1 = mod.r1
    r1.base.VERSION = r1.VERSION
    r1.base.N_DEFAULT = r1.N

    opt_score, selected = r1.base.optimize_m10()
    if selected.__dict__ != m10_ref or m10_ref != freeze["frozen_m10"]:
        raise RuntimeError("M10 reconstruction mismatch")
    if not math.isclose(float(opt_score), float(freeze["pilot_m10_objective"]), rel_tol=1e-12, abs_tol=1e-12):
        raise RuntimeError("M10 objective reconstruction mismatch")

    X, rows, feature_names = r1.build_aggregate_dataset(selected)
    y = np.array([1 if mode == "M0" else 0 for mode, _ in rows], dtype=int)
    fit_mask = r1.split_mask(rows, r1.FIT)
    cal_mask = r1.split_mask(rows, r1.CAL)

    mu_replay, sd_replay = r1.fit_standard(X[fit_mask])
    mu = np.asarray(std_ref["mean"], dtype=float)
    sd = np.asarray(std_ref["std"], dtype=float)

    if feature_names != std_ref["features"]:
        raise RuntimeError("standardization feature order mismatch")
    if not np.allclose(mu_replay, mu, rtol=1e-12, atol=1e-12):
        raise RuntimeError("standardization mean replay mismatch beyond 1e-12")
    if not np.allclose(sd_replay, sd, rtol=1e-12, atol=1e-12):
        raise RuntimeError("standardization std replay mismatch beyond 1e-12")

    Z = (X - mu) / sd
    cal_rows = [row for row, keep in zip(rows, cal_mask) if keep]
    models = {}

    for name, cls in r1.REPRESENTATIONS.items():
        model = cls().fit(Z[fit_mask], y[fit_mask])
        cal_scores = np.asarray(model.score(Z[cal_mask]), dtype=float)
        calibration = r1.calibrate_threshold(cal_scores, cal_rows)
        frozen = thresholds_ref[name]
        manifest = freeze["thresholds"][name]

        for key in ("threshold", "calibration_tpr_M0", "calibration_worst_fp"):
            if float(frozen[key]) != float(manifest[key]):
                raise RuntimeError(f"threshold freeze manifest mismatch: {name}.{key}")
            if not math.isclose(float(calibration[key]), float(frozen[key]), rel_tol=1e-12, abs_tol=1e-12):
                raise RuntimeError(f"threshold replay mismatch beyond 1e-12: {name}.{key}")

        if bool(calibration["feasible"]) != bool(frozen["feasible"]) or bool(frozen["feasible"]) != bool(manifest["feasible"]):
            raise RuntimeError(f"threshold feasibility mismatch: {name}")

        models[name] = model

    return selected, mu, sd, feature_names, models


mod.reconstruct_pilot_freeze = repaired_reconstruct_pilot_freeze


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="experiments/v0.3.2-r1-confirmatory/artifacts/confirmatory")
    args = ap.parse_args()
    raise SystemExit(mod.run_confirmatory(Path(args.outdir)))


if __name__ == "__main__":
    main()
