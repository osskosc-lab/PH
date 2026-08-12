from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
FROZEN_FILES = [
    "config.json",
    "preregistration.md",
    "feature_spec.json",
    "model_spec.json",
    "thresholds.json",
    "seed_manifest.json",
    "adversarial_spec.json",
    "analysis_plan.json",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def seed32(stage: str, mode: str, condition: str, index: int) -> int:
    token = f"PH-v0.3.2|{stage}|{mode}|{condition}|{index}".encode("utf-8")
    digest = hashlib.sha256(token).digest()
    return int.from_bytes(digest[:4], "big", signed=False)


def generate_seed_manifest(stage: str, modes: Iterable[str], conditions: Iterable[str], n: int) -> dict:
    rows = []
    seen = set()
    for mode in modes:
        for condition in conditions:
            for index in range(n):
                s = seed32(stage, mode, condition, index)
                if s in seen:
                    raise RuntimeError(f"seed collision: {s}")
                seen.add(s)
                rows.append({"stage": stage, "mode": mode, "condition": condition, "index": index, "seed": s})
    return {"version": "PH-v0.3.2", "algorithm": "uint32(first4bytes(SHA256(token)))", "rows": rows}


def write_freeze() -> dict:
    missing = [name for name in FROZEN_FILES if not (ROOT / name).exists()]
    if missing:
        raise FileNotFoundError(f"cannot freeze; missing: {missing}")
    hashes = {name: sha256_file(ROOT / name) for name in FROZEN_FILES}
    payload = {"version": "PH-v0.3.2", "files": hashes}
    (ROOT / "freeze.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def verify_freeze() -> bool:
    freeze_path = ROOT / "freeze.json"
    if not freeze_path.exists():
        raise FileNotFoundError("freeze.json not found")
    frozen = json.loads(freeze_path.read_text(encoding="utf-8"))
    for name, expected in frozen["files"].items():
        actual = sha256_file(ROOT / name)
        if actual != expected:
            raise RuntimeError(f"freeze mismatch: {name}: {actual} != {expected}")
    return True


def pilot_gate_decision(metrics: dict) -> dict:
    required = ["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"]
    missing = [g for g in required if g not in metrics]
    if missing:
        return {"decision": "INCONCLUSIVE", "reason": f"missing pilot gates: {missing}"}
    failed = [g for g in required if metrics[g] is not True]
    if failed:
        return {
            "decision": "STOP",
            "failed_gates": failed,
            "rule": "Any change requires revision suffix and fresh Pilot seeds.",
        }
    return {"decision": "PILOT_PASS_FREEZE_ALLOWED"}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    seeds = sub.add_parser("seeds")
    seeds.add_argument("--stage", choices=["pilot", "confirmatory"], required=True)
    seeds.add_argument("--n", type=int, required=True)
    seeds.add_argument("--output", required=True)

    sub.add_parser("freeze")
    sub.add_parser("verify-freeze")

    gates = sub.add_parser("pilot-gates")
    gates.add_argument("metrics_json")

    args = parser.parse_args()
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    models = list(json.loads((ROOT / "model_spec.json").read_text(encoding="utf-8"))["models"].keys())

    if args.cmd == "seeds":
        if args.stage == "pilot":
            conditions = config["train_interventions"] + config["ood_interventions"] + config["additional_interventions"]
        else:
            conditions = config["train_interventions"] + config["ood_interventions"] + config["additional_interventions"]
        manifest = generate_seed_manifest(args.stage, models, conditions, args.n)
        Path(args.output).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    elif args.cmd == "freeze":
        print(json.dumps(write_freeze(), indent=2))
    elif args.cmd == "verify-freeze":
        verify_freeze()
        print("PASS")
    elif args.cmd == "pilot-gates":
        metrics = json.loads(Path(args.metrics_json).read_text(encoding="utf-8"))
        print(json.dumps(pilot_gate_decision(metrics), indent=2))


if __name__ == "__main__":
    main()
