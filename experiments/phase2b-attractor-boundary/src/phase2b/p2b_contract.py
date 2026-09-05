from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_contract(path: str | Path) -> dict[str, Any]:
    contract = load_json(path)
    if contract["contract_id"] != "ATCT-PH-P2B-v0.1-IMPLEMENTATION-CONTRACT":
        raise ValueError("unexpected contract_id")
    if contract["contract_version"] != "1.0":
        raise ValueError("unexpected contract_version")
    if contract["numeric_contract"]["scalar_type"] != "IEEE-754 binary64":
        raise ValueError("binary64 contract required")
    return contract


def as_f64(x: Any) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64)
    if arr.dtype != np.float64:
        raise TypeError("float64 required")
    return arr


def a_kappa(contract: dict[str, Any], kappa: float) -> np.ndarray:
    h = float(contract["dynamics"]["h"])
    q0 = as_f64(contract["dynamics"]["Q_0"])
    omega = as_f64(contract["dynamics"]["Omega"])
    qk = as_f64(contract["dynamics"]["Q_K"])
    eye = np.eye(4, dtype=np.float64)
    return eye + h * (-q0 + omega - float(kappa) * qk)


def observation_matrix(contract: dict[str, Any]) -> np.ndarray:
    return as_f64(contract["observation_model"]["C_nominal"])


def profile_value(profile: str, n: int) -> float:
    if profile == "impulse":
        return 1.0 if n == 0 else 0.0
    if profile == "pulse8":
        return 1.0 if 0 <= n < 8 else 0.0
    if profile == "sine16x4":
        return math.sin(2.0 * math.pi * n / 16.0) if 0 <= n < 64 else 0.0
    if profile == "biphasic16":
        if 0 <= n < 8:
            return 1.0
        if 8 <= n < 16:
            return -1.0
        return 0.0
    raise KeyError(f"unknown profile: {profile}")


def cell_by_id(contract: dict[str, Any], cell_id: str) -> dict[str, Any]:
    for cell in contract["intervention_contract"]["matched_cells"]:
        if cell["cell_id"] == cell_id:
            return cell
    raise KeyError(cell_id)


def derive_master_seed(contract: dict[str, Any], stage: str, index: int) -> int:
    ns = contract["seed_namespace"]["master_namespace"]
    payload = f"{ns}|{stage}|{index}".encode("utf-8")
    word = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return word & 0x7FFFFFFFFFFFFFFF


def stream_key(
    contract: dict[str, Any],
    stage: str,
    seed_index: int,
    kappa_index: int,
    cell_id: str,
    stream_name: str,
) -> bytes:
    allowed = set(contract["seed_namespace"]["distinct_streams"])
    if stream_name not in allowed:
        raise ValueError(f"unregistered stream: {stream_name}")
    ns = contract["seed_namespace"]["master_namespace"]
    return (
        f"{ns}|{stage}|seed_index={seed_index}|kappa_index={kappa_index}"
        f"|cell={cell_id}|stream={stream_name}"
    ).encode("utf-8")


def uniform64(key: bytes, q: int) -> float:
    if q < 0:
        raise ValueError("q must be non-negative")
    digest = hashlib.sha256(key + f"|q={q}".encode("utf-8")).digest()
    word = int.from_bytes(digest[:8], "big")
    return (word + 0.5) / float(1 << 64)


def gaussian_stream(key: bytes, count: int) -> np.ndarray:
    if count < 0:
        raise ValueError("count must be non-negative")
    out = np.empty(count, dtype=np.float64)
    j = 0
    pair = 0
    while j < count:
        u1 = uniform64(key, 2 * pair)
        u2 = uniform64(key, 2 * pair + 1)
        radius = math.sqrt(-2.0 * math.log(u1))
        angle = 2.0 * math.pi * u2
        z0 = radius * math.cos(angle)
        z1 = radius * math.sin(angle)
        out[j] = z0
        j += 1
        if j < count:
            out[j] = z1
            j += 1
        pair += 1
    return out


def exact_uniform_integer(key: bytes, n: int) -> int:
    if n <= 0:
        raise ValueError("n must be positive")
    limit = ((1 << 64) // n) * n
    word_index = 0
    while True:
        digest = hashlib.sha256(key + f"|word={word_index}".encode("utf-8")).digest()
        word = int.from_bytes(digest[:8], "big")
        if word < limit:
            return word % n
        word_index += 1


def bootstrap_index(replicate: int, draw: int, n: int) -> int:
    key = f"ATCT-PH-P2B-v0.1|BOOT|rep={replicate}|draw={draw}".encode("utf-8")
    return exact_uniform_integer(key, n)


def null_swap_bit(seed_index: int, cell_id: str, repeat: int) -> int:
    key = (
        f"ATCT-PH-P2B-v0.1|NULLSWAP|seed={seed_index}"
        f"|cell={cell_id}|rep={repeat}"
    ).encode("utf-8")
    return hashlib.sha256(key).digest()[0] & 1


def git_blob_sha1_bytes(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def require_execution_authorization(
    experiment_root: str | Path,
    stage: str,
    expected_contract_blob_sha: str,
) -> None:
    root = Path(experiment_root)
    auth_path = root / "execution_authorization.json"
    if not auth_path.exists():
        raise PermissionError(
            "stochastic execution is locked: execution_authorization.json is absent"
        )
    auth = load_json(auth_path)
    if stage not in auth.get("authorized_stages", []):
        raise PermissionError(f"stage {stage!r} is not authorized")
    if auth.get("contract_git_blob_sha") != expected_contract_blob_sha:
        raise PermissionError("authorization does not match frozen contract")
    if stage == "CONF" and not auth.get("separate_confirmatory_freeze", False):
        raise PermissionError("CONF requires a separate confirmatory freeze")
