from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .p2b_contract import git_blob_sha1_bytes, load_contract, load_json


REQUIRED_P0_FILES = (
    "implementation_contract.json",
    "preregistration.json",
    "CLAIM_FIREWALL.md",
    "P0_FREEZE_AUDIT.md",
    "README.md",
)

REQUIRED_P1_SOURCE_FILES = (
    "src/phase2b/__init__.py",
    "src/phase2b/p2b_contract.py",
    "src/phase2b/p2b_simulator.py",
    "src/phase2b/p2b_estimator.py",
    "src/phase2b/p2b_validator.py",
    "tests/test_p1_deterministic.py",
    "requirements.txt",
)

PROHIBITED_SOURCE_TOKENS = (
    "np.random",
    "numpy.random",
    "random.random",
    "random.gauss",
    "default_rng(",
)


def validate_p0_hash_lock(root: str | Path) -> dict[str, str]:
    root = Path(root)
    lock = load_json(root / "p0_lock.json")
    expected = lock["git_blob_sha1"]
    observed: dict[str, str] = {}
    for name in REQUIRED_P0_FILES:
        data = (root / name).read_bytes()
        observed[name] = git_blob_sha1_bytes(data)
        if observed[name] != expected[name]:
            raise AssertionError(
                f"P0 frozen file changed: {name}: {observed[name]} != {expected[name]}"
            )
    return observed


def validate_p1_source_hash_lock(root: str | Path) -> dict[str, str]:
    root = Path(root)
    lock = load_json(root / "p1_source_lock.json")
    expected = lock["git_blob_sha1"]
    observed: dict[str, str] = {}
    for rel in REQUIRED_P1_SOURCE_FILES:
        data = (root / rel).read_bytes()
        observed[rel] = git_blob_sha1_bytes(data)
        if observed[rel] != expected[rel]:
            raise AssertionError(
                f"P1 source changed: {rel}: {observed[rel]} != {expected[rel]}"
            )
    return observed


def validate_contract_semantics(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    c = load_contract(root / "implementation_contract.json")

    assert c["scientific_execution"] == "PROHIBITED"
    assert c["numeric_contract"]["state_dimension"] == 4
    assert c["numeric_contract"]["state_order"] == ["c1", "c2", "e1", "e2"]
    assert c["numeric_contract"]["no_float32"] is True
    assert c["dynamics"]["h"] == 0.25
    assert c["dynamics"]["kappa_grid"] == [1, 0.75, 0.5, 0.25, 0]
    assert len(c["intervention_contract"]["matched_cells"]) == 16
    assert c["intervention_contract"]["amplitudes"] == [0.25, 0.5]
    assert list(c["intervention_contract"]["profiles"]) == [
        "impulse",
        "pulse8",
        "sine16x4",
        "biphasic16",
    ]
    assert c["trajectory_signature"]["dimension"] == 256
    assert c["bootstrap_contract"]["repeats"] == 10000
    assert c["seed_namespace"]["qualification"]["n"] == 96
    assert c["seed_namespace"]["confirmatory_reserved"]["n"] == 384
    assert (
        c["seed_namespace"]["confirmatory_reserved"]["generation"]
        == "PROHIBITED_UNTIL_SEPARATE_CONFIRMATORY_FREEZE"
    )
    assert c["stage_lock"]["current_stage"] == "P2B-P1_IMPLEMENTATION_QUALIFICATION"
    return c


def validate_no_execution_authorization(root: str | Path) -> None:
    root = Path(root)
    if (root / "execution_authorization.json").exists():
        raise AssertionError(
            "P1 branch must not contain execution_authorization.json"
        )


def validate_source_rng_guard(root: str | Path) -> list[str]:
    root = Path(root)
    src = root / "src" / "phase2b"
    checked: list[str] = []
    for path in sorted(src.glob("*.py")):
        if path.name == "p2b_validator.py":
            checked.append(path.name)
            continue
        text = path.read_text(encoding="utf-8")
        for token in PROHIBITED_SOURCE_TOKENS:
            if token in text:
                raise AssertionError(f"prohibited RNG token {token!r} in {path.name}")
        checked.append(path.name)
    if not checked:
        raise AssertionError("no P1 source files found")
    return checked


def validate_no_qual_entrypoint(root: str | Path) -> None:
    root = Path(root)
    forbidden = (
        root / "run_qual.py",
        root / "run_confirmatory.py",
        root / "src" / "phase2b" / "run_qual.py",
        root / "src" / "phase2b" / "run_confirmatory.py",
    )
    present = [str(p) for p in forbidden if p.exists()]
    if present:
        raise AssertionError(f"execution entrypoint prohibited in P1: {present}")


def static_p1_audit(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    return {
        "p0_hashes": validate_p0_hash_lock(root),
        "p1_source_hashes": validate_p1_source_hash_lock(root),
        "contract_id": validate_contract_semantics(root)["contract_id"],
        "execution_authorization_absent": (
            not (root / "execution_authorization.json").exists()
        ),
        "source_files": validate_source_rng_guard(root),
        "qual_entrypoint_absent": True,
    }


if __name__ == "__main__":
    here = Path(__file__).resolve().parents[2]
    validate_no_execution_authorization(here)
    validate_no_qual_entrypoint(here)
    print(json.dumps(static_p1_audit(here), indent=2, sort_keys=True))
