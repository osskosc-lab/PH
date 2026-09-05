from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from phase2b.p2b_contract import (  # noqa: E402
    a_kappa,
    bootstrap_index,
    cell_by_id,
    gaussian_stream,
    load_contract,
    null_swap_bit,
    profile_value,
    require_execution_authorization,
    stream_key,
)
from phase2b.p2b_estimator import (  # noqa: E402
    normalized_energy_distance,
    trend_statistics,
)
from phase2b.p2b_simulator import (  # noqa: E402
    exact_null_target,
    simulate_oracle_clone_with_noise,
    simulate_with_noise,
    trajectory_signature,
)
from phase2b.p2b_validator import (  # noqa: E402
    validate_contract_semantics,
    validate_no_execution_authorization,
    validate_no_qual_entrypoint,
    validate_p0_hash_lock,
    validate_source_rng_guard,
)


CONTRACT_PATH = ROOT / "implementation_contract.json"


def contract():
    return load_contract(CONTRACT_PATH)


def test_p0_lock_and_stage_guard():
    validate_p0_hash_lock(ROOT)
    validate_contract_semantics(ROOT)
    validate_no_execution_authorization(ROOT)
    validate_no_qual_entrypoint(ROOT)
    validate_source_rng_guard(ROOT)


def test_a_kappa_exact_endpoints():
    c = contract()
    a1 = a_kappa(c, 1.0)
    a0 = a_kappa(c, 0.0)
    expected_a1 = np.array(
        [
            [0.75, -0.05, 0.015, 0.0],
            [0.05, 0.75, 0.0, 0.015],
            [0.01, 0.0, 0.9125, -0.03],
            [0.0, 0.01, 0.03, 0.9125],
        ],
        dtype=np.float64,
    )
    expected_a0 = expected_a1.copy()
    expected_a0[0, 0] = 0.95
    expected_a0[1, 1] = 0.95
    assert np.array_equal(a1, expected_a1)
    assert np.array_equal(a0, expected_a0)


def test_profiles_are_frozen():
    assert [profile_value("impulse", n) for n in (-1, 0, 1)] == [0.0, 1.0, 0.0]
    assert sum(profile_value("pulse8", n) for n in range(20)) == 8.0
    assert profile_value("biphasic16", 0) == 1.0
    assert profile_value("biphasic16", 8) == -1.0
    assert profile_value("biphasic16", 16) == 0.0
    assert profile_value("sine16x4", 64) == 0.0


def test_matched_noise_key_excludes_side():
    c = contract()
    k1 = stream_key(c, "QUAL", 0, 0, "P1-impulse-a0.25", "PROCESS")
    k2 = stream_key(c, "QUAL", 0, 0, "P1-impulse-a0.25", "PROCESS")
    assert k1 == k2
    assert np.array_equal(gaussian_stream(k1, 16), gaussian_stream(k2, 16))


def test_bootstrap_and_null_bits_are_replayable():
    assert bootstrap_index(17, 3, 96) == bootstrap_index(17, 3, 96)
    assert null_swap_bit(11, "P2-pulse8-a0.50", 9) == null_swap_bit(
        11, "P2-pulse8-a0.50", 9
    )


def test_exact_null_target_is_identical_for_both_labels():
    c = contract()
    cell = cell_by_id(c, "P1-impulse-a0.25")
    t = exact_null_target(cell)
    expected = np.array([1.0, 0.0, 1.0, 0.0], dtype=np.float64) / np.sqrt(2.0)
    assert np.array_equal(t, expected)


def test_trajectory_signature_indexing():
    y = np.arange(385 * 2, dtype=np.float64).reshape(385, 2)
    z = trajectory_signature(y, 128)
    baseline = y[192:256].mean(axis=0)
    expected = (y[257:385] - baseline).reshape(-1) / 16.0
    assert z.shape == (256,)
    assert np.array_equal(z, expected)


def test_energy_distance_identity_and_separation():
    x = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float64)
    assert normalized_energy_distance(x, x) <= 1e-15
    y = x + 10.0
    assert normalized_energy_distance(x, y) > 0.0


def test_zero_noise_oracle_clone_exactly_matches_base():
    c = contract()
    cell = cell_by_id(c, "P2-pulse8-a0.50")
    pnoise = np.zeros((384, 4), dtype=np.float64)
    onoise = np.zeros((385, 2), dtype=np.float64)
    _, y_base = simulate_with_noise(
        c,
        0.5,
        np.asarray(cell["in_target"], dtype=np.float64),
        cell["profile"],
        cell["amplitude"],
        pnoise,
        onoise,
    )
    z, y_clone = simulate_oracle_clone_with_noise(
        c,
        0.5,
        np.asarray(cell["in_target"], dtype=np.float64),
        cell["profile"],
        cell["amplitude"],
        pnoise,
        onoise,
    )
    assert np.array_equal(z[:, :4], z[:, 4:])
    assert np.array_equal(y_base, y_clone)


def test_trend_statistics_direction():
    stats = trend_statistics(
        [1.0, 0.75, 0.50, 0.25, 0.0],
        [0.50, 0.45, 0.40, 0.30, 0.20],
    )
    assert stats["V_mon"] <= 0.0
    assert stats["Delta_D"] == pytest.approx(0.30)
    assert stats["D_min"] == pytest.approx(0.20)


def test_stochastic_execution_is_locked_in_p1():
    with pytest.raises(PermissionError):
        require_execution_authorization(
            ROOT,
            "QUAL",
            "b7284913acb980fdb4285ee9c26f1725dff08380",
        )
