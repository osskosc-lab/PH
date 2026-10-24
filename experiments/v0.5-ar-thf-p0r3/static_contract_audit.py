import hashlib
import json
import math
import pathlib
import unicodedata

ROOT = pathlib.Path("experiments/v0.5-ar-thf-p0r3")
spec = (ROOT / "P0_R3_AMENDMENT.md").read_text(encoding="utf-8")
decision = json.loads((ROOT / "decision.json").read_text(encoding="utf-8"))

assert decision["decision"] == "P0_R3_STAGED_FOR_HUMAN_FREEZE_REVIEW"
for key in ("P1_IMPLEMENTATION", "STOCHASTIC_QUALIFICATION", "PILOT", "CONFIRMATORY"):
    assert decision[key] == "PROHIBITED", (key, decision[key])
assert decision["simulation_executed"] is False
assert decision["stochastic_data_generated"] is False

for phrase in (
    "full EKF state",
    "receipt time",
    "0.05, and 0.20 s",
    "P_aug,+_(k,00)",
    "501 samples",
    "-0.5831158907023989",
    "does not test or support generalization",
    "master_index|replicate_index|component",
    "little-endian",
    "FEATURE and H3_TARGET",
):
    assert phrase in spec, f"missing normative requirement: {phrase}"

# Deterministic trapezoid known-answer check; no model simulation or RNG.
dt = 0.01
samples = [math.sin(20.0 + k * dt) for k in range(501)]
trap = dt * (0.5 * samples[0] + sum(samples[1:-1]) + 0.5 * samples[-1])
assert abs(trap - (-0.5831158907023989)) <= 1e-12, trap

# Deterministic SHA-256 seed known-answer check; no RNG is initialized or drawn.
canonical = unicodedata.normalize(
    "NFC", "123|burnin|G0|PLANT|H1_G0_A1|0|0|x1"
).encode("utf-8")
seed = int.from_bytes(hashlib.sha256(canonical).digest()[:8], "little", signed=False)
assert seed == 10371618808033434132, seed

for forbidden in ("simulator.py", "run_qual.py", "run_pilot.py", "run_confirmatory.py",
                  "execution_authorization.json"):
    assert not any(p.name == forbidden for p in ROOT.rglob("*")), (
        f"execution-lock violation: {forbidden}"
    )

print("P0_R3_STATIC_AMENDMENT_AUDIT: PASS")
print("Deterministic checks only; no simulator or stochastic execution performed.")
