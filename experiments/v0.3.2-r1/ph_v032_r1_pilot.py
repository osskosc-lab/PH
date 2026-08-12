from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

VERSION = "PH-v0.3.2-r1"
N = 80
TUNE = range(0, 20)
FIT = range(20, 40)
CAL = range(40, 60)
EVAL = range(60, 80)
PRIMARY = "balanced_logistic"
TARGET_NEGATIVES = ("M10", "M1", "M2", "M5")

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE.parent / "v0.3.2" / "ph_v032_pilot.py"
_spec = importlib.util.spec_from_file_location("ph_v032_base", BASE_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load base implementation: {BASE_PATH}")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

# Fresh namespace, while retaining the exact v0.3.2 dynamics, M10 grid and 35-feature extractor.
base.VERSION = VERSION
base.N_DEFAULT = N
MODES = list(base.MODES)
TRAIN_CONDITIONS = list(base.TRAIN_CONDITIONS)
RAW_FEATURE_COUNT = 35
AGG_FEATURE_COUNT = 70
EPS = 1e-12


def h32(token: str) -> int:
    return int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big")


def old_audit_seed(mode: str, condition: str, index: int) -> int:
    return h32(f"PH-v0.3.2|pilot|{mode}|{condition}|{index}")


def aggregate_row(mode: str, index: int, m10) -> tuple[np.ndarray, list[str]]:
    per_condition = []
    raw_names = None
    for condition in TRAIN_CONDITIONS:
        row, raw_names = base.raw_row(mode, condition, index, m10)
        per_condition.append(row)
    A = np.vstack(per_condition)
    if raw_names is None:
        raise RuntimeError("raw feature names missing")
    names = [f"mean::{x}" for x in raw_names] + [f"std::{x}" for x in raw_names]
    return np.concatenate([A.mean(axis=0), A.std(axis=0)]), names


def build_aggregate_dataset(m10):
    rows = []
    X = []
    names = None
    for mode in MODES:
        for index in range(N):
            x, names = aggregate_row(mode, index, m10)
            X.append(x)
            rows.append((mode, index))
    return np.vstack(X), rows, names


def split_mask(rows, indices):
    ii = set(indices)
    return np.array([index in ii for _, index in rows], dtype=bool)


def balanced_weights(y: np.ndarray) -> np.ndarray:
    pos = y == 1
    neg = ~pos
    if pos.sum() == 0 or neg.sum() == 0:
        raise RuntimeError("both classes are required")
    w = np.zeros(len(y), dtype=float)
    w[pos] = 0.5 / pos.sum()
    w[neg] = 0.5 / neg.sum()
    return w / w.mean()


def fit_standard(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    return mu, np.where(sd < 1e-6, 1.0, sd)


class BalancedLogistic:
    def fit(self, X, y):
        Xa = np.column_stack([np.ones(len(X)), X])
        sw = balanced_weights(y)
        coef = np.zeros(Xa.shape[1])
        for _ in range(700):
            z = np.clip(Xa @ coef, -30, 30)
            p = 1.0 / (1.0 + np.exp(-z))
            grad = Xa.T @ (sw * (p - y)) / sw.sum()
            grad[1:] += 0.02 * coef[1:]
            coef -= 0.18 * grad
        self.coef = coef
        return self

    def score(self, X):
        return np.column_stack([np.ones(len(X)), X]) @ self.coef


class BalancedRidge:
    def fit(self, X, y):
        Xa = np.column_stack([np.ones(len(X)), X])
        sw = balanced_weights(y)
        yy = 2.0 * y - 1.0
        XtW = Xa.T * sw
        reg = np.eye(Xa.shape[1]) * 1.0
        reg[0, 0] = 0.0
        self.coef = np.linalg.solve(XtW @ Xa + reg, XtW @ yy)
        return self

    def score(self, X):
        return np.column_stack([np.ones(len(X)), X]) @ self.coef


class ShrinkageDiagonalLDA:
    def fit(self, X, y):
        x1 = X[y == 1]
        x0 = X[y == 0]
        self.m1 = x1.mean(axis=0)
        self.m0 = x0.mean(axis=0)
        v1 = x1.var(axis=0)
        v0 = x0.var(axis=0)
        pooled = 0.5 * (v1 + v0)
        floor = max(float(np.median(pooled)) * 0.25, 1e-4)
        self.var = pooled + floor
        self.mid = 0.5 * (self.m1 + self.m0)
        self.direction = (self.m1 - self.m0) / self.var
        return self

    def score(self, X):
        return (X - self.mid) @ self.direction


class BalancedCentroid:
    def fit(self, X, y):
        self.m1 = X[y == 1].mean(axis=0)
        self.m0 = X[y == 0].mean(axis=0)
        return self

    def score(self, X):
        d1 = np.sum((X - self.m1) ** 2, axis=1)
        d0 = np.sum((X - self.m0) ** 2, axis=1)
        return d0 - d1


class BalancedNonparametricDistance:
    def fit(self, X, y):
        self.pos = X[y == 1].copy()
        self.neg = X[y == 0].copy()
        return self

    @staticmethod
    def _mean_k_distance(z, ref, k=5):
        d = np.sum((ref - z) ** 2, axis=1)
        kk = min(k, len(d))
        return float(np.mean(np.partition(d, kk - 1)[:kk]))

    def score(self, X):
        out = []
        for z in X:
            dp = self._mean_k_distance(z, self.pos)
            dn = self._mean_k_distance(z, self.neg)
            out.append(dn - dp)
        return np.asarray(out)


REPRESENTATIONS = {
    "balanced_logistic": BalancedLogistic,
    "balanced_ridge": BalancedRidge,
    "shrinkage_diagonal_lda": ShrinkageDiagonalLDA,
    "balanced_centroid": BalancedCentroid,
    "balanced_nonparametric_distance": BalancedNonparametricDistance,
}


def rates_at_threshold(scores, rows, threshold):
    pred = scores >= threshold
    out = {}
    for mode in MODES:
        mask = np.array([m == mode for m, _ in rows])
        if mask.any():
            out[mode] = float(np.mean(pred[mask]))
    return out


def threshold_candidates(scores):
    s = np.unique(np.asarray(scores, dtype=float))
    if len(s) == 1:
        return np.array([s[0] - 1e-9, s[0] + 1e-9])
    mids = (s[:-1] + s[1:]) / 2.0
    pad = max(1e-9, float(np.ptp(s)) * 1e-9)
    return np.concatenate([[s[0] - pad], mids, [s[-1] + pad]])


def calibrate_threshold(scores, rows):
    feasible = []
    diagnostic = []
    for threshold in threshold_candidates(scores):
        rates = rates_at_threshold(scores, rows, float(threshold))
        tpr = rates.get("M0", 0.0)
        worst_fp = max(rates.get(m, 1.0) for m in TARGET_NEGATIVES)
        rec = (float(threshold), tpr, worst_fp, rates)
        diagnostic.append(rec)
        if tpr >= 0.80:
            feasible.append(rec)
    if feasible:
        chosen = min(feasible, key=lambda r: (r[2], -r[1], -r[0]))
        is_feasible = True
    else:
        chosen = max(diagnostic, key=lambda r: (r[1] - r[2], r[1], -r[2], r[0]))
        is_feasible = False
    threshold, tpr, worst_fp, rates = chosen
    return {
        "threshold": threshold,
        "feasible": is_feasible,
        "calibration_tpr_M0": tpr,
        "calibration_worst_fp": worst_fp,
        "calibration_rates": rates,
    }


def raw_dynamic_range(m10):
    raw = []
    for mode in ("M0", "M10"):
        for condition in TRAIN_CONDITIONS:
            for index in EVAL:
                f, _ = base.raw_row(mode, condition, index, m10)
                raw.append(f)
    A = np.vstack(raw)
    return A, A.std(axis=0)


def seed_integrity():
    new_audit = set()
    old_audit = set()
    pair_map = {}
    paired_ok = True
    for mode in MODES:
        for condition in TRAIN_CONDITIONS:
            for index in range(N):
                ns = base.audit_seed(mode, condition, index)
                os = old_audit_seed(mode, condition, index)
                if ns in new_audit:
                    return False, False, -1
                new_audit.add(ns)
                old_audit.add(os)
                key = (condition, index)
                ps = base.pair_seed(condition, index)
                if key in pair_map and pair_map[key] != ps:
                    paired_ok = False
                pair_map[key] = ps
    overlap = len(new_audit & old_audit)
    return True, paired_ok, overlap


def run_pilot(outdir: Path) -> int:
    outdir.mkdir(parents=True, exist_ok=True)

    # Fresh Pilot-side adversary tuning, exact carry-over grid/objective.
    opt_score, m10 = base.optimize_m10()

    X, rows, feature_names = build_aggregate_dataset(m10)
    y = np.array([1 if mode == "M0" else 0 for mode, _ in rows], dtype=int)
    fit_mask = split_mask(rows, FIT)
    cal_mask = split_mask(rows, CAL)
    eval_mask = split_mask(rows, EVAL)

    mu, sd = fit_standard(X[fit_mask])
    Z = (X - mu) / sd
    fit_rows = [r for r, keep in zip(rows, fit_mask) if keep]
    cal_rows = [r for r, keep in zip(rows, cal_mask) if keep]
    eval_rows = [r for r, keep in zip(rows, eval_mask) if keep]

    representation_results = {}
    fitted_ok = True
    for name, cls in REPRESENTATIONS.items():
        model = cls().fit(Z[fit_mask], y[fit_mask])
        fit_scores = np.asarray(model.score(Z[fit_mask]), dtype=float)
        cal_scores = np.asarray(model.score(Z[cal_mask]), dtype=float)
        eval_scores = np.asarray(model.score(Z[eval_mask]), dtype=float)
        calibration = calibrate_threshold(cal_scores, cal_rows)
        threshold = calibration["threshold"]
        eval_rates = rates_at_threshold(eval_scores, eval_rows, threshold)
        fitted_ok = fitted_ok and np.isfinite(fit_scores).all() and np.std(fit_scores) > 1e-8
        representation_results[name] = {
            **calibration,
            "evaluation_rates": eval_rates,
            "fit_score_std": float(np.std(fit_scores)),
            "evaluation_score_min": float(np.min(eval_scores)),
            "evaluation_score_max": float(np.max(eval_scores)),
        }

    primary = representation_results[PRIMARY]
    primary_rates = primary["evaluation_rates"]

    consensus_pass = []
    for name, result in representation_results.items():
        rr = result["evaluation_rates"]
        ok = bool(
            result["feasible"]
            and rr.get("M0", 0.0) >= 0.80
            and rr.get("M10", 1.0) <= 0.05
            and rr.get("M0", 0.0) > rr.get("M10", 1.0)
        )
        if ok:
            consensus_pass.append(name)

    raw_matrix, raw_stds = raw_dynamic_range(m10)
    powers = [float(np.var(base.intervention(c, i))) for c in TRAIN_CONDITIONS for i in EVAL]
    unique_ok, paired_ok, legacy_overlap = seed_integrity()

    gates = {
        "G0": bool(unique_ok and paired_ok and legacy_overlap == 0),
        "G1": bool(np.isfinite(raw_matrix).all() and np.all(raw_stds > 1e-5) and np.all(raw_stds < 50)),
        "G2": bool(min(powers) > 0.02),
        "G3": bool(primary["feasible"] and primary_rates.get("M0", 0.0) >= 0.80),
        "G4": bool(primary["feasible"] and primary_rates.get("M10", 1.0) <= 0.05),
        "G5": bool(primary["feasible"] and all(primary_rates.get(m, 1.0) <= 0.05 for m in ("M1", "M2", "M5"))),
        "G6": bool(len(consensus_pass) >= 3),
        "G7": bool(
            np.isfinite(X).all()
            and np.isfinite(mu).all()
            and np.isfinite(sd).all()
            and fitted_ok
            and len(feature_names) == AGG_FEATURE_COUNT
            and raw_matrix.shape[1] == RAW_FEATURE_COUNT
            and all(np.isfinite(v["threshold"]) for v in representation_results.values())
        ),
    }

    failed = [g for g, ok in gates.items() if not ok]
    decision = "PILOT_PASS_FREEZE_ALLOWED" if not failed else "STOP"

    result = {
        "version": VERSION,
        "decision": decision,
        "failed_gates": failed,
        "gates": gates,
        "primary_representation": PRIMARY,
        "primary_calibration": {
            k: primary[k]
            for k in ("threshold", "feasible", "calibration_tpr_M0", "calibration_worst_fp", "calibration_rates")
        },
        "primary_eval_rates": primary_rates,
        "representation_consensus_pass": consensus_pass,
        "representations": representation_results,
        "m10_optimization": {
            "objective": float(opt_score),
            "params": m10.__dict__,
            "grid_size": len(base.M10_GRID),
            "carry_over_check": "same 36-point grid and objective implementation imported from v0.3.2",
            "split": "indices 0-19 only; train interventions only",
        },
        "splits": {
            "m10_tuning": "0-19",
            "representation_fit": "20-39",
            "threshold_calibration": "40-59",
            "gate_evaluation": "60-79",
        },
        "feature_structure": {
            "raw_feature_count": RAW_FEATURE_COUNT,
            "aggregate_feature_count": len(feature_names),
            "aggregation": "feature-wise mean and std across multisine, impulse, PRBS",
            "aggregate_feature_names": feature_names,
        },
        "dynamic_range": {
            "raw_min_std": float(raw_stds.min()),
            "raw_max_std": float(raw_stds.max()),
        },
        "excitation": {"min_variance": float(min(powers))},
        "seed_integrity": {
            "audit_seed_unique": unique_ok,
            "paired_rng": paired_ok,
            "legacy_v0.3.2_overlap": legacy_overlap,
            "namespace": VERSION,
        },
        "rule": "Any Pilot gate failure => STOP; any change requires v0.3.2-r2 and fresh Pilot.",
    }

    (outdir / "pilot_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (outdir / "m10_frozen_from_fresh_tuning.json").write_text(json.dumps(m10.__dict__, indent=2) + "\n", encoding="utf-8")
    (outdir / "standardization.json").write_text(
        json.dumps({"mean": mu.tolist(), "std": sd.tolist(), "features": feature_names}, indent=2) + "\n",
        encoding="utf-8",
    )
    (outdir / "calibrated_thresholds.json").write_text(
        json.dumps(
            {
                name: {
                    "threshold": res["threshold"],
                    "feasible": res["feasible"],
                    "calibration_tpr_M0": res["calibration_tpr_M0"],
                    "calibration_worst_fp": res["calibration_worst_fp"],
                }
                for name, res in representation_results.items()
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    with (outdir / "representation_confusion.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["representation", "calibration_feasible"] + MODES)
        for name, res in representation_results.items():
            rates = res["evaluation_rates"]
            w.writerow([name, res["feasible"]] + [rates.get(mode, "") for mode in MODES])

    structure = {
        "entrypoint": "ph_v032_r1_pilot.py",
        "imports_core_from": "../v0.3.2/ph_v032_pilot.py",
        "core_reused": ["simulate", "intervention", "features", "raw_row", "M10_GRID", "optimize_m10"],
        "new_layers": [
            "fresh r1 RNG namespace",
            "70D intervention-set aggregation",
            "class-balanced representation fitting",
            "isolated threshold calibration",
            "fresh held-out G0-G7 evaluation",
        ],
        "artifacts": [
            "pilot_result.json",
            "m10_frozen_from_fresh_tuning.json",
            "standardization.json",
            "calibrated_thresholds.json",
            "representation_confusion.csv",
            "python_structure.json",
        ],
    }
    (outdir / "python_structure.json").write_text(json.dumps(structure, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2))
    return 0 if decision == "PILOT_PASS_FREEZE_ALLOWED" else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="artifacts/pilot")
    args = ap.parse_args()
    raise SystemExit(run_pilot(Path(args.outdir)))


if __name__ == "__main__":
    main()
