# PH v0.3.2-r1 Confirmatory Result

## Experiment

Frozen Fresh Confirmatory — Dynamic Intervention Fingerprint & Identifiability Falsification

## Official decision

`NON_IDENTIFIABLE`

The frozen PH v0.3.2-r1 detector did not maintain shared-vs-mimic specificity on fresh Confirmatory data.

This is a scientific result, not a technical execution failure.

## Reproducibility record

- Branch: `experiment/ph-v0.3.2-r1-confirmatory`
- GitHub Actions run: `31573394761`
- Confirmatory commit: `affeaae3390a982467e5c0ef4bdf66add2863f9f`
- Artifact: `ph-v0.3.2-r1-confirmatory`
- Artifact ID: `9132231501`
- Artifact SHA256: `0ba63753b7da59ee3611c6e1309c1049fe7f1bad27a2ef33909ed04a68be81f7`
- N: `256 / model`
- Pilot seed overlap: `0`
- Paired RNG integrity: `PASS`
- Confirmatory seed uniqueness: `PASS`

## Frozen state

No Confirmatory tuning was performed.

Frozen from the successful r1 Pilot:

- M10: `av=0.88, ao=0.87, gv=0.36, go=0.34`
- 35 raw dynamic features
- 70D intervention-set fingerprint
- Pilot standardization
- all five representation families
- Pilot-calibrated thresholds
- primary representation: `balanced_logistic`

Primary threshold:

`1.1891711734690704`

## Confirmatory Gates

| Gate | Criterion | Result |
|---|---|---|
| C0 | Freeze integrity | PASS |
| C1 | Core M0 LCB95 > 0.80 | PASS |
| C2 | Core M10 UCB95 < 0.05 | **FAIL** |
| C3 | Core M1/M2/M5 UCB95 < 0.05 | **FAIL** |
| C4 | OOD M0 LCB95 > 0.80 | PASS |
| C5 | OOD M10 UCB95 < 0.05 | **FAIL** |
| C6 | OOD M1/M2/M5 UCB95 < 0.05 | **FAIL** |
| C7 | >=3 representation families independently pass | **FAIL** |
| C8 | Numerical + seed integrity | PASS |

No representation family passed the preregistered Confirmatory consensus rule.

## Primary representation: balanced logistic

### Core intervention set

| Mode | accepted / 256 | Rate | Wilson 95% bound relevant to Gate |
|---|---:|---:|---:|
| M0 shared | 256 | 1.0000 | LCB = `0.985216` |
| M10 maximal mimic | 39 | 0.152344 | UCB = `0.201478` |
| M1 separate | 39 | 0.152344 | UCB = `0.201478` |
| M2 common driver | 39 | 0.152344 | UCB = `0.201478` |
| M5 null | 39 | 0.152344 | UCB = `0.201478` |

Positive recoverability survived extremely strongly, but specificity did not.

The primary M10 false-positive rate was about three times the allowed point threshold and its Wilson UCB was about four times the preregistered 0.05 bound.

### OOD intervention set

For balanced logistic:

- M0: `256/256 = 1.00`
- M10: `256/256 = 1.00`
- M1/M2/M5: `256/256 = 1.00`
- all other negative models were also accepted as shared at `1.00`

Therefore the frozen parametric detector collapsed to an almost unconditional shared classification under the unseen intervention family.

## Representation independence

The failure was not confined to the primary classifier.

### Balanced ridge

- Core M0: `1.00`
- Core M10: `0.152344`
- OOD: all modes, including negatives, accepted at `1.00`

### Shrinkage diagonal LDA

- Core M0: `254/256 = 0.992188`, LCB95 `0.971967`
- Core M10: `46/256 = 0.179688`, UCB95 `0.231344`
- OOD: all modes accepted at `1.00`

### Balanced centroid

- Core M0: `249/256 = 0.972656`
- Core M10: `54/256 = 0.210938`, UCB95 `0.265000`
- OOD: all modes accepted at `1.00`

### Balanced nonparametric distance

This family failed in the opposite direction.

Core:

- M0: `213/256 = 0.832031`, LCB95 `0.781404` — positive Gate fails
- M10: `10/256 = 0.0390625`, UCB95 `0.070400` — strict specificity Gate still fails
- M1: `6/256 = 0.023438`, UCB95 `0.050181`
- M2: `7/256 = 0.027344`, UCB95 `0.055356`
- M5: `0/256`, UCB95 `0.014784`

OOD:

- M0: `0/256`
- M10: `0/256`
- all other models: `0/256`

Thus parametric families generalize by accepting essentially everything, whereas the nonparametric-distance family generalizes by rejecting essentially everything.

This is a representation-level failure rather than a single-classifier accident.

## Dynamic separation diagnostics

These diagnostics were preregistered as non-gating:

- `DIS_core = 0.0273811000`
- `DIS_OOD = 0.3514639013`

Both are below 1, and the core value is especially small, consistent with poor separation of M0 and M10 relative to within-M0 variation.

## Technical replay repair provenance

The first Confirmatory workflow attempt stopped before Confirmatory data generation because the freeze validator incorrectly required a floating-point-derived `standardization.json` to reproduce byte-for-byte.

Before any Confirmatory seed was generated, this was repaired by:

1. committing the original Pilot artifact files byte-for-byte;
2. verifying their original SHA256 hashes exactly;
3. comparing deterministic floating-point replay against the frozen values with `1e-12` numerical tolerance;
4. leaving all scientific parameters, thresholds, M10, features, representations, sample size, seeds, and decision rules unchanged.

The original frozen Confirmatory protocol hash remained:

`c211971efd9a6e97ff1234f8e6ae7b08f9a0426430e113c3555a30598b00d241`

The technical replay wrapper hash was separately frozen as:

`392e39f4189baab0f9ef70076493750f59434c68ad56fca75b38fb3d8469fb9b`

## Interpretation

The r1 Pilot success did not survive full fresh Confirmatory evaluation.

The strongest defensible conclusion for this version is:

> The currently observed 35-feature / 70D aggregated dynamic intervention fingerprint does not robustly identify a shared boundary against maximal mimic and basic negative mechanisms under fresh Confirmatory and OOD intervention data.

This result does **not** falsify the existence of a shared boundary in general. It falsifies the stronger detector claim that the present observable dynamic fingerprint is sufficient for robust identification of that boundary.

It is therefore not scientifically valid to respond by merely tuning a new classifier or threshold inside v0.3.2-r1.

## Next valid research direction

Any continuation must be a new revision with a fresh Pilot and genuinely new intervention information, rather than post-hoc classifier repair.

Examples of admissible new information sources include:

- explicit cross-intervention invariants rather than only mean/std aggregation;
- state-dependent intervention sequences;
- randomized intervention location or channel;
- multi-site interventions that impose shared-latent consistency constraints;
- recovery trajectories conditional on matched pre-intervention latent state;
- directional causal constraints that a pair of independent mimics cannot jointly satisfy.

These are future hypotheses only. None may be retrofitted into the present Confirmatory result.
