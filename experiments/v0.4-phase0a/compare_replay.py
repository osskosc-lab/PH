from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXCLUDE = {"runtime_seconds"}


def canonical_without_runtime(path: Path) -> bytes:
    obj = json.loads(path.read_text(encoding="utf-8"))
    for key in EXCLUDE:
        obj.pop(key, None)
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("first")
    ap.add_argument("second")
    args = ap.parse_args()
    first = Path(args.first)
    second = Path(args.second)
    names = [
        "pilot_result.json",
        "gate_evidence.json",
        "decision.json",
        "m11_capacity_ladder.json",
        "seed_audit.json",
        "calibration_results.csv",
        "intervention_selectivity.csv",
        "per_seed_metrics.csv",
        "model_summary.csv",
    ]
    checks = {}
    ok = True
    for name in names:
        a = first / name
        b = second / name
        if name.endswith(".json"):
            same = canonical_without_runtime(a) == canonical_without_runtime(b)
        else:
            same = file_hash(a) == file_hash(b)
        checks[name] = {"same": same, "first_sha256": file_hash(a), "second_sha256": file_hash(b)}
        ok = ok and same
    result = {"status": "PASS" if ok else "FAIL", "checks": checks, "runtime_excluded": sorted(EXCLUDE)}
    (first / "replay_audit.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
