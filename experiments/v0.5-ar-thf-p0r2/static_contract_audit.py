import csv
import json
import pathlib
import re

ROOT = pathlib.Path("experiments/v0.5-ar-thf-p0r2")

required = [
    "ph_v05_ar_thf_preregistration.json",
    "synthetic_generator_spec.md",
    "access_operator_spec.md",
    "metric_definitions.md",
    "qualification_gates.json",
    "seed_manifest.json",
    "decision.json",
    "claim_ledger.md",
    "experiment_matrix.csv",
    "null_canary_spec.md",
    "audit_manifest.json",
    "DEBUG_FINDINGS.md",
]

for name in required:
    p = ROOT / name
    assert p.exists(), f"missing required P0-r2 artifact: {name}"

for name in [
    "ph_v05_ar_thf_preregistration.json",
    "qualification_gates.json",
    "seed_manifest.json",
    "decision.json",
    "audit_manifest.json",
]:
    with open(ROOT / name, encoding="utf-8") as f:
        json.load(f)

forbidden_names = {
    "simulator.py",
    "run_qual.py",
    "run_pilot.py",
    "run_confirmatory.py",
    "execution_authorization.json",
}
present = [str(p) for p in ROOT.rglob("*") if p.name in forbidden_names]
assert not present, f"execution-lock violation: {present}"

decision = json.load(open(ROOT / "decision.json", encoding="utf-8"))
assert decision["decision"] == "P0_R2_STAGED_FOR_HUMAN_FREEZE_REVIEW"
for key in ["P1_IMPLEMENTATION", "STOCHASTIC_QUALIFICATION", "PILOT", "CONFIRMATORY"]:
    assert decision[key] == "PROHIBITED", (key, decision[key])

pre = json.load(open(ROOT / "ph_v05_ar_thf_preregistration.json", encoding="utf-8"))
assert pre["version"] == "0.5.0-p0r2"
assert pre["p1_authorized"] is False
assert pre["stochastic_execution_authorized"] is False

seed = json.load(open(ROOT / "seed_manifest.json", encoding="utf-8"))
ranges = list(seed["master_index_ranges"].values())
for i, (a0, a1) in enumerate(ranges):
    assert a0 <= a1
    for b0, b1 in ranges[i+1:]:
        assert a1 < b0 or b1 < a0, f"seed range overlap: {(a0,a1)} {(b0,b1)}"
assert "pair_group" in seed["hash_to_seed"]
assert "generator" not in seed["hash_to_seed"]
assert "access" not in seed["hash_to_seed"]
assert "FEATURE" in seed["stream_types"] and "H3_TARGET" in seed["stream_types"]

access = (ROOT / "access_operator_spec.md").read_text(encoding="utf-8")
assert "tau=t-20.0" in access
assert "signs=[+1,-1,+1,+1,-1,-1,+1,-1,-1,+1]" in access
assert "No random PRBS generator is permitted" in access
for leak in ["do(x5", "do(zV", "do(zO", "model identity is an argument"]:
    assert leak.lower() not in access.lower(), f"ontology/access leak string found: {leak}"

metrics = (ROOT / "metric_definitions.md").read_text(encoding="utf-8")
assert "FEATURE and H3_TARGET" in metrics
assert "B=20000" in metrics
assert "train master indices 2000..2119" in metrics
assert "test master indices 2120..2199" in metrics
assert "lambda_I=1.0" in metrics

synth = (ROOT / "synthetic_generator_spec.md").read_text(encoding="utf-8")
assert "5*4*2=40 combinations repeated exactly five times" in synth
assert "pair_group" in synth

gates = json.load(open(ROOT / "qualification_gates.json", encoding="utf-8"))
for i in range(11):
    assert f"Q{i}" in gates
assert "null_canary_suite" == gates["Q8"]["name"]

nulls = (ROOT / "null_canary_spec.md").read_text(encoding="utf-8")
for h in ["H1 null", "H2 null", "H3 null", "H4 null", "H5 null"]:
    assert h in nulls

with open(ROOT / "experiment_matrix.csv", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))
ids = [r["cell_id"] for r in rows]
assert len(ids) == len(set(ids)), "duplicate experiment cell_id"
for needed in ["C01","C02","C18","C19","N01","N02","N03","N04","N05"]:
    assert needed in ids

print("P0_R2_STATIC_CONTRACT_AUDIT: PASS")
print("No simulator or stochastic execution performed.")
