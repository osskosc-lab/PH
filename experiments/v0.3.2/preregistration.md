# PH v0.3.2 — Dynamic Intervention Fingerprint & Identifiability Falsification

## Primary question
Can a true shared boundary mechanism be distinguished from an adversarial dynamic mimic using observable intervention dynamics on fresh holdout data?

## Primary contrast
- M0: shared_boundary
- M10: maximal_dynamic_mimic

## Model family
M0 shared_boundary
M1 separate_boundary
M2 common_driver
M3 viability_only
M4 observability_only
M5 null
M6 sensor_measurement_artifact
M7 static_clamp_mimic
M8 spectral_mimic
M9 phase_mimic
M10 maximal_dynamic_mimic

## Dynamic fingerprint
F = {gain/amplitude, phase, impulse response, recovery time, V-O cross transfer, intervention direction asymmetry, hysteresis/path dependence}.

Primary standardized dynamic distance:
D_dyn = (D_G + D_phi + D_h + D_tau + D_C + D_A) / 6.

Dynamic Identifiability Score:
DIS = d(M0, nearest negative) / d_within(M0).

## Interventions
Train: multisine, impulse, PRBS.
OOD: chirp, unseen frequencies, unseen amplitudes, burst, reversed sequence.
Additional: dual-timescale perturbation.

## Primary endpoints
- TPR_S = P(predicted shared | M0)
- FP_A = P(predicted shared | M10)
- DIS
- OOD retention
- representation-family agreement
- stress degradation envelope

## Confirmatory thresholds
- LCB95(TPR_S) > 0.80
- UCB95(FP_A) < 0.05
- UCB95(FP_sep) < 0.05
- UCB95(FP_common) < 0.05
- LCB95(DIS) > 1.0
- compound stress graceful-degradation floor s* >= 0.50

## Representation families
All defined before Pilot and frozen before Confirmatory:
- logistic classifier
- ridge classifier
- capacity-limited tree ensemble
- nearest centroid
- nonparametric distance classifier

No Confirmatory model selection is permitted.

## Pilot
Fresh seeds only. Legacy overlap must equal 0.
N = 60 per mode per condition.

Pilot gates:
G0 seed integrity
G1 dynamic range
G2 excitation
G3 positive recoverability
G4 maximal-adversarial specificity
G5 basic negative specificity
G6 representation consensus
G7 numerical integrity

If any Pilot gate fails: STOP. Any feature, threshold, classifier, regularization, or adversarial-model change requires a new revision and fresh Pilot seeds.

## Freeze
After Pilot PASS, freeze the following by SHA256:
config.json
preregistration.md
feature_spec.json
model_spec.json
thresholds.json
seed_manifest.json
adversarial_spec.json
analysis_plan.json

Then generate freeze.json. No post-freeze mutation is allowed before Confirmatory execution.

## Confirmatory
Fresh seeds only.
N = 256 per mode.
Primary comparison: M0 vs M10.

Confirmatory gates:
G0 Freeze integrity
G1 Positive identification
G2 Adversarial specificity
G3 Separate specificity
G4 Common-driver specificity
G5 Dynamic fingerprint separation
G6 OOD
G7 Representation independence
G8 Intervention asymmetry
G9 Temporal causality
G10 Stress degradation
G11 Compound
G12 Max-adversary challenge

## Stress axis
s in {0, 0.25, 0.5, 0.75, 1.0}
Stressors: clamp leakage, clamp noise, measurement error, latent driver, weak V/O coupling, colored noise, parameter drift, compound.

Graceful degradation:
s* = sup{s: TPR_S(s) >= 0.80 and FP_A(s) <= 0.05}.

## Final decision
IDENTIFIABLE: all core, OOD, representation, and stress gates pass.
FRAGILE_IDENTIFIABLE: core identifiability passes but stress envelope is narrower than preregistered.
NON_IDENTIFIABLE: maximal mimic and shared are not distinguishable on fresh Confirmatory data, especially when failure replicates across representation families.
INCONCLUSIVE: technical/numerical/preregistration failure prevents a valid test of identifiability.

## Scientific falsification rule
If M10 is accepted as shared above the preregistered FP limit across multiple independent representation families, do not relabel the outcome as 'needs a better classifier'. Treat it as evidence that the current intervention-observation set is insufficient for shared-boundary identifiability.
