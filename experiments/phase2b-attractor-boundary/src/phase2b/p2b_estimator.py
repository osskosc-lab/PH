from __future__ import annotations

import math
from typing import Any

import numpy as np

from .p2b_contract import as_f64, bootstrap_index, null_swap_bit


def _pairwise_distances(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = as_f64(a)
    b = as_f64(b)
    if a.ndim != 2 or b.ndim != 2 or a.shape[1] != b.shape[1]:
        raise ValueError("a and b must be 2D with equal feature dimension")
    aa = np.sum(a * a, axis=1)[:, None]
    bb = np.sum(b * b, axis=1)[None, :]
    sq = aa + bb - 2.0 * (a @ b.T)
    return np.sqrt(np.maximum(sq, 0.0))


def normalized_energy_distance(x: np.ndarray, y: np.ndarray) -> float:
    x = as_f64(x)
    y = as_f64(y)
    if x.ndim != 2 or y.ndim != 2 or x.shape[1] != y.shape[1]:
        raise ValueError("x and y must be 2D with equal feature dimension")
    n, m = x.shape[0], y.shape[0]
    if n == 0 or m == 0:
        raise ValueError("empty sample")

    dxy = _pairwise_distances(x, y)
    dxx = _pairwise_distances(x, x)
    dyy = _pairwise_distances(y, y)

    ed = (
        2.0 * dxy.sum() / float(n * m)
        - dxx.sum() / float(n * n)
        - dyy.sum() / float(m * m)
    )
    ed_pos = max(float(ed), 0.0)
    pooled_total = dxx.sum() + dyy.sum() + 2.0 * dxy.sum()
    s_pool = float(pooled_total) / float((n + m) * (n + m))
    return ed_pos / (ed_pos + s_pool + 1e-12)


def frozen_even_median(values: list[float] | np.ndarray) -> float:
    v = np.sort(as_f64(values).reshape(-1))
    if v.size == 0:
        raise ValueError("empty values")
    mid = v.size // 2
    if v.size % 2:
        return float(v[mid])
    return float((v[mid - 1] + v[mid]) / 2.0)


def d_boundary(cell_samples: dict[str, dict[str, np.ndarray]]) -> tuple[float, dict[str, float]]:
    if len(cell_samples) != 16:
        raise ValueError("exactly 16 frozen cells are required")
    per_cell: dict[str, float] = {}
    for cell_id, sides in cell_samples.items():
        if set(sides) != {"in", "out"}:
            raise ValueError(f"{cell_id}: expected in/out samples")
        per_cell[cell_id] = normalized_energy_distance(sides["in"], sides["out"])
    return frozen_even_median(list(per_cell.values())), per_cell


def trend_statistics(kappa_values: list[float], d_values: list[float]) -> dict[str, float]:
    if len(kappa_values) != 5 or len(d_values) != 5:
        raise ValueError("the frozen kappa grid has five values")
    if any(kappa_values[i] <= kappa_values[i + 1] for i in range(4)):
        raise ValueError("kappa_values must be strictly descending")
    d = as_f64(d_values)
    increments = d[1:] - d[:-1]
    return {
        "V_mon": float(np.max(increments)),
        "Delta_D": float(d[0] - d[-1]),
        "D_min": float(d[-1]),
    }


def nearest_rank(values: np.ndarray, p: float) -> float:
    v = np.sort(as_f64(values).reshape(-1))
    if v.size == 0:
        raise ValueError("empty values")
    if not 0.0 < p <= 1.0:
        raise ValueError("p must be in (0,1]")
    one_based = int(math.ceil(p * v.size))
    return float(v[one_based - 1])


def bootstrap_resample_indices(replicate: int, n: int) -> np.ndarray:
    return np.asarray(
        [bootstrap_index(replicate, draw, n) for draw in range(n)],
        dtype=np.int64,
    )


def bootstrap_primary(
    signatures_by_kappa: dict[float, dict[str, dict[str, np.ndarray]]],
    repeats: int = 10000,
) -> dict[str, Any]:
    """Frozen paired-seed bootstrap. Do not call during P1."""
    kappa_grid = [1.0, 0.75, 0.50, 0.25, 0.0]
    if set(signatures_by_kappa) != set(kappa_grid):
        raise ValueError("missing frozen kappa values")

    first_k = signatures_by_kappa[1.0]
    first_cell = next(iter(first_k.values()))
    n = as_f64(first_cell["in"]).shape[0]
    if n <= 0:
        raise ValueError("no seeds")

    out = np.empty((repeats, 3), dtype=np.float64)
    for b in range(repeats):
        idx = bootstrap_resample_indices(b, n)
        dvals: list[float] = []
        for kappa in kappa_grid:
            cells: dict[str, dict[str, np.ndarray]] = {}
            for cell_id, sides in signatures_by_kappa[kappa].items():
                cells[cell_id] = {
                    "in": as_f64(sides["in"])[idx],
                    "out": as_f64(sides["out"])[idx],
                }
            dvals.append(d_boundary(cells)[0])
        stats = trend_statistics(kappa_grid, dvals)
        out[b] = [stats["V_mon"], stats["Delta_D"], stats["D_min"]]

    return {
        "V_mon": out[:, 0],
        "Delta_D": out[:, 1],
        "D_min": out[:, 2],
        "U95_V_mon": nearest_rank(out[:, 0], 0.975),
        "L95_Delta_D": nearest_rank(out[:, 1], 0.025),
        "U95_D_min": nearest_rank(out[:, 2], 0.975),
    }


def apply_paired_null_swap(
    inside: np.ndarray,
    outside: np.ndarray,
    seed_indices: list[int],
    cell_id: str,
    repeat: int,
) -> tuple[np.ndarray, np.ndarray]:
    inside = as_f64(inside).copy()
    outside = as_f64(outside).copy()
    if inside.shape != outside.shape:
        raise ValueError("paired arrays must have the same shape")
    if inside.shape[0] != len(seed_indices):
        raise ValueError("seed_indices length mismatch")
    for row, seed_index in enumerate(seed_indices):
        if null_swap_bit(seed_index, cell_id, repeat):
            tmp = inside[row].copy()
            inside[row] = outside[row]
            outside[row] = tmp
    return inside, outside


def fisher_information_conditional_gaussian(
    states: np.ndarray,
    sigma_obs: float = 0.03,
) -> np.ndarray:
    """Diagnostic Fisher matrix for theta=(c13,c24,log sigma_obs)."""
    states = as_f64(states)
    if states.ndim != 2 or states.shape[1] != 4:
        raise ValueError("states must have shape (N,4)")
    if sigma_obs <= 0:
        raise ValueError("sigma_obs must be positive")
    inv_var = 1.0 / (float(sigma_obs) ** 2)
    e1_sq = float(np.mean(states[:, 2] ** 2))
    e2_sq = float(np.mean(states[:, 3] ** 2))
    g = np.zeros((3, 3), dtype=np.float64)
    g[0, 0] = e1_sq * inv_var
    g[1, 1] = e2_sq * inv_var
    g[2, 2] = 4.0
    return g


def fisher_spectrum(g: np.ndarray) -> dict[str, Any]:
    g = as_f64(g)
    if g.shape != (3, 3):
        raise ValueError("g must have shape (3,3)")
    eigenvalues = np.linalg.eigvalsh(g)
    lam_max = float(np.max(eigenvalues))
    eps = 1e-6 * lam_max
    rank = int(np.sum(eigenvalues > eps)) if lam_max > 0 else 0
    return {
        "eigenvalues": eigenvalues,
        "lambda_min": float(np.min(eigenvalues)),
        "effective_rank_epsilon": eps,
        "effective_rank": rank,
    }


def finite_difference_susceptibility(
    axis_values: list[float],
    scores: np.ndarray,
    log_axis: bool = False,
) -> np.ndarray:
    x = as_f64(axis_values)
    y = as_f64(scores)
    if y.shape[0] != x.size:
        raise ValueError("axis length mismatch")
    if x.size < 2:
        raise ValueError("at least two axis values are required")
    z = np.log(x) if log_axis else x
    out = np.empty_like(y, dtype=np.float64)
    out[0] = np.abs((y[1] - y[0]) / (z[1] - z[0]))
    out[-1] = np.abs((y[-1] - y[-2]) / (z[-1] - z[-2]))
    for i in range(1, x.size - 1):
        out[i] = np.abs((y[i + 1] - y[i - 1]) / (z[i + 1] - z[i - 1]))
    return out
