from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

VERSION = "PH-v0.3.2-r1-confirmatory"
N = 256
CORE_CONDITIONS = ["multisine", "impulse", "PRBS"]
OOD_CONDITIONS = ["chirp", "unseen_frequencies", "unseen_amplitudes", "burst", "reversed_sequence"]
PRIMARY = "balanced_logistic"
PRIMARY_NEGATIVES = ("M10", "M1", "M2", "M5")
Z95 = 1.959963984540054

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
R1_PATH = HERE.parent / "v0.3.2-r1" / "ph_v032_r1_pilot.py"
FREEZE_PATH = HERE / "freeze.json"

_spec = importlib.util.spec_from_file_location("ph_v032_r1_frozen", R1_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load frozen r1 implementation: {R1_PATH}")
r1 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = r1
_spec.loader.exec_module(r1)

MODES = list(r1.MODES)


def h32(token: str) -> int:
    return int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big")


def confirmatory_pair_seed(condition: str, index: int) -> int:
    return h32(f"PH-v0.3.2-r1|confirmatory|paired|{condition}|{index}")


def confirmatory_audit_seed(mode: str, condition: str, index: int) -> int:
    return h32(f"PH-v0.3.2-r1|confirmatory|{mode}|{condition}|{index}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def load_freeze() -> dict:
    return json.loads(FREEZE_PATH.read_text(encoding="utf-8"))


def verify_source_blobs(freeze: dict) -> None:
    for rel, expected in freeze["source_git_blobs"].items():
        got = git_blob_sha1(ROOT / rel)
        if got != expected:
            raise RuntimeError(f"freeze source mismatch: {rel}: {got} != {expected}")


def exact_json_sha(payload) -> str:
    return sha256_bytes((json.dumps(payload, indent=2) + "\n").encode("utf-8"))


def reconstruct_pilot_freeze(freeze: dict):
    # Reconstruct only the already-frozen Pilot fit. No selection is permitted here.
    r1.base.VERSION = r1.VERSION
    r1.base.N_DEFAULT = r1.N

    opt_score, selected = r1.base.optimize_m10()
    expected_m10 = freeze["frozen_m10"]
    got_m10 = selected.__dict__
    if got_m10 != expected_m10:
        raise RuntimeError(f"M10 reconstruction mismatch: {got_m10} != {expected_m10}")
    if not math.isclose(float(opt_score), float(freeze["pilot_m10_objective"]), rel_tol=1e-12, abs_tol=1e-12):
        raise RuntimeError("M10 objective reconstruction mismatch")
    if exact_json_sha(got_m10) != freeze["pilot_artifact_members"]["m10_frozen_from_fresh_tuning.json"]:
        raise RuntimeError("M10 artifact member hash mismatch")

    X, rows, feature_names = r1.build_aggregate_dataset(selected)
    y = np.array([1 if mode == "M0" else 0 for mode, _ in rows], dtype=int)
    fit_mask = r1.split_mask(rows, r1.FIT)
    cal_mask = r1.split_mask(rows, r1.CAL)

    mu, sd = r1.fit_standard(X[fit_mask])
    standardization_payload = {"mean": mu.tolist(), "std": sd.tolist(), "features": feature_names}
    if exact_json_sha(standardization_payload) != freeze["pilot_artifact_members"]["standardization.json"]:
        raise RuntimeError("standardization artifact member hash mismatch")

    Z = (X - mu) / sd
    cal_rows = [row for row, keep in zip(rows, cal_mask) if keep]
    models = {}
    threshold_payload = {}

    for name, cls in r1.REPRESENTATIONS.items():
        model = cls().fit(Z[fit_mask], y[fit_mask])
        cal_scores = np.asarray(model.score(Z[cal_mask]), dtype=float)
        calibration = r1.calibrate_threshold(cal_scores, cal_rows)
        frozen = freeze["thresholds"][name]
        if not math.isclose(calibration["threshold"], frozen["threshold"], rel_tol=1e-12, abs_tol=1e-12):
            raise RuntimeError(f"threshold reconstruction mismatch: {name}")
        if bool(calibration["feasible"]) != bool(frozen["feasible"]):
            raise RuntimeError(f"feasibility reconstruction mismatch: {name}")
        if not math.isclose(calibration["calibration_tpr_M0"], frozen["calibration_tpr_M0"], rel_tol=1e-12, abs_tol=1e-12):
            raise RuntimeError(f"calibration TPR mismatch: {name}")
        if not math.isclose(calibration["calibration_worst_fp"], frozen["calibration_worst_fp"], rel_tol=1e-12, abs_tol=1e-12):
            raise RuntimeError(f"calibration FP mismatch: {name}")
        threshold_payload[name] = dict(frozen)
        models[name] = model

    if exact_json_sha(threshold_payload) != freeze["pilot_artifact_members"]["calibrated_thresholds.json"]:
        raise RuntimeError("threshold artifact member hash mismatch")

    return selected, mu, sd, feature_names, models


def install_confirmatory_rng() -> None:
    r1.base.VERSION = VERSION
    r1.base.N_DEFAULT = N
    r1.base.pair_seed = confirmatory_pair_seed
    r1.base.audit_seed = confirmatory_audit_seed


def aggregate_conditions(mode: str, index: int, m10, conditions: list[str]) -> tuple[np.ndarray, list[str]]:
    per_condition = []
    raw_names = None
    for condition in conditions:
        row, raw_names = r1.base.raw_row(mode, condition, index, m10)
        per_condition.append(row)
    A = np.vstack(per_condition)
    if raw_names is None:
        raise RuntimeError("raw feature names missing")
    names = [f"mean::{x}" for x in raw_names] + [f"std::{x}" for x in raw_names]
    return np.concatenate([A.mean(axis=0), A.std(axis=0)]), names


def build_dataset(m10, conditions: list[str]):
    X = []
    rows = []
    names = None
    for mode in MODES:
        for index in range(N):
            x, names = aggregate_conditions(mode, index, m10, conditions)
            X.append(x)
            rows.append((mode, index))
    return np.vstack(X), rows, names


def wilson(k: int, n: int) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")
    p = k / n
    z2 = Z95 * Z95
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half = Z95 * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n) / denom
    return max(0.0, center - half), min(1.0, center + half)


def mode_stats(scores: np.ndarray, rows, threshold: float) -> dict:
    pred = np.asarray(scores) >= threshold
    out = {}
    for mode in MODES:
        mask = np.array([m == mode for m, _ in rows], dtype=bool)
        n = int(mask.sum())
        k = int(pred[mask].sum())
        lo, hi = wilson(k, n)
        out[mode] = {"k": k, "n": n, "rate": k / n, "lcb95": lo, "ucb95": hi}
    return out


def dis_diagnostic(Z: np.ndarray, rows) -> float:
    m0 = Z[np.array([m == "M0" for m, _ in rows])]
    m10 = Z[np.array([m == "M10" for m, _ in rows])]
    d_between = float(np.linalg.norm(m0.mean(axis=0) - m10.mean(axis=0)))
    d_within = float(np.sqrt(np.mean(np.sum((m0 - m0.mean(axis=0)) ** 2, axis=1))))
    return d_between / max(d_within, 1e-12)


def seed_integrity() -> dict:
    pilot = set()
    confirm = set()
    paired = {}
    paired_ok = True
    for mode in MODES:
        for condition in CORE_CONDITIONS + OOD_CONDITIONS:
            for index in range(N):
                confirm.add(confirmatory_audit_seed(mode, condition, index))
                if index < r1.N and condition in r1.TRAIN_CONDITIONS:
                    pilot.add(h32(f"PH-v0.3.2-r1|pilot|{mode}|{condition}|{index}"))
                key = (condition, index)
                ps = confirmatory_pair_seed(condition, index)
                if key in paired and paired[key] != ps:
                    paired_ok = False
                paired[key] = ps
    return {
        "confirmatory_unique": len(confirm) == len(MODES) * len(CORE_CONDITIONS + OOD_CONDITIONS) * N,
        "pilot_overlap": len(confirm & pilot),
        "paired_rng": paired_ok,
    }


def family_pass(stats_core: dict, stats_ood: dict) -> bool:
    return bool(
        stats_core["M0"]["lcb95"] > 0.80
        and stats_core["M10"]["ucb95"] < 0.05
        and stats_ood["M0"]["lcb95"] > 0.80
        and stats_ood["M10"]["ucb95"] < 0.05
    )


def final_decision(gates: dict, reps: dict, technical_ok: bool) -> str:
    if not technical_ok or not gates["C0_freeze_integrity"] or not gates["C8_numerical_seed_integrity"]:
        return "INCONCLUSIVE"
    if all(gates.values()):
        return "IDENTIFIABLE"

    primary_core = reps[PRIMARY]["core"]
    primary_ood = reps[PRIMARY]["ood"]
    core_ok = (
        primary_core["M0"]["lcb95"] > 0.80
        and primary_core["M10"]["ucb95"] < 0.05
        and all(primary_core[m]["ucb95"] < 0.05 for m in ("M1", "M2", "M5"))
    )
    ood_ok = (
        primary_ood["M0"]["lcb95"] > 0.80
        and primary_ood["M10"]["ucb95"] < 0.05
        and all(primary_ood[m]["ucb95"] < 0.05 for m in ("M1", "M2", "M5"))
    )
    fail_same_direction = sum(
        not family_pass(result["core"], result["ood"])
        for result in reps.values()
    ) >= 3

    if not core_ok and fail_same_direction:
        return "NON_IDENTIFIABLE"
    if core_ok and not ood_ok:
        return "FRAGILE_IDENTIFIABLE"
    if core_ok and not gates["C7_representation_independence"]:
        return "FRAGILE_IDENTIFIABLE"
    return "NON_IDENTIFIABLE" if fail_same_direction else "FRAGILE_IDENTIFIABLE"


def run_confirmatory(outdir: Path) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    freeze = load_freeze()
    verify_source_blobs(freeze)
    m10, mu, sd, feature_names, models = reconstruct_pilot_freeze(freeze)

    install_confirmatory_rng()
    seed_audit = seed_integrity()

    X_core, rows_core, names_core = build_dataset(m10, CORE_CONDITIONS)
    X_ood, rows_ood, names_ood = build_dataset(m10, OOD_CONDITIONS)
    if names_core != feature_names or names_ood != feature_names:
        raise RuntimeError("confirmatory feature ordering differs from frozen Pilot")

    Z_core = (X_core - mu) / sd
    Z_ood = (X_ood - mu) / sd

    representations = {}
    consensus = []
    for name, model in models.items():
        threshold = freeze["thresholds"][name]["threshold"]
        core_scores = np.asarray(model.score(Z_core), dtype=float)
        ood_scores = np.asarray(model.score(Z_ood), dtype=float)
        core_stats = mode_stats(core_scores, rows_core, threshold)
        ood_stats = mode_stats(ood_scores, rows_ood, threshold)
        ok = family_pass(core_stats, ood_stats)
        if ok:
            consensus.append(name)
        representations[name] = {
            "threshold": threshold,
            "core": core_stats,
            "ood": ood_stats,
            "confirmatory_family_pass": ok,
        }

    primary_core = representations[PRIMARY]["core"]
    primary_ood = representations[PRIMARY]["ood"]

    numerical_ok = bool(
        np.isfinite(X_core).all()
        and np.isfinite(X_ood).all()
        and np.isfinite(Z_core).all()
        and np.isfinite(Z_ood).all()
        and seed_audit["confirmatory_unique"]
        and seed_audit["paired_rng"]
        and seed_audit["pilot_overlap"] == 0
    )

    gates = {
        "C0_freeze_integrity": True,
        "C1_core_positive": bool(primary_core["M0"]["lcb95"] > 0.80),
        "C2_core_M10_specificity": bool(primary_core["M10"]["ucb95"] < 0.05),
        "C3_core_basic_specificity": bool(all(primary_core[m]["ucb95"] < 0.05 for m in ("M1", "M2", "M5"))),
        "C4_OOD_positive": bool(primary_ood["M0"]["lcb95"] > 0.80),
        "C5_OOD_M10_specificity": bool(primary_ood["M10"]["ucb95"] < 0.05),
        "C6_OOD_basic_specificity": bool(all(primary_ood[m]["ucb95"] < 0.05 for m in ("M1", "M2", "M5"))),
        "C7_representation_independence": bool(len(consensus) >= 3),
        "C8_numerical_seed_integrity": numerical_ok,
    }

    decision = final_decision(gates, representations, numerical_ok)
    result = {
        "version": VERSION,
        "decision": decision,
        "N_per_mode": N,
        "primary_representation": PRIMARY,
        "gates": gates,
        "failed_gates": [k for k, ok in gates.items() if not ok],
        "representation_consensus_pass": consensus,
        "representations": representations,
        "diagnostics": {
            "DIS_core": dis_diagnostic(Z_core, rows_core),
            "DIS_OOD": dis_diagnostic(Z_ood, rows_ood),
        },
        "seed_integrity": seed_audit,
        "frozen": {
            "pilot_artifact_zip_sha256": freeze["pilot_artifact_zip_sha256"],
            "pilot_artifact_id": freeze["pilot_artifact_id"],
            "M10": freeze["frozen_m10"],
            "thresholds": {k: v["threshold"] for k, v in freeze["thresholds"].items()},
            "standardization_member_sha256": freeze["pilot_artifact_members"]["standardization.json"],
        },
        "rule": "No post-confirmatory estimator, threshold, M10, feature, or seed changes are permitted for this version.",
    }

    (outdir / "confirmatory_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    with (outdir / "confirmatory_primary_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["set", "mode", "k", "n", "rate", "lcb95", "ucb95"])
        for set_name, stats in (("core", primary_core), ("ood", primary_ood)):
            for mode in MODES:
                rec = stats[mode]
                w.writerow([set_name, mode, rec["k"], rec["n"], rec["rate"], rec["lcb95"], rec["ucb95"]])

    with (outdir / "representation_confirmatory.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["representation", "set", "TPR_M0", "M0_LCB95", "FP_M10", "M10_UCB95", "family_pass"])
        for name, rec in representations.items():
            for set_name in ("core", "ood"):
                st = rec[set_name]
                w.writerow([
                    name, set_name,
                    st["M0"]["rate"], st["M0"]["lcb95"],
                    st["M10"]["rate"], st["M10"]["ucb95"],
                    rec["confirmatory_family_pass"],
                ])

    print(json.dumps(result, indent=2))
    return 0 if decision in ("IDENTIFIABLE", "FRAGILE_IDENTIFIABLE", "NON_IDENTIFIABLE") else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="experiments/v0.3.2-r1-confirmatory/artifacts/confirmatory")
    args = ap.parse_args()
    raise SystemExit(run_confirmatory(Path(args.outdir)))


if __name__ == "__main__":
    main()
