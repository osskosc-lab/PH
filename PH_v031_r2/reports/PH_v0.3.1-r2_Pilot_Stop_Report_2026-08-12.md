# PH v0.3.1-r2 Pilot Stop Report — 2026-08-12

**Official decision: INCONCLUSIVE (Pilot stop; Confirmatory not started)**

## Purpose
R2 was designed to separate technical ambiguity from true compound-stress fragility without lowering any inherited decision threshold.

## Technical repairs that worked
- Raw-margin saturation gate: PASS. Maximum clipping fraction across Pilot core modes = 0.003571 (<0.05).
- Paired RNG integrity: PASS. Base-noise hashes are identical across stress strengths for every audited `(mode, factor, index)`.
- Fresh SHA256 seed registry: no overlap with the registered v0.3/v0.3.1 seed ranges.

## Kernel Pilot Gate
Deterministic leave-one-lambda-out CV selected:
- bandwidth h = 0.5
- alpha = 0.01
- CV RMSE = 0.163899

The shared positive control had point-estimate R_kernel = 0.986550 (<1), but the preregistered paired-bootstrap recovery probability was only 0.675, below the required 0.80.

Critical negative kernel false-positive probability remained controlled: max FP = 0.0433 (<=0.05).

## Decision consequence
The preregistration explicitly states that Kernel Pilot validation failure stops the experiment before Confirmatory. Therefore no fresh Confirmatory seeds were consumed, no confirmatory freeze was created, and no ROBUST/FRAGILE/FALSIFIED call is permitted.

This result isolates the unresolved issue: the repaired kernel representation is specific but not sufficiently sensitive/reliable on the Pilot positive control. The next version should revise the representation method itself before any new Confirmatory run; G12 must remain untouched.
