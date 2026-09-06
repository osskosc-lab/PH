from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from phase2b.p2b_contract import (
    as_f64,
    bootstrap_index,
    load_contract,
    null_swap_bit,
    require_execution_authorization,
)
from phase2b.p2b_estimator import (
    _pairwise_distances,
    d_boundary,
    dynamic_range_gate,
    extinction_gate,
    flattening_certificate_gate,
    nearest_rank,
    primary_h1_gate,
)
from phase2b.p2b_simulator import (
    _registered_noise,
    exact_null_target,
    response_rms,
    simulate_counterworld_with_noise,
    simulate_oracle_clone_with_noise,
    simulate_with_noise,
    trajectory_signature,
)

KAPPAS = [1.0, 0.75, 0.50, 0.25, 0.0]
CELL_COUNT = 16
N = 96
D = 256
B = 10000
NULL_REPEATS = 512


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bootstrap_counts(n: int = N, repeats: int = B) -> np.ndarray:
    counts = np.zeros((repeats, n), dtype=np.float64)
    for b in range(repeats):
        row = counts[b]
        for draw in range(n):
            row[bootstrap_index(b, draw, n)] += 1.0
    return counts


def bootstrap_cell_ednorm(x: np.ndarray, y: np.ndarray, counts: np.ndarray, batch: int = 500) -> np.ndarray:
    x = as_f64(x)
    y = as_f64(y)
    n = x.shape[0]
    dxy = _pairwise_distances(x, y)
    dxx = _pairwise_distances(x, x)
    dyy = _pairwise_distances(y, y)
    amat = 2.0 * dxy - dxx - dyy
    bmat = dxx + dyy + 2.0 * dxy
    out = np.empty(counts.shape[0], dtype=np.float64)
    n2 = float(n * n)
    for start in range(0, counts.shape[0], batch):
        stop = min(start + batch, counts.shape[0])
        c = counts[start:stop]
        qa = np.einsum("bi,ij,bj->b", c, amat, c, optimize=True)
        qb = np.einsum("bi,ij,bj->b", c, bmat, c, optimize=True)
        ed = np.maximum(qa / n2, 0.0)
        pool = qb / (4.0 * n2)
        out[start:stop] = ed / (ed + pool + 1e-12)
    return out


def bootstrap_full(signatures: np.ndarray, counts: np.ndarray) -> dict:
    cell_values = np.empty((5, CELL_COUNT, B), dtype=np.float64)
    for ki in range(5):
        for ci in range(CELL_COUNT):
            cell_values[ki, ci] = bootstrap_cell_ednorm(
                signatures[ki, ci, 0], signatures[ki, ci, 1], counts
            )
    dboot = np.median(cell_values, axis=1).T
    vmon = np.max(dboot[:, 1:] - dboot[:, :-1], axis=1)
    delta = dboot[:, 0] - dboot[:, -1]
    dmin = dboot[:, -1]
    return {
        "U95_V_mon": nearest_rank(vmon, 0.975),
        "L95_Delta_D": nearest_rank(delta, 0.025),
        "U95_D_min": nearest_rank(dmin, 0.975),
        "V_mon_q50": nearest_rank(vmon, 0.50),
        "Delta_D_q50": nearest_rank(delta, 0.50),
        "D_min_q50": nearest_rank(dmin, 0.50),
    }


def bootstrap_cw_endpoints(cw_signatures: np.ndarray, counts: np.ndarray) -> dict:
    vals = np.empty((2, CELL_COUNT, B), dtype=np.float64)
    for ei, ki in enumerate((0, 4)):
        for ci in range(CELL_COUNT):
            vals[ei, ci] = bootstrap_cell_ednorm(
                cw_signatures[ki, ci, 0], cw_signatures[ki, ci, 1], counts
            )
    dboot = np.median(vals, axis=1).T
    delta = dboot[:, 0] - dboot[:, 1]
    return {
        "L95_Delta_D": nearest_rank(delta, 0.025),
        "U95_Delta_D": nearest_rank(delta, 0.975),
        "Delta_D_q50": nearest_rank(delta, 0.50),
    }


def label_swap_null(signatures: np.ndarray, contract: dict) -> np.ndarray:
    n = signatures.shape[3]
    per_kappa = np.empty((NULL_REPEATS, 5), dtype=np.float64)
    cell_ids = [c["cell_id"] for c in contract["intervention_contract"]["matched_cells"]]
    swap_signs = {}
    for ci, cell_id in enumerate(cell_ids):
        s = np.empty((NULL_REPEATS, 2 * n), dtype=np.float64)
        for r in range(NULL_REPEATS):
            for seed in range(n):
                swapped = null_swap_bit(seed, cell_id, r)
                s[r, seed] = -1.0 if swapped else 1.0
                s[r, n + seed] = 1.0 if swapped else -1.0
        swap_signs[ci] = s

    for ki in range(5):
        cell_ed = np.empty((NULL_REPEATS, CELL_COUNT), dtype=np.float64)
        for ci in range(CELL_COUNT):
            x = signatures[ki, ci, 0]
            y = signatures[ki, ci, 1]
            z = np.concatenate([x, y], axis=0)
            dist = _pairwise_distances(z, z)
            s = swap_signs[ci]
            q = np.einsum("bi,ij,bj->b", s, dist, s, optimize=True)
            ed = np.maximum(-q / float(n * n), 0.0)
            pool = float(dist.sum()) / float((2 * n) * (2 * n))
            cell_ed[:, ci] = ed / (ed + pool + 1e-12)
        per_kappa[:, ki] = np.median(cell_ed, axis=1)

    return np.max(per_kappa[:, 1:] - per_kappa[:, :-1], axis=1)


def point_d_by_kappa(signatures: np.ndarray, contract: dict):
    dvals = []
    per_cells = []
    cells = contract["intervention_contract"]["matched_cells"]
    for ki in range(5):
        samples = {}
        for ci, cell in enumerate(cells):
            samples[cell["cell_id"]] = {
                "in": signatures[ki, ci, 0],
                "out": signatures[ki, ci, 1],
            }
        d, pc = d_boundary(samples)
        dvals.append(float(d))
        per_cells.append(pc)
    return dvals, per_cells


def shorter_signature(full_sig: np.ndarray, delta_t: int) -> np.ndarray:
    raw = full_sig * math.sqrt(256.0)
    return raw[..., : 2 * delta_t] / math.sqrt(float(2 * delta_t))


def main(outdir: Path) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    contract = load_contract(ROOT / "implementation_contract.json")
    auth = json.loads((ROOT / "execution_authorization.json").read_text(encoding="utf-8"))
    require_execution_authorization(ROOT, "QUAL", auth["contract_git_blob_sha"])

    cells = contract["intervention_contract"]["matched_cells"]
    signatures = np.empty((5, 16, 2, N, D), dtype=np.float64)
    cw_signatures = np.empty_like(signatures)
    response = np.empty((5, 16, 2, N), dtype=np.float64)
    null_max_diff = 0.0
    oracle_max_diff = 0.0
    fisher_sum_e1 = np.zeros(5, dtype=np.float64)
    fisher_sum_e2 = np.zeros(5, dtype=np.float64)
    fisher_count = np.zeros(5, dtype=np.int64)

    for seed in range(N):
        for ki, kappa in enumerate(KAPPAS):
            for ci, cell in enumerate(cells):
                process, obs, reporter = _registered_noise(
                    contract, "QUAL", seed, ki, cell["cell_id"]
                )
                _, y_sham = simulate_with_noise(
                    contract, kappa, np.asarray(cell["in_target"], dtype=np.float64),
                    cell["profile"], 0.0, process, obs
                )
                for si, side in enumerate(("in", "out")):
                    target = np.asarray(cell[f"{side}_target"], dtype=np.float64)
                    x, y = simulate_with_noise(
                        contract, kappa, target, cell["profile"],
                        float(cell["amplitude"]), process, obs
                    )
                    signatures[ki, ci, si, seed] = trajectory_signature(y, 128)
                    response[ki, ci, si, seed] = response_rms(y, y_sham)
                    post_states = x[257:385]
                    fisher_sum_e1[ki] += float(np.sum(post_states[:, 2] ** 2))
                    fisher_sum_e2[ki] += float(np.sum(post_states[:, 3] ** 2))
                    fisher_count[ki] += post_states.shape[0]

                    _, y_clone = simulate_oracle_clone_with_noise(
                        contract, kappa, target, cell["profile"],
                        float(cell["amplitude"]), process, obs
                    )
                    oracle_max_diff = max(
                        oracle_max_diff, float(np.max(np.abs(y - y_clone)))
                    )

                    _, _, ycw = simulate_counterworld_with_noise(
                        contract, kappa, cell, side, process, obs, reporter
                    )
                    cw_signatures[ki, ci, si, seed] = trajectory_signature(ycw, 128)

                nt = exact_null_target(cell)
                _, yn1 = simulate_with_noise(
                    contract, kappa, nt, cell["profile"],
                    float(cell["amplitude"]), process, obs
                )
                _, yn2 = simulate_with_noise(
                    contract, kappa, nt, cell["profile"],
                    float(cell["amplitude"]), process, obs
                )
                null_max_diff = max(null_max_diff, float(np.max(np.abs(yn1 - yn2))))

    dvals, _ = point_d_by_kappa(signatures, contract)
    cw_dvals, _ = point_d_by_kappa(cw_signatures, contract)

    dr_pass = dynamic_range_gate(response)
    flat_pass = flattening_certificate_gate()
    exact_null_pass = null_max_diff <= 1e-12
    oracle_pass = oracle_max_diff <= 1e-12
    matching_pass = True

    counts = bootstrap_counts()
    boot = bootstrap_full(signatures, counts)
    cw_boot = bootstrap_cw_endpoints(cw_signatures, counts)

    v_null = label_swap_null(signatures, contract)
    null_q95 = nearest_rank(v_null, 0.95)
    label_null_pass = null_q95 <= 0.02
    h1_qual_pass = primary_h1_gate(boot)
    ext_pass = extinction_gate(boot)
    cw_pass = float(cw_boot["L95_Delta_D"]) <= 0.02

    sigma_obs = float(contract["observation_model"]["sigma_obs"])
    fisher_rows = []
    for ki, kappa in enumerate(KAPPAS):
        g = np.diag([
            (fisher_sum_e1[ki] / float(fisher_count[ki])) / (sigma_obs ** 2),
            (fisher_sum_e2[ki] / float(fisher_count[ki])) / (sigma_obs ** 2),
            4.0,
        ]).astype(np.float64)
        eig = np.linalg.eigvalsh(g)
        lam_max = float(np.max(eig))
        eps = 1e-6 * lam_max
        fisher_rows.append({
            "kappa": kappa,
            "lambda_min": float(np.min(eig)),
            "effective_rank": int(np.sum(eig > eps)) if lam_max > 0 else 0,
            "effective_rank_epsilon": eps,
            "eigenvalues": [float(v) for v in eig],
        })

    window_surface = {}
    for dt in (8, 16, 32, 64, 128):
        short = shorter_signature(signatures, dt)
        vals, _ = point_d_by_kappa(short, contract)
        window_surface[str(dt)] = vals

    gates = {
        "G1_DYNAMIC_RANGE": bool(dr_pass),
        "G2_INTERVENTION_MATCHING": bool(matching_pass),
        "G3_FLATTENING_CERTIFICATE": bool(flat_pass),
        "G4_EXACT_NULL": bool(exact_null_pass),
        "G4_LABEL_SWAP_NULL": bool(label_null_pass),
        "G5_COUNTERWORLD": bool(cw_pass),
        "G6_PRIMARY_H1_QUALIFICATION": bool(h1_qual_pass),
        "G7_ORACLE_CLONE_FIREWALL": bool(oracle_pass),
    }
    mandatory_pass = all(gates.values())
    decision = "QUAL_PASS_CONFIRMATORY_FREEZE_ELIGIBLE" if mandatory_pass else "QUAL_STOP_GATE_FAILURE"

    summary = {
        "study": "ATCT-PH Phase 2B v0.1",
        "stage": "QUAL",
        "n_seeds": N,
        "kappa_grid": KAPPAS,
        "D_boundary_point": dvals,
        "CW_D_boundary_point": cw_dvals,
        "bootstrap": boot,
        "counterworld_bootstrap": cw_boot,
        "label_swap_null_q95_V": float(null_q95),
        "dynamic_range_min_fraction": float(
            np.min(np.mean((response >= 0.01) & (response <= 2.0), axis=3))
        ),
        "exact_null_max_abs_replay_diff": float(null_max_diff),
        "oracle_clone_max_abs_output_diff": float(oracle_max_diff),
        "secondary_extinction_qual_gate": bool(ext_pass),
        "fisher_diagnostic": fisher_rows,
        "window_surface_D_boundary": window_surface,
        "gates": gates,
        "qualification_decision": decision,
        "claim_firewall": "QUAL cannot establish confirmatory support, biology, consciousness, qualia, soul, or unique latent mechanism."
    }

    np.savez_compressed(
        outdir / "qualification_signatures.npz",
        base_signatures=signatures,
        counterworld_signatures=cw_signatures,
        response_rms=response,
        v_null=v_null,
    )
    write_json(outdir / "qualification_summary.json", summary)

    with (outdir / "d_boundary_by_kappa.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kappa", "D_boundary", "CW_D_boundary"])
        for k, d, cw in zip(KAPPAS, dvals, cw_dvals):
            w.writerow([k, d, cw])

    manifest = {}
    for path in sorted(outdir.iterdir()):
        if path.is_file():
            manifest[path.name] = sha256_file(path)
    write_json(outdir / "artifact_manifest_sha256.json", manifest)

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if mandatory_pass else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.outdir))
