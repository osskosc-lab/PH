from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import numpy as np

from .p2b_contract import (
    a_kappa,
    as_f64,
    cell_by_id,
    gaussian_stream,
    load_contract,
    observation_matrix,
    profile_value,
    require_execution_authorization,
    stream_key,
)

Side = Literal["in", "out"]


def _validate_noise(process_noise: np.ndarray, obs_noise: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    process_noise = as_f64(process_noise)
    obs_noise = as_f64(obs_noise)
    if process_noise.shape != (384, 4):
        raise ValueError("process_noise must have shape (384,4)")
    if obs_noise.shape != (385, 2):
        raise ValueError("obs_noise must have shape (385,2)")
    return process_noise, obs_noise


def simulate_with_noise(
    contract: dict[str, Any],
    kappa: float,
    target_vector: np.ndarray,
    profile: str,
    amplitude: float,
    process_noise: np.ndarray,
    obs_noise: np.ndarray,
    initial_state: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic simulator given explicit noise arrays.

    This function performs no RNG calls and is suitable for P1 deterministic tests.
    """
    process_noise, obs_noise = _validate_noise(process_noise, obs_noise)
    target = as_f64(target_vector).reshape(4)
    x0 = (
        as_f64(contract["dynamics"]["initial_state"]).reshape(4)
        if initial_state is None
        else as_f64(initial_state).reshape(4)
    )
    A = a_kappa(contract, kappa)
    C = observation_matrix(contract)

    x = np.empty((385, 4), dtype=np.float64)
    y = np.empty((385, 2), dtype=np.float64)
    x[0] = x0
    y[0] = C @ x[0] + obs_noise[0]

    for t in range(384):
        n = t - 256
        u = float(amplitude) * profile_value(profile, n)
        x[t + 1] = A @ x[t] + target * u + process_noise[t]
        y[t + 1] = C @ x[t + 1] + obs_noise[t + 1]

    return x, y


def simulate_oracle_clone_with_noise(
    contract: dict[str, Any],
    kappa: float,
    target_vector: np.ndarray,
    profile: str,
    amplitude: float,
    process_noise: np.ndarray,
    obs_noise: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """8D duplicated-latent Oracle Clone with exactly shared process noise."""
    process_noise, obs_noise = _validate_noise(process_noise, obs_noise)
    target = as_f64(target_vector).reshape(4)
    A = a_kappa(contract, kappa)
    C = observation_matrix(contract)
    x0 = as_f64(contract["dynamics"]["initial_state"]).reshape(4)

    z = np.empty((385, 8), dtype=np.float64)
    y = np.empty((385, 2), dtype=np.float64)
    z[0, :4] = x0
    z[0, 4:] = x0
    y[0] = C @ ((z[0, :4] + z[0, 4:]) / 2.0) + obs_noise[0]

    for t in range(384):
        n = t - 256
        u = float(amplitude) * profile_value(profile, n)
        xa = A @ z[t, :4] + target * u + process_noise[t]
        xb = A @ z[t, 4:] + target * u + process_noise[t]
        z[t + 1, :4] = xa
        z[t + 1, 4:] = xb
        y[t + 1] = C @ ((xa + xb) / 2.0) + obs_noise[t + 1]

    return z, y


def simulate_counterworld_with_noise(
    contract: dict[str, Any],
    kappa: float,
    cell: dict[str, Any],
    side: Side,
    process_noise: np.ndarray,
    obs_noise: np.ndarray,
    reporter_noise: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    process_noise, obs_noise = _validate_noise(process_noise, obs_noise)
    reporter_noise = as_f64(reporter_noise)
    if reporter_noise.shape != (384, 2):
        raise ValueError("reporter_noise must have shape (384,2)")

    target = as_f64(cell[f"{side}_target"]).reshape(4)
    A = a_kappa(contract, kappa)
    C = observation_matrix(contract)
    x = np.empty((385, 4), dtype=np.float64)
    r = np.empty((385, 2), dtype=np.float64)
    y = np.empty((385, 2), dtype=np.float64)
    x[0] = as_f64(contract["dynamics"]["initial_state"]).reshape(4)
    r[0] = 0.0
    y[0] = C @ x[0] + 0.60 * r[0] + obs_noise[0]

    pair_id = cell["pair_id"]
    sign = 1.0 if side == "in" else -1.0
    for t in range(384):
        n = t - 256
        u = float(cell["amplitude"]) * profile_value(cell["profile"], n)
        x[t + 1] = A @ x[t] + target * u + process_noise[t]

        drive = np.zeros(2, dtype=np.float64)
        if pair_id == "P1":
            drive[0] = sign * u
        elif pair_id == "P2":
            drive[1] = sign * u
        else:
            raise KeyError(pair_id)
        r[t + 1] = 0.65 * r[t] + 0.30 * drive + reporter_noise[t]
        y[t + 1] = C @ x[t + 1] + 0.60 * r[t + 1] + obs_noise[t + 1]

    return x, r, y


def trajectory_signature(y: np.ndarray, delta_t: int = 128) -> np.ndarray:
    y = as_f64(y)
    if y.shape != (385, 2):
        raise ValueError("y must have shape (385,2)")
    if delta_t not in (8, 16, 32, 64, 128):
        raise ValueError("delta_t must be one of the frozen DeltaT grid values")
    baseline = y[192:256].mean(axis=0)
    post = y[257 : 257 + delta_t] - baseline
    return post.reshape(-1) / np.sqrt(float(2 * delta_t))


def response_rms(y_do: np.ndarray, y_sham: np.ndarray) -> float:
    y_do = as_f64(y_do)
    y_sham = as_f64(y_sham)
    if y_do.shape != (385, 2) or y_sham.shape != (385, 2):
        raise ValueError("responses must have shape (385,2)")
    diff = y_do[257:385] - y_sham[257:385]
    return float(np.sqrt(np.mean(diff * diff)))


def d_k(x: np.ndarray) -> np.ndarray:
    x = as_f64(x)
    return np.sqrt(x[..., 0] ** 2 + x[..., 1] ** 2)


def tau_return(x: np.ndarray, threshold: float = 0.10, horizon: int = 128) -> int:
    x = as_f64(x)
    if x.ndim != 2 or x.shape[1] != 4:
        raise ValueError("x must have shape (T,4)")
    limit = min(horizon, x.shape[0] - 1)
    distances = d_k(x)
    for t in range(1, limit + 1):
        if distances[t] <= threshold:
            return t
    return 129


def exact_null_target(cell: dict[str, Any]) -> np.ndarray:
    inside = as_f64(cell["in_target"]).reshape(4)
    outside = as_f64(cell["out_target"]).reshape(4)
    return (inside + outside) / np.sqrt(2.0)


def _registered_noise(
    contract: dict[str, Any],
    stage: str,
    seed_index: int,
    kappa_index: int,
    cell_id: str,
) -> tuple[np.ndarray, np.ndarray]:
    pkey = stream_key(contract, stage, seed_index, kappa_index, cell_id, "PROCESS")
    okey = stream_key(contract, stage, seed_index, kappa_index, cell_id, "OBS")
    sigma_p = float(contract["dynamics"]["process_noise"]["sigma_process"])
    sigma_o = float(contract["observation_model"]["sigma_obs"])
    process = gaussian_stream(pkey, 384 * 4).reshape(384, 4) * sigma_p
    obs = gaussian_stream(okey, 385 * 2).reshape(385, 2) * sigma_o
    return process, obs


def simulate_registered(
    contract_path: str | Path,
    stage: str,
    seed_index: int,
    kappa_index: int,
    cell_id: str,
    side: Side,
    expected_contract_blob_sha: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Authorized stochastic runner.

    P1 intentionally cannot call this successfully because no execution
    authorization file is present on the branch.
    """
    contract_path = Path(contract_path)
    root = contract_path.parent
    require_execution_authorization(root, stage, expected_contract_blob_sha)
    contract = load_contract(contract_path)

    kappas = contract["dynamics"]["kappa_grid"]
    if not 0 <= kappa_index < len(kappas):
        raise IndexError("kappa_index out of range")
    cell = cell_by_id(contract, cell_id)
    process, obs = _registered_noise(
        contract, stage, seed_index, kappa_index, cell_id
    )
    target = as_f64(cell[f"{side}_target"])
    return simulate_with_noise(
        contract,
        float(kappas[kappa_index]),
        target,
        cell["profile"],
        float(cell["amplitude"]),
        process,
        obs,
    )
