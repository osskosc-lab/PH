from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


VERSION = "PH-v0.4-Phase0A"
N_PILOT = 96
ACCESS_CAL = tuple(range(0, 24))
MIMIC_FIT = tuple(range(24, 48))
EVALUATION = tuple(range(48, 96))
T = 192
LOCAL_START = 48
LOCAL_END = 160
PROFILES = ("impulse", "finite_pulse", "PRBS", "multisine")
AMPLITUDES = (0.5, 1.0)
MODELS = ("M0", "M11-C", "M11-U", "M10", "M1", "M2", "M_CD", "M_NULL")
NEGATIVE_MODELS = ("M1", "M2", "M_NULL")
EPS = 1e-12

HERE = Path(__file__).resolve().parent


def h32(token: str) -> int:
    return int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4], "big")


def rng_for(*parts: object) -> np.random.Generator:
    return np.random.default_rng(h32("|".join(map(str, parts))))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def target_label_map(index: int) -> dict[str, str]:
    """Randomize internal parameter-slot labels without using model identity."""
    swap = bool(h32(f"{VERSION}|target-label|{index}") % 2)
    if swap:
        return {"V": "slot_B", "O": "slot_A"}
    return {"V": "slot_A", "O": "slot_B"}


def old_namespace_seed_tokens() -> list[str]:
    namespaces = (
        "PH-v0.2",
        "PH-v0.2.1",
        "PH-v0.3",
        "PH-v0.3.1",
        "PH-v0.3.2",
        "PH-v0.3.2-r1",
        "PH-v0.3.3",
        "PH-v0.3.3-r1",
    )
    return [f"{ns}|pilot|{model}|{profile}|{index}" for ns in namespaces for model in MODELS for profile in PROFILES for index in range(N_PILOT)]


def seed_audit() -> dict:
    tokens = [f"{VERSION}|pilot|{model}|{profile}|{index}" for model in MODELS for profile in PROFILES for index in range(N_PILOT)]
    seeds = [h32(token) for token in tokens]
    old_seeds = {h32(token) for token in old_namespace_seed_tokens()}
    return {
        "namespace": VERSION,
        "token_rule": "sha256(VERSION|pilot|model|profile|index)[:4]",
        "count": len(seeds),
        "unique": len(seeds) == len(set(seeds)),
        "legacy_overlap": len(set(seeds) & old_seeds),
        "legacy_namespaces_checked": [
            "PH-v0.2",
            "PH-v0.2.1",
            "PH-v0.3",
            "PH-v0.3.1",
            "PH-v0.3.2",
            "PH-v0.3.2-r1",
            "PH-v0.3.3",
            "PH-v0.3.3-r1",
        ],
        "target_label_map_hash": sha256_bytes(
            json.dumps({str(i): target_label_map(i) for i in range(N_PILOT)}, sort_keys=True).encode("utf-8")
        ),
        "model_independent_target_rule": True,
    }


def external_inputs(profile: str, index: int) -> tuple[np.ndarray, np.ndarray]:
    """Create paired Fast/Slow external inputs; no model state is consulted."""
    t = np.arange(T, dtype=float)
    r = rng_for(VERSION, "external", profile, index)
    if profile == "impulse":
        fast = np.zeros(T)
        fast[18:22] = 1.1
        fast[86:89] = -0.75
        slow = 0.45 * np.exp(-((t - 62.0) / 24.0) ** 2)
    elif profile == "finite_pulse":
        fast = np.zeros(T)
        fast[24:52] = 0.65
        fast[112:132] = -0.45
        slow = np.zeros(T)
        slow[35:115] = 0.35
    elif profile == "PRBS":
        fast = 0.48 * np.repeat(r.choice([-1.0, 1.0], size=math.ceil(T / 6)), 6)[:T]
        slow = np.convolve(fast, np.ones(18) / 18.0, mode="same")
    elif profile == "multisine":
        fast = 0.38 * np.sin(2 * np.pi * 0.105 * t) + 0.24 * np.sin(2 * np.pi * 0.145 * t + 0.4)
        slow = 0.52 * np.sin(2 * np.pi * 0.018 * t + 0.2) + 0.18 * np.sin(2 * np.pi * 0.031 * t + 0.7)
    else:
        raise ValueError(profile)
    return fast.astype(float), slow.astype(float)


def local_wave(profile: str, index: int, amplitude: float) -> np.ndarray:
    """Fixed A1 local waveform; its side is supplied separately."""
    t = np.arange(T, dtype=float)
    r = rng_for(VERSION, "local", profile, index)
    j = np.zeros(T)
    if profile == "impulse":
        j[LOCAL_START : LOCAL_START + 4] = amplitude
        j[LOCAL_START + 58 : LOCAL_START + 61] = -0.60 * amplitude
    elif profile == "finite_pulse":
        j[LOCAL_START + 4 : LOCAL_START + 28] = amplitude
        j[LOCAL_START + 76 : LOCAL_START + 92] = -0.55 * amplitude
    elif profile == "PRBS":
        blocks = r.choice([-1.0, 1.0], size=math.ceil((LOCAL_END - LOCAL_START) / 6))
        j[LOCAL_START:LOCAL_END] = amplitude * np.repeat(blocks, 6)[: LOCAL_END - LOCAL_START]
    elif profile == "multisine":
        w = t - LOCAL_START
        mask = (w >= 0) & (w < LOCAL_END - LOCAL_START)
        j[mask] = amplitude * (
            0.56 * np.sin(2 * np.pi * 0.071 * w[mask] + 0.3)
            + 0.34 * np.sin(2 * np.pi * 0.119 * w[mask] + 1.1)
        )
    else:
        raise ValueError(profile)
    return j


def noise(profile: str, index: int, tag: str, scale: float) -> np.ndarray:
    return rng_for(VERSION, "noise", profile, index, tag).normal(0.0, scale, T)


def routed_local(profile: str, index: int, side: str | None, amplitude: float) -> tuple[np.ndarray, np.ndarray]:
    j = local_wave(profile, index, amplitude) if side is not None else np.zeros(T)
    return (j.copy(), np.zeros(T)) if side == "V" else (np.zeros(T), j.copy()) if side == "O" else (np.zeros(T), np.zeros(T))


def simulate_m0(profile: str, index: int, side: str | None, amplitude: float) -> tuple[np.ndarray, np.ndarray]:
    fast, slow = external_inputs(profile, index)
    jv, jo = routed_local(profile, index, side, amplitude)
    labels = target_label_map(index)
    slot_gain = {"slot_A": 0.36, "slot_B": 0.32}
    g_v, g_o = slot_gain[labels["V"]], slot_gain[labels["O"]]
    nb = noise(profile, index, "shared_boundary", 0.025)
    nv = noise(profile, index, "V", 0.018)
    no = noise(profile, index, "O", 0.018)
    b = np.zeros(T)
    v = np.zeros(T)
    o = np.zeros(T)
    for t in range(1, T):
        b[t] = 0.82 * b[t - 1] + 0.42 * fast[t - 1] + 0.22 * slow[t - 1] + g_v * jv[t - 1] + g_o * jo[t - 1] - 0.025 * b[t - 1] ** 3 + nb[t]
        v[t] = 0.70 * v[t - 1] + 0.58 * np.tanh(b[t]) + 0.10 * fast[t] + nv[t]
        o[t] = 0.67 * o[t - 1] + 0.54 * np.tanh(b[t]) + 0.10 * slow[t] + no[t]
    return v, o


@dataclass(frozen=True)
class M11Params:
    a_v: float
    a_o: float
    b_fv: float
    b_fo: float
    b_sv: float
    b_so: float
    g_v: float
    g_o: float
    c_v_to_o: float
    c_o_to_v: float
    rho_shared: float
    k_v_from_o: float
    k_o_from_v: float
    q_v: float
    q_o: float


def default_m11_params(c_max: float, rho_max: float, kappa_max: float) -> M11Params:
    return M11Params(
        0.82,
        0.79,
        0.42,
        0.38,
        0.22,
        0.25,
        0.36,
        0.32,
        c_max,
        c_max,
        rho_max,
        kappa_max,
        kappa_max,
        0.58,
        0.54,
    )


def simulate_m11_c(profile: str, index: int, side: str | None, amplitude: float, params: M11Params) -> tuple[np.ndarray, np.ndarray]:
    fast, slow = external_inputs(profile, index)
    jv, jo = routed_local(profile, index, side, amplitude)
    labels = target_label_map(index)
    # The internal slot permutation is applied to parameter slots, never inferred from model identity.
    slot_gain = {"slot_A": (params.g_v, params.g_o), "slot_B": (params.g_o, params.g_v)}
    g_v, g_o = slot_gain[labels["V"]]
    nv = noise(profile, index, "V", 0.018)
    no = noise(profile, index, "O", 0.018)
    ns = noise(profile, index, "shared_boundary", 0.025)
    zv = np.zeros(T)
    zo = np.zeros(T)
    v = np.zeros(T)
    o = np.zeros(T)
    for t in range(1, T):
        zv[t] = params.a_v * zv[t - 1] + params.b_fv * fast[t - 1] + params.b_sv * slow[t - 1] + g_v * jv[t - 1] + params.c_o_to_v * g_o * jo[t - 1] + params.rho_shared * ns[t]
        zo[t] = params.a_o * zo[t - 1] + params.b_fo * fast[t - 1] + params.b_so * slow[t - 1] + g_o * jo[t - 1] + params.c_v_to_o * g_v * jv[t - 1] + params.rho_shared * ns[t]
        v[t] = 0.70 * v[t - 1] + params.q_v * np.tanh(zv[t]) + params.k_v_from_o * np.tanh(zo[t]) + 0.10 * fast[t] + nv[t]
        o[t] = 0.67 * o[t - 1] + params.q_o * np.tanh(zo[t]) + params.k_o_from_v * np.tanh(zv[t]) + 0.10 * slow[t] + no[t]
    return v, o


def simulate(model: str, profile: str, index: int, side: str | None, amplitude: float, params: M11Params | None = None) -> tuple[np.ndarray, np.ndarray]:
    if model == "M0" or model == "M11-U":
        # M11-U is an explicit oracle canary: duplicated labels, exact M0 observable trace.
        return simulate_m0(profile, index, side, amplitude)
    fast, slow = external_inputs(profile, index)
    jv, jo = routed_local(profile, index, side, amplitude)
    labels = target_label_map(index)
    slot_gain = {"slot_A": 0.36, "slot_B": 0.32}
    gv, go = slot_gain[labels["V"]], slot_gain[labels["O"]]
    nv = noise(profile, index, "V", 0.018)
    no = noise(profile, index, "O", 0.018)
    nc = noise(profile, index, "common_driver", 0.025)
    v = np.zeros(T)
    o = np.zeros(T)
    if model == "M11-C":
        if params is None:
            raise ValueError("M11-C parameters are required")
        return simulate_m11_c(profile, index, side, amplitude, params)
    if model in {"M1", "M10"}:
        bv = np.zeros(T)
        bo = np.zeros(T)
        av, ao = (0.81, 0.79) if model == "M1" else (0.82, 0.79)
        cubic = 0.0 if model == "M1" else 0.022
        for t in range(1, T):
            bv[t] = av * bv[t - 1] + 0.42 * fast[t - 1] + 0.22 * slow[t - 1] + gv * jv[t - 1] - cubic * bv[t - 1] ** 3 + nv[t]
            bo[t] = ao * bo[t - 1] + 0.38 * fast[t - 1] + 0.25 * slow[t - 1] + go * jo[t - 1] - cubic * bo[t - 1] ** 3 + no[t]
            v[t] = 0.70 * v[t - 1] + 0.58 * np.tanh(bv[t]) + 0.10 * fast[t] + nv[t]
            o[t] = 0.67 * o[t - 1] + 0.54 * np.tanh(bo[t]) + 0.10 * slow[t] + no[t]
        return v, o
    if model == "M2":
        bv = np.zeros(T)
        bo = np.zeros(T)
        c = np.zeros(T)
        for t in range(1, T):
            c[t] = 0.88 * c[t - 1] + 0.35 * fast[t - 1] + 0.30 * slow[t - 1] + nc[t]
            bv[t] = 0.75 * bv[t - 1] + 0.22 * jv[t - 1] + nv[t]
            bo[t] = 0.77 * bo[t - 1] + 0.22 * jo[t - 1] + no[t]
            v[t] = 0.70 * v[t - 1] + 0.38 * np.tanh(c[t]) + 0.18 * np.tanh(bv[t]) + 0.08 * fast[t] + nv[t]
            o[t] = 0.67 * o[t - 1] + 0.34 * np.tanh(c[t]) + 0.18 * np.tanh(bo[t]) + 0.08 * slow[t] + no[t]
        return v, o
    if model == "M_CD":
        c = np.zeros(T)
        for t in range(1, T):
            c[t] = 0.90 * c[t - 1] + 0.36 * fast[t - 1] + 0.29 * slow[t - 1] + nc[t]
            v[t] = 0.70 * v[t - 1] + 0.50 * np.tanh(c[t]) + 0.28 * jv[t - 1] + 0.08 * fast[t] + nv[t]
            o[t] = 0.67 * o[t - 1] + 0.46 * np.tanh(c[t]) + 0.28 * jo[t - 1] + 0.08 * slow[t] + no[t]
        return v, o
    if model == "M_NULL":
        for t in range(1, T):
            v[t] = 0.35 * v[t - 1] + 0.02 * nv[t]
            o[t] = 0.32 * o[t - 1] + 0.02 * no[t]
        return v, o
    raise ValueError(model)


def trajectory_signature(y: np.ndarray) -> np.ndarray:
    points = np.arange(LOCAL_START, LOCAL_END, 7)
    return np.asarray(y[points], dtype=float)


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(x, dtype=float) ** 2)))


def normalized_energy_distance(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.ndim != 2 or b.ndim != 2 or a.shape[1] != b.shape[1]:
        raise ValueError("energy distance arrays must be two-dimensional with equal feature width")
    cross = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2).mean()
    aa = np.linalg.norm(a[:, None, :] - a[None, :, :], axis=2).mean()
    bb = np.linalg.norm(b[:, None, :] - b[None, :, :], axis=2).mean()
    return float(max(0.0, 2.0 * cross - aa - bb) / math.sqrt(a.shape[1]))


def output_distribution_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Fixed holdout distribution distance used for Delta_ID."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    mean_term = np.linalg.norm(a.mean(axis=0) - b.mean(axis=0)) / math.sqrt(a.shape[1])
    std_term = np.linalg.norm(a.std(axis=0) - b.std(axis=0)) / math.sqrt(a.shape[1])
    return float(mean_term + 0.25 * std_term)


def calibration_plant(profile: str, index: int, side: str, amplitude: float) -> dict[str, float]:
    """Model-independent actuator bench used only for local access calibration."""
    command = local_wave(profile, index, amplitude)
    kernel = np.array([1.0, 0.55, 0.20])
    target_signal = np.convolve(command, kernel, mode="full")[:T]
    leakage_signal = np.convolve(command, np.array([0.075, 0.035]), mode="full")[:T]
    target_noise = rng_for(VERSION, "actuator-noise", profile, index, side, "target").normal(0, 0.018, T)
    cross_noise = rng_for(VERSION, "actuator-noise", profile, index, side, "cross").normal(0, 0.018, T)
    target = target_signal + target_noise
    cross = leakage_signal + cross_noise
    target_rms = rms(target_signal[LOCAL_START:LOCAL_END])
    cross_rms = rms(leakage_signal[LOCAL_START:LOCAL_END])
    target_snr = target_rms / (rms(target_noise[LOCAL_START:LOCAL_END]) + EPS)
    ratio = cross_rms / (target_rms + EPS)
    return {
        "target_rms": target_rms,
        "cross_rms": cross_rms,
        "snr": float(target_snr),
        "cross_talk_ratio": float(ratio),
        "max_abs": float(np.max(np.abs(target[LOCAL_START:LOCAL_END]))),
        "finite": bool(np.isfinite(target).all() and np.isfinite(cross).all()),
    }


def run_access_calibration() -> tuple[dict, list[dict]]:
    rows: list[dict] = []
    for index in ACCESS_CAL:
        for profile in PROFILES:
            for side in ("V", "O"):
                for amp in AMPLITUDES:
                    r = calibration_plant(profile, index, side, amp)
                    rows.append({"index": index, "profile": profile, "side": side, "amplitude": amp, **r})
    ratios = np.array([r["cross_talk_ratio"] for r in rows], dtype=float)
    snrs = np.array([r["snr"] for r in rows], dtype=float)
    max_abs = np.array([r["max_abs"] for r in rows], dtype=float)
    q95 = float(np.quantile(ratios, 0.95))
    c_max = min(0.20, 1.25 * q95)
    summary = {
        "rows": len(rows),
        "cross_talk_q95": q95,
        "c_max": c_max,
        "direct_target_snr_min_observed": float(snrs.min()),
        "max_abs_observed": float(max_abs.max()),
        "rule": "c_max=min(cross_talk_cap=0.20, cross_talk_margin=1.25 * calibration q95)",
        "thresholds": {"snr_min": 5.0, "max_abs_limit": 4.0},
        "pass": bool(np.isfinite(ratios).all() and np.isfinite(snrs).all() and np.all(snrs >= 5.0) and np.all(max_abs <= 4.0) and np.all(ratios <= c_max + 1e-12)),
    }
    return summary, rows


def run_quality_calibration(c_max: float, params: M11Params | None = None) -> tuple[dict, list[dict]]:
    rows: list[dict] = []
    for index in MIMIC_FIT:
        for profile in PROFILES:
            base_v, base_o = simulate("M0", profile, index, None, 0.0)
            for side in ("V", "O"):
                for amp in AMPLITUDES:
                    v, o = simulate("M0", profile, index, side, amp)
                    if side == "V":
                        target_delta, cross_delta = v - base_v, o - base_o
                    else:
                        target_delta, cross_delta = o - base_o, v - base_v
                    noise_scale = max(float(np.std(base_v if side == "V" else base_o)), 1e-3)
                    cross_scale = max(float(np.std(base_o if side == "V" else base_v)), 1e-3)
                    rows.append(
                        {
                            "index": index,
                            "profile": profile,
                            "side": side,
                            "amplitude": amp,
                            "target_effect_rms": rms(target_delta[LOCAL_START:LOCAL_END]),
                            "cross_effect_rms": rms(cross_delta[LOCAL_START:LOCAL_END]),
                            "target_snr": rms(target_delta[LOCAL_START:LOCAL_END]) / noise_scale,
                            "cross_snr": rms(cross_delta[LOCAL_START:LOCAL_END]) / cross_scale,
                            "target_max_abs": float(np.max(np.abs(v if side == "V" else o))),
                            "finite": bool(np.isfinite(v).all() and np.isfinite(o).all()),
                        }
                    )
    target_snrs = np.array([r["target_snr"] for r in rows])
    cross_snrs = np.array([r["cross_snr"] for r in rows])
    maxima = np.array([r["target_max_abs"] for r in rows])
    summary = {
        "rows": len(rows),
        "target_snr_min": float(target_snrs.min()),
        "cross_snr_min": float(cross_snrs.min()),
        "target_max_abs": float(maxima.max()),
        "thresholds": {"target_snr_min": 2.0, "cross_snr_min": 1.0, "max_abs_limit": 4.0},
        "pass": bool(np.isfinite(target_snrs).all() and np.isfinite(cross_snrs).all() and np.all(target_snrs >= 2.0) and np.all(cross_snrs >= 1.0) and np.all(maxima <= 4.0)),
        "note": "quality uses M0 only on the pre-evaluation quality split; it does not inspect evaluation results",
    }
    return summary, rows


PARAM_NAMES = tuple(M11Params.__dataclass_fields__.keys())


@dataclass(frozen=True)
class FitCase:
    profile: str
    index: int
    side: str | None
    amplitude: float
    target: np.ndarray
    fast: np.ndarray
    slow: np.ndarray
    jv: np.ndarray
    jo: np.ndarray
    nv: np.ndarray
    no: np.ndarray
    ns: np.ndarray


def parameter_bounds(c_max: float, rho_max: float, kappa_max: float, stage: dict) -> tuple[np.ndarray, np.ndarray]:
    bound_map = {
        "a_v": (0.65, 0.95),
        "a_o": (0.65, 0.95),
        "b_fv": (0.10, 0.80),
        "b_fo": (0.10, 0.80),
        "b_sv": (0.05, 0.60),
        "b_so": (0.05, 0.60),
        "g_v": (0.15, 0.80),
        "g_o": (0.15, 0.80),
        "c_v_to_o": (-float(stage["cross_talk_bound"]), float(stage["cross_talk_bound"])),
        "c_o_to_v": (-float(stage["cross_talk_bound"]), float(stage["cross_talk_bound"])),
        "rho_shared": (-float(stage["shared_innovation_bound"]), float(stage["shared_innovation_bound"])),
        "k_v_from_o": (-float(stage["cross_output_coupling_bound"]), float(stage["cross_output_coupling_bound"])),
        "k_o_from_v": (-float(stage["cross_output_coupling_bound"]), float(stage["cross_output_coupling_bound"])),
        "q_v": (0.25, 0.90),
        "q_o": (0.25, 0.90),
    }
    low = np.array([bound_map[name][0] for name in PARAM_NAMES], dtype=float)
    high = np.array([bound_map[name][1] for name in PARAM_NAMES], dtype=float)
    return low, high


def params_from_vector(x: np.ndarray) -> M11Params:
    return M11Params(**{name: float(value) for name, value in zip(PARAM_NAMES, x)})


def build_fit_cases(indices: Iterable[int]) -> list[FitCase]:
    cases: list[FitCase] = []
    for index in indices:
        for profile in PROFILES:
            for side, amp in [(None, 0.0), ("V", AMPLITUDES[0]), ("V", AMPLITUDES[1]), ("O", AMPLITUDES[0]), ("O", AMPLITUDES[1])]:
                v, o = simulate_m0(profile, index, side, amp)
                target = np.concatenate([trajectory_signature(v), trajectory_signature(o)])
                fast, slow = external_inputs(profile, index)
                jv, jo = routed_local(profile, index, side, amp)
                cases.append(
                    FitCase(
                        profile,
                        index,
                        side,
                        amp,
                        target,
                        fast,
                        slow,
                        jv,
                        jo,
                        noise(profile, index, "V", 0.018),
                        noise(profile, index, "O", 0.018),
                        noise(profile, index, "shared_boundary", 0.025),
                    )
                )
    return cases


def fit_objective(params: M11Params, cases: list[FitCase]) -> float:
    """Vectorized observed-output fit; no hidden M0 state is used."""
    fast = np.stack([c.fast for c in cases])
    slow = np.stack([c.slow for c in cases])
    jv = np.stack([c.jv for c in cases])
    jo = np.stack([c.jo for c in cases])
    nv = np.stack([c.nv for c in cases])
    no = np.stack([c.no for c in cases])
    ns = np.stack([c.ns for c in cases])
    gv = np.array([params.g_v if target_label_map(c.index)["V"] == "slot_A" else params.g_o for c in cases])[:, None]
    go = np.array([params.g_o if target_label_map(c.index)["O"] == "slot_B" else params.g_v for c in cases])[:, None]
    zv = np.zeros_like(fast)
    zo = np.zeros_like(fast)
    v = np.zeros_like(fast)
    o = np.zeros_like(fast)
    for t in range(1, T):
        zv[:, t] = params.a_v * zv[:, t - 1] + params.b_fv * fast[:, t - 1] + params.b_sv * slow[:, t - 1] + gv[:, 0] * jv[:, t - 1] + params.c_o_to_v * go[:, 0] * jo[:, t - 1] + params.rho_shared * ns[:, t]
        zo[:, t] = params.a_o * zo[:, t - 1] + params.b_fo * fast[:, t - 1] + params.b_so * slow[:, t - 1] + go[:, 0] * jo[:, t - 1] + params.c_v_to_o * gv[:, 0] * jv[:, t - 1] + params.rho_shared * ns[:, t]
        v[:, t] = 0.70 * v[:, t - 1] + params.q_v * np.tanh(zv[:, t]) + params.k_v_from_o * np.tanh(zo[:, t]) + 0.10 * fast[:, t] + nv[:, t]
        o[:, t] = 0.67 * o[:, t - 1] + params.q_o * np.tanh(zo[:, t]) + params.k_o_from_v * np.tanh(zv[:, t]) + 0.10 * slow[:, t] + no[:, t]
    points = np.arange(LOCAL_START, LOCAL_END, 7)
    pred = np.concatenate([v[:, points], o[:, points]], axis=1)
    target = np.stack([c.target for c in cases])
    return float(np.mean((pred - target) ** 2))


def fit_m11_c(stage: dict, c_max: float, rho_max: float, kappa_max: float, cases: list[FitCase], random_count: int, seed_params: M11Params | None = None) -> tuple[M11Params, float, dict]:
    low, high = parameter_bounds(c_max, rho_max, kappa_max, stage)
    r = rng_for(VERSION, "M11-C-fit", stage["name"])
    candidates = [0.5 * (low + high)]
    # Force the most permissive signed cross paths into the candidate set.
    for sign in (-1.0, 1.0):
        x = 0.5 * (low + high)
        for name in ("c_v_to_o", "c_o_to_v", "rho_shared", "k_v_from_o", "k_o_from_v"):
            j = PARAM_NAMES.index(name)
            x[j] = sign * high[j]
        candidates.append(x)
    if seed_params is not None:
        candidates.append(np.array([getattr(seed_params, name) for name in PARAM_NAMES], dtype=float))
    candidates.extend(low + r.random((random_count, len(PARAM_NAMES))) * (high - low))
    best_x, best_score = None, float("inf")
    for x in candidates:
        score = fit_objective(params_from_vector(x), cases)
        if score < best_score:
            best_x, best_score = x.copy(), score
    assert best_x is not None
    steps = 0.20 * (high - low)
    for _ in range(2):
        improved = False
        for j in range(len(PARAM_NAMES)):
            for direction in (-1.0, 1.0):
                trial = best_x.copy()
                trial[j] = np.clip(trial[j] + direction * steps[j], low[j], high[j])
                score = fit_objective(params_from_vector(trial), cases)
                if score + 1e-14 < best_score:
                    best_x, best_score, improved = trial, score, True
        steps *= 0.5
        if not improved:
            break
    params = params_from_vector(best_x)
    return params, float(best_score), {"random_candidates": len(candidates), "coordinate_rounds": 2, "parameter_names": list(PARAM_NAMES)}


def collect_observations(model: str, indices: Iterable[int], params: M11Params | None) -> tuple[dict, list[dict]]:
    cells: dict[tuple[str, float], dict[str, list[np.ndarray]]] = {}
    rows: list[dict] = []
    for profile in PROFILES:
        for amp in AMPLITUDES:
            cells[(profile, amp)] = {"zero_v": [], "zero_o": [], "jv_v": [], "jv_o": [], "jo_v": [], "jo_o": []}
    for index in indices:
        for profile in PROFILES:
            zero_v, zero_o = simulate(model, profile, index, None, 0.0, params)
            for amp in AMPLITUDES:
                jv_v, jv_o = simulate(model, profile, index, "V", amp, params)
                jo_v, jo_o = simulate(model, profile, index, "O", amp, params)
                cell = cells[(profile, amp)]
                cell["zero_v"].append(trajectory_signature(zero_v))
                cell["zero_o"].append(trajectory_signature(zero_o))
                cell["jv_v"].append(trajectory_signature(jv_v))
                cell["jv_o"].append(trajectory_signature(jv_o))
                cell["jo_v"].append(trajectory_signature(jo_v))
                cell["jo_o"].append(trajectory_signature(jo_o))
                rows.append(
                    {
                        "model": model,
                        "index": index,
                        "profile": profile,
                        "amplitude": amp,
                        "JV_to_V_effect_rms": rms((jv_v - zero_v)[LOCAL_START:LOCAL_END]),
                        "JV_to_O_effect_rms": rms((jv_o - zero_o)[LOCAL_START:LOCAL_END]),
                        "JO_to_V_effect_rms": rms((jo_v - zero_v)[LOCAL_START:LOCAL_END]),
                        "JO_to_O_effect_rms": rms((jo_o - zero_o)[LOCAL_START:LOCAL_END]),
                        "finite": bool(np.isfinite(zero_v).all() and np.isfinite(zero_o).all() and np.isfinite(jv_v).all() and np.isfinite(jv_o).all() and np.isfinite(jo_v).all() and np.isfinite(jo_o).all()),
                    }
                )
    arrays = {key: {name: np.vstack(values) for name, values in cell.items()} for key, cell in cells.items()}
    return arrays, rows


def cross_summary(observations: dict) -> tuple[dict, dict]:
    cell_scores: dict[str, dict] = {}
    jv_scores, jo_scores = [], []
    for (profile, amp), c in observations.items():
        jv_to_o = normalized_energy_distance(c["jv_o"], c["zero_o"])
        jo_to_v = normalized_energy_distance(c["jo_v"], c["zero_v"])
        jv_to_v = normalized_energy_distance(c["jv_v"], c["zero_v"])
        jo_to_o = normalized_energy_distance(c["jo_o"], c["zero_o"])
        key = f"{profile}|amp={amp:g}"
        cell_scores[key] = {
            "N_JV_to_O": jv_to_o,
            "N_JO_to_V": jo_to_v,
            "direct_JV_to_V": jv_to_v,
            "direct_JO_to_O": jo_to_o,
            "Gamma_cross_cell": min(jv_to_o, jo_to_v),
        }
        jv_scores.append(jv_to_o)
        jo_scores.append(jo_to_v)
    summary = {
        "N_JV_to_O": float(min(jv_scores)),
        "N_JO_to_V": float(min(jo_scores)),
        "Gamma_cross": float(min(min(jv_scores), min(jo_scores))),
        "cell_count": len(cell_scores),
        "cell_positive_count": int(sum(v["Gamma_cross_cell"] >= 0.05 for v in cell_scores.values())),
        "cell_scores": cell_scores,
    }
    return summary, cell_scores


def delta_id(m0_obs: dict, alt_obs: dict) -> tuple[float, dict]:
    distances: dict[str, float] = {}
    for key, m0 in m0_obs.items():
        alt = alt_obs[key]
        m0_joint_zero = np.column_stack([m0["zero_v"], m0["zero_o"]])
        alt_joint_zero = np.column_stack([alt["zero_v"], alt["zero_o"]])
        m0_joint_jv = np.column_stack([m0["jv_v"], m0["jv_o"]])
        alt_joint_jv = np.column_stack([alt["jv_v"], alt["jv_o"]])
        m0_joint_jo = np.column_stack([m0["jo_v"], m0["jo_o"]])
        alt_joint_jo = np.column_stack([alt["jo_v"], alt["jo_o"]])
        distances[f"{key}|zero"] = output_distribution_distance(m0_joint_zero, alt_joint_zero)
        distances[f"{key}|JV"] = output_distribution_distance(m0_joint_jv, alt_joint_jv)
        distances[f"{key}|JO"] = output_distribution_distance(m0_joint_jo, alt_joint_jo)
    return float(max(distances.values())), distances


def capacity_ladder(c_max: float, rho_max: float, kappa_max: float, cases: list[FitCase], m0_eval: dict) -> tuple[list[dict], M11Params]:
    raw_stages = [
        {"name": "C0_separate_no_cross", "cross_talk_bound": 0.0, "shared_innovation_bound": 0.0, "cross_output_coupling_bound": 0.0},
        {"name": "C1_measured_local_leakage", "cross_talk_bound": c_max, "shared_innovation_bound": 0.0, "cross_output_coupling_bound": 0.0},
        {"name": "C2_plus_shared_innovation", "cross_talk_bound": c_max, "shared_innovation_bound": rho_max, "cross_output_coupling_bound": 0.0},
        {"name": "C3_full_constrained_M11-C", "cross_talk_bound": c_max, "shared_innovation_bound": rho_max, "cross_output_coupling_bound": kappa_max},
    ]
    ladder = []
    full_params = None
    previous_params = None
    for stage in raw_stages:
        params, objective, fit_meta = fit_m11_c(
            stage,
            c_max,
            rho_max,
            kappa_max,
            cases,
            24 if stage["name"] != "C3_full_constrained_M11-C" else 64,
            seed_params=previous_params,
        )
        eval_obs, _ = collect_observations("M11-C", EVALUATION, params)
        holdout_delta, _ = delta_id(m0_eval, eval_obs)
        gamma, _ = cross_summary(eval_obs)
        record = {
            **stage,
            "params": asdict(params),
            "fit_objective": objective,
            "holdout_Delta_ID": holdout_delta,
            "holdout_Gamma_cross": gamma["Gamma_cross"],
            "fit_meta": fit_meta,
            "hidden_state_oracle_used": False,
        }
        ladder.append(record)
        previous_params = params
        if stage["name"] == "C3_full_constrained_M11-C":
            full_params = params
    assert full_params is not None
    return ladder, full_params


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def compare_seed_target_maps() -> bool:
    maps = {i: target_label_map(i) for i in range(N_PILOT)}
    # A second construction must agree and the map contains both permutations.
    replay = {i: target_label_map(i) for i in range(N_PILOT)}
    return maps == replay and len({tuple(m.values()) for m in maps.values()}) == 2


def technical_replay_probe() -> dict:
    a = rng_for(VERSION, "replay-probe").normal(size=256)
    b = rng_for(VERSION, "replay-probe").normal(size=256)
    return {
        "status": "PASS" if np.array_equal(a, b) else "FAIL",
        "same_seed_exact_array": bool(np.array_equal(a, b)),
        "probe_sha256": sha256_bytes(a.tobytes()),
        "scope": "deterministic seed construction probe; CI also performs full artifact replay",
    }


def build_gate_results(
    seed_info: dict,
    access: dict,
    quality: dict,
    summaries: dict[str, dict],
    delta_results: dict[str, dict],
    ladder: list[dict],
    replay: dict,
) -> tuple[dict, dict]:
    positive = 0.05
    negative = 0.02
    tolerance = 0.02
    m0 = summaries["M0"]
    m11c = summaries["M11-C"]
    m11u = summaries["M11-U"]
    basic_ok = all(summaries[m]["Gamma_cross"] <= negative for m in NEGATIVE_MODELS)
    m10_ok = summaries["M10"]["Gamma_cross"] <= negative
    cd_ok = summaries["M_CD"]["Gamma_cross"] <= negative
    m11c_delta = delta_results["M11-C"]["Delta_ID_M11_C"]
    m11c_separated = m11c_delta > tolerance and m11c["Gamma_cross"] < positive
    all_cells_robust = all(
        score["Gamma_cross_cell"] >= positive for score in m0["cell_scores"].values()
    ) and all(
        min(score["N_JV_to_O"], score["N_JO_to_V"]) < positive for score in m11c["cell_scores"].values()
    )
    ladder_monotone = all(
        ladder[i + 1]["fit_objective"] <= ladder[i]["fit_objective"] + 1e-10 for i in range(len(ladder) - 1)
    )
    gates = {
        "G0": bool(seed_info["unique"] and seed_info["legacy_overlap"] == 0 and seed_info["model_independent_target_rule"] and compare_seed_target_maps()),
        "G1": bool(access["pass"]),
        "G2": bool(quality["pass"]),
        "G3": bool(m0["N_JV_to_O"] >= positive and m0["N_JO_to_V"] >= positive),
        "G4": bool(basic_ok),
        "G5": bool(m10_ok),
        "G6": bool(cd_ok),
        "G7": bool(m11c_separated),
        "G8": bool(all_cells_robust),
        "G9": bool(len(ladder) == 4 and ladder[-1]["name"] == "C3_full_constrained_M11-C" and ladder_monotone),
        "G10": bool(delta_results["M11-U"]["Delta_ID_M11_C"] <= 1e-12 and m11u["Gamma_cross"] == m0["Gamma_cross"]),
        "G11": bool(replay["status"] == "PASS" and all(np.isfinite(x["Gamma_cross"]) for x in summaries.values())),
    }
    evidence = {
        "thresholds": {"positive": positive, "negative": negative, "equivalence_tolerance": tolerance},
        "gates": gates,
        "evidence": {
            "M0": {"Gamma_cross": m0["Gamma_cross"], "N_JV_to_O": m0["N_JV_to_O"], "N_JO_to_V": m0["N_JO_to_V"]},
            "M11-C": {"Gamma_cross": m11c["Gamma_cross"], "Delta_ID": m11c_delta},
            "M11-U": {"Gamma_cross": m11u["Gamma_cross"], "Delta_ID": delta_results["M11-U"]["Delta_ID_M11_C"]},
            "basic_negative_max_Gamma": max(summaries[m]["Gamma_cross"] for m in NEGATIVE_MODELS),
            "M10_Gamma_cross": summaries["M10"]["Gamma_cross"],
            "M_CD_Gamma_cross": summaries["M_CD"]["Gamma_cross"],
            "capacity_ladder": [{"name": x["name"], "fit_objective": x["fit_objective"], "holdout_Delta_ID": x["holdout_Delta_ID"]} for x in ladder],
        },
        "interpretation": "G10 is an oracle firewall; M11-U equivalence is expected and cannot support global identification.",
    }
    technical_gates = ("G0", "G1", "G9", "G10", "G11")
    scientific_gates = ("G3", "G4", "G5", "G6", "G7", "G8")
    if any(not gates[g] for g in technical_gates):
        decision = "INCONCLUSIVE_TECHNICAL"
    elif not gates["G2"] or not gates["G3"]:
        # The M0 positive control did not establish an estimable bidirectional A1 effect.
        # This is an access-assumption failure, not evidence for or against PH.
        decision = "ACCESS_ASSUMPTION_FAIL"
    elif m11c_delta <= tolerance:
        decision = "NON_IDENTIFIABLE_UNDER_A1"
    elif all(gates[g] for g in scientific_gates):
        # Phase 0A is a Pilot. This status authorizes a separately frozen confirmatory protocol,
        # but is not itself a final real-world identification claim.
        decision = "ACCESS_CONDITIONAL_IDENTIFIABILITY_SUPPORTED"
    else:
        decision = "INCONCLUSIVE_TECHNICAL"
    return evidence, {
        "decision": decision,
        "pilot_status": "PILOT_PASS_FREEZE_ALLOWED" if decision == "ACCESS_CONDITIONAL_IDENTIFIABILITY_SUPPORTED" else "PILOT_STOP",
        "failed_gates": [g for g, ok in gates.items() if not ok],
        "gates": gates,
        "claim_firewall": {
            "allowed": [
                "A1 and the frozen alternative class were evaluated in this synthetic model family.",
                "M0/M11-C interventional equivalence was or was not broken under the specified access model.",
            ],
            "forbidden": [
                "PH exists in nature.",
                "PH does not exist in nature.",
                "A single latent node is a person, self, consciousness, qualia, or soul.",
                "M11-C rejection rejects every possible alternative class.",
            ],
        },
        "confirmatory_authorization": decision == "ACCESS_CONDITIONAL_IDENTIFIABILITY_SUPPORTED",
    }


def generate_report(result: dict, access: dict, quality: dict, ladder: list[dict]) -> str:
    gates = result["gates"]
    lines = [
        "# PH v0.4 Phase 0A Pilot Result",
        "",
        f"**Decision:** `{result['decision']}`  ",
        f"**Pilot status:** `{result['pilot_status']}`",
        "",
        "## 1. Executive Summary",
        "",
        "The PH v0.3.3-r1 single shared-boundary node `NON_IDENTIFIABLE` result under A0 is frozen. This Pilot adds only A1 selective local interventions `J_V` and `J_O`; it does not repair the old classifier.",
        "",
        f"M0 Gamma_cross = `{result['summary']['M0']['Gamma_cross']:.6f}`; M11-C Gamma_cross = `{result['summary']['M11-C']['Gamma_cross']:.6f}`; operational Delta_ID(M11-C) = `{result['delta']['M11-C']['Delta_ID_M11_C']:.6f}`.",
        "",
        "## 2. Frozen Prior Result",
        "",
        "The prior v0.3.3-r1 technical STOP and structural NON_IDENTIFIABILITY are retained. No old feature, threshold, classifier, or Confirmatory result was changed.",
        "",
        "## 3. New Access Model",
        "",
        "A0 observes V/O under paired Fast/Slow inputs. A1 adds model-independent calibrated local waveforms J_V and J_O. Internal target-slot labels are seed-randomized identically across models.",
        "",
        "## 4. Model and Adversary Definitions",
        "",
        "M0 has one latent B. M11-C has duplicated Z_V/Z_O states and may use only pre-frozen bounded local leakage, shared innovation, and cross-output coupling. M11-U copies the M0 observable trace exactly and is an impossibility canary.",
        "",
        "## 5. Independent Calibration",
        "",
        f"Actuator calibration: `{access['pass']}`; c_max = `{access['c_max']:.6f}`; q95 cross-talk = `{access['cross_talk_q95']:.6f}`; minimum direct SNR = `{access['direct_target_snr_min_observed']:.3f}`.",
        f"M0 quality calibration: `{quality['pass']}`; minimum target SNR = `{quality['target_snr_min']:.3f}`; minimum cross SNR = `{quality['cross_snr_min']:.3f}`.",
        "",
        "## 6. Preregistered Metrics",
        "",
        "Primary Gamma_cross is the minimum normalized energy distance over both directions and every preregistered profile/amplitude cell. Delta_ID is the maximum holdout interventional distribution distance for the fitted full M11-C.",
        "",
        "## 7. Gate Results",
        "",
        "| Gate | Result |",
        "|---|---|",
    ]
    lines.extend(f"| {g} | {'PASS' if ok else 'FAIL'} |" for g, ok in gates.items())
    lines += [
        "",
        "## 8. Oracle Capacity Audit",
        "",
        "| Capacity | Fit objective | Holdout Delta_ID |",
        "|---|---:|---:|",
    ]
    lines.extend(f"| {x['name']} | {x['fit_objective']:.6f} | {x['holdout_Delta_ID']:.6f} |" for x in ladder)
    lines += [
        "",
        "The unrestricted oracle is intentionally not a success criterion. If M11-C reaches the equivalence tolerance, the result is `NON_IDENTIFIABLE_UNDER_A1`, and classifier repair is prohibited.",
        "",
        "## 9. Identifiability Analysis",
        "",
        f"M0: JV->O `{result['summary']['M0']['N_JV_to_O']:.6f}`, JO->V `{result['summary']['M0']['N_JO_to_V']:.6f}`.",
        f"M11-C: JV->O `{result['summary']['M11-C']['N_JV_to_O']:.6f}`, JO->V `{result['summary']['M11-C']['N_JO_to_V']:.6f}`.",
        f"M11-U holdout distance: `{result['delta']['M11-U']['Delta_ID_M11_C']:.12f}`.",
        "",
        "## 10. Red-Team Findings",
        "",
        "- Construction counterexample: M11-U is exactly equivalent by construction; it remains a firewall.",
        "- Unmeasured confound: a nonlocal shared actuator path outside the calibrated A1 channel family could mimic cross-effects.",
        "- Access-model failure risk: the local actuator is synthetic; calibration establishes only the declared synthetic selectivity, not physical access to a biological boundary.",
        "- Capacity audit: C0-C3 were evaluated; M11-C did not receive M0 hidden-state access.",
        "",
        "## 11. Claim Firewall",
        "",
        "This is a synthetic, access-conditional identifiability result. It does not establish or refute PH, consciousness, self, qualia, soul, or any natural-world entity.",
        "",
        "## 12. Final Decision",
        "",
        f"`{result['decision']}`",
        "",
        "## 13. Reproducibility and Artifact Hashes",
        "",
        f"Git commit: `{result['provenance']['git_commit']}`; config SHA256: `{result['provenance']['config_sha256']}`; preregistration SHA256: `{result['provenance']['preregistration_sha256']}`.",
        "",
        "## 14. Narrowest Defensible Next Step",
        "",
        "If NON_IDENTIFIABLE_UNDER_A1, stop the single-node identification program and redesign the access model or redefine PH as an interventional causal-equivalence class. If Pilot PASS is obtained, create a separately frozen blind-access Confirmatory protocol before generating N=384/model.",
        "",
    ]
    return "\n".join(lines)


def run(outdir: Path) -> int:
    started = time.time()
    outdir.mkdir(parents=True, exist_ok=True)
    config_path = HERE / "config.json"
    prereg_path = HERE / "preregistration.json"
    seed_info = seed_audit()
    access, access_rows = run_access_calibration()
    quality, quality_rows = run_quality_calibration(access["c_max"])
    fit_cases = build_fit_cases(MIMIC_FIT)
    m0_eval, m0_rows = collect_observations("M0", EVALUATION, None)
    ladder, m11c_params = capacity_ladder(access["c_max"], 0.25, 0.20, fit_cases, m0_eval)
    observations: dict[str, dict] = {"M0": m0_eval}
    all_per_seed = list(m0_rows)
    for model in MODELS:
        if model == "M0":
            continue
        params = m11c_params if model == "M11-C" else None
        obs, rows = collect_observations(model, EVALUATION, params)
        observations[model] = obs
        all_per_seed.extend(rows)
    summaries = {}
    for model, obs in observations.items():
        summaries[model], _ = cross_summary(obs)
    delta_results = {}
    for model in MODELS:
        if model == "M0":
            delta_results[model] = {"Delta_ID_M11_C": 0.0, "per_cell": {}}
        else:
            d, per_cell = delta_id(m0_eval, observations[model])
            delta_results[model] = {"Delta_ID_M11_C": d, "per_cell": per_cell}
    replay = technical_replay_probe()
    evidence, decision = build_gate_results(seed_info, access, quality, summaries, delta_results, ladder, replay)
    provenance = {
        "version": VERSION,
        "git_commit": os.environ.get("GITHUB_SHA", "LOCAL_UNCOMMITTED"),
        "config_sha256": sha256_file(config_path),
        "preregistration_sha256": sha256_file(prereg_path),
        "python": sys.version,
        "platform": platform.platform(),
    }
    result = {
        **decision,
        "version": VERSION,
        "summary": summaries,
        "delta": delta_results,
        "provenance": provenance,
        "runtime_seconds": time.time() - started,
        "splits": {"access_calibration": [0, 23], "quality_and_mimic_fit": [24, 47], "evaluation": [48, 95]},
        "frozen_prior": "PH v0.3.3-r1 structural NON_IDENTIFIABLE under A0",
    }

    write_json(outdir / "pilot_result.json", result)
    write_json(outdir / "gate_evidence.json", evidence)
    write_json(outdir / "decision.json", result)
    write_json(outdir / "m11_capacity_ladder.json", {"version": VERSION, "bounds": {"c_max": access["c_max"], "rho_max": 0.25, "kappa_max": 0.20}, "stages": ladder})
    write_json(outdir / "seed_audit.json", seed_info)
    write_json(outdir / "replay_audit.json", replay)
    write_json(outdir / "calibration_summary.json", access)
    write_json(outdir / "quality_summary.json", quality)
    (outdir / "README.md").write_text((HERE / "README.md").read_text(encoding="utf-8"), encoding="utf-8")
    write_csv(outdir / "calibration_results.csv", list(access_rows[0].keys()), access_rows)
    write_csv(outdir / "intervention_selectivity.csv", list(quality_rows[0].keys()), quality_rows)
    write_csv(outdir / "per_seed_metrics.csv", list(all_per_seed[0].keys()), all_per_seed)
    summary_rows = []
    for model in MODELS:
        s = summaries[model]
        summary_rows.append({
            "model": model,
            "N_JV_to_O": s["N_JV_to_O"],
            "N_JO_to_V": s["N_JO_to_V"],
            "Gamma_cross": s["Gamma_cross"],
            "cell_positive_count": s["cell_positive_count"],
            "Delta_ID_vs_M0": delta_results[model]["Delta_ID_M11_C"],
        })
    write_csv(outdir / "model_summary.csv", list(summary_rows[0].keys()), summary_rows)
    report_result = {**result}
    (outdir / "report.md").write_text(generate_report(report_result, access, quality, ladder), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pilot_status": result["pilot_status"], "failed_gates": result["failed_gates"], "summary": summary_rows}, indent=2))
    return 0 if result["decision"] == "ACCESS_CONDITIONAL_IDENTIFIABILITY_SUPPORTED" else 2


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="artifacts/pilot")
    args = ap.parse_args()
    raise SystemExit(run(Path(args.outdir)))


if __name__ == "__main__":
    main()
