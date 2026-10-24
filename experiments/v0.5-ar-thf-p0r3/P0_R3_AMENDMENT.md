# P0-r3 Normative Amendment — Freeze Blockers B-1…B-4

Status: staged specification amendment only. This document does not authorize implementation, qualification, pilot, or confirmatory execution.

## Scope and precedence

This amendment resolves only the four P0-r2 freeze-review blockers: delayed-observation EKF semantics, H3 quadrature, the H3 claim boundary, and canonical seed derivation. It does not alter the P0-r2 model equations, G0–G9 model family, H_V/H_O/H_I/H2/H4/H5 definitions, execution gates, or PR #14 state. Where this amendment conflicts with an earlier P0-r2 sentence on one of these four topics, this amendment governs. All other P0-r2 text remains unchanged.

## B-1 — Delayed-observation EKF

### State and timing

Let the full EKF state used by the existing H_O definition be x_k in R^n. Augment that full EKF state, not merely the six-coordinate canonical observation surface:

x_aug,k = [x_k^T, x_(k-1)^T, ..., x_(k-n_d)^T]^T, with n_d = d / Δt.

The frozen time step is Δt = 0.01 s. Registered delays are 0, 0.05, and 0.20 s, giving n_d = 0, 5, and 20. A delay is valid only if |d/Δt - round(d/Δt)| <= 1e-12; reject, do not silently round, any other delay.

An observation generated at time t_j is received at t_r = t_j + d. At receipt time t_r, update the augmented-state block representing x(t_j), i.e. block index n_d for a fixed-delay stream. Do not rewind the filter clock or apply the measurement as if it were a current-state observation. The observation matrix selects only the registered observed coordinates in that historical block. Zero-delay observations select the current block.

### Initialization and propagation

Start the augmented filter at simulation time 0. Initialize each state block to the registered generator initial-state mean; initialize the augmented covariance block-diagonally with the existing H_O initial covariance P_0 = 0.25 I_n. The existing 20 s burn-in remains in force, so the initial history transient is excluded from metric aggregation.

Use the shift transition: propagate the leading state block with the existing EKF dynamics and Jacobian, shift the previous state blocks one position, and discard the oldest block. Propagate covariance with the corresponding augmented Jacobian:
P^-_k = F_aug,k P_(k-1) F_aug,k^T + Q_aug,k.
Place process noise only in the leading block; the deterministic history shift has zero process-noise blocks. Preserve cross-covariances created by propagation and measurement updates. Use the existing Joseph-form covariance update and existing finite-difference Jacobian convention.

Observations received at the same simulation timestamp are applied sequentially in ascending observation-generation timestamp, then ascending access label as a deterministic tie-breaker. Each update uses the state and covariance resulting from the immediately preceding update.

### Omega_a compatibility

For every registered observation update, compute the ratio using the leading/current-state block only:
r_k = tr(P_aug,+_(k,00)) / tr(P_aug,-_(k,00)).
Here the minus covariance is immediately before that observation update and the plus covariance is immediately after it; historical-block traces are never included. Retain P0-r2's burn-in exclusion, convergence rule, aggregation window, and H1 decision rule.

## B-2 — H3 target integral

For Y = (1/8) sum_i integral from 20 to 25 of |e_i(t) - e_i,control(t)| dt, use the composite trapezoidal rule with Δt = 0.01 s and exactly 501 samples:
t_k = 20.0 + 0.01 k, k = 0,...,500.
Include both endpoints. Use weights 1/2 at k=0 and k=500 and weight 1 at all interior points, multiplied by 0.01. Evaluate the integrand directly at stored simulation states; do not interpolate. The t=20.0 state is the state at the end of burn-in, and the t=25.0 state is included.

The deterministic quadrature check is the composite-trapezoid approximation to integral_20^25 sin(t) dt, using the same 501-point grid. The expected numerical value is -0.5831158907023989 with absolute tolerance 1e-12. This check must not initialize or draw from any RNG and must not run a model simulation.

## B-3 — H3 claim boundary

The permitted claim is:

> H3 tests whether adding H_I to the registered baseline features reduces independent-test-set prediction error across repeated realizations of the same 40 registered G0-HET parameter combinations. It does not test or support generalization to unseen parameter values, unseen structures, or distribution shifts.

Use “incremental predictive information across repeated realizations” for this claim. Do not describe it as unseen-structure generalization. The training and test sets share the same 40 parameter combinations and differ only by complete lattice repeats. Any claim beyond this boundary requires a separate amendment freezing a genuinely unseen parameter/structure split.

## B-4 — Canonical seed derivation

### Canonical serialization

All seed inputs are NFC-normalized strings encoded as UTF-8 with no BOM and no trailing newline. Join fields with the literal ASCII vertical bar U+007C. Fields may not contain |, CR, LF, or NUL. No whitespace trimming, case folding, or implicit numeric conversion is allowed.

The canonical field order is:

master_seed|phase|model_id|stream_type|pair_group|master_index|replicate_index|component

- master_seed, master_index, and replicate_index: unsigned decimal integers, no leading zero except the value 0; scientific notation and signs are forbidden.
- phase: exactly burnin or measurement.
- model_id: exactly G0…G9, or PAIR for a registered paired stream whose plant noise must be shared across models.
- stream_type: exactly one of PLANT, FEATURE, H3_TARGET, OBS, INTERVENTION, BOOTSTRAP, or PERMUTATION. This canonical registry supersedes legacy P0-r2 stream labels: MEASUREMENT is renamed OBS; BOOTSTRAP and PERMUTATION retain their names. INTERVENTION is used only if a registered protocol explicitly defines an independently randomized intervention stream; deterministic actuator profiles do not create an intervention RNG stream.
- pair_group: a registered identifier from the frozen seed manifest, or exactly none.
- component: an exact component token registered in the frozen seed manifest; no runtime-generated component names are allowed.

For a paired PLANT stream, use model_id=PAIR and the registered non-none pair group so the seed is identical across the models in that pair. For unpaired streams, use the actual model ID. FEATURE and H3_TARGET must remain distinct stream types. The manifest must list every legal tuple and check derived-seed collisions across distinct canonical strings before any future execution authorization is considered.

Compute SHA-256 over the canonical UTF-8 bytes. Interpret digest bytes 0–7 as an unsigned little-endian 64-bit integer; do not mask off the high bit. This is a seed derivation rule, not a mathematical guarantee that hash collisions are impossible.

### Frozen known-answer test

For canonical string
123|burnin|G0|PLANT|H1_G0_A1|0|0|x1
SHA-256's first eight bytes interpreted little-endian must produce seed 15144518583270549771. This deterministic known-answer test must not initialize or draw from an RNG.

## Execution locks and allowed validation

The status remains P0_R3_STAGED_FOR_HUMAN_FREEZE_REVIEW. The only allowed automated validation introduced by this amendment is deterministic static-contract checking and the two deterministic known-answer/unit checks described above. No simulator, stochastic qualification, pilot, confirmatory run, random dataset, or scientific pass/fail conclusion is authorized.

The following values must remain unchanged in the decision record:

- P1_IMPLEMENTATION: PROHIBITED
- STOCHASTIC_QUALIFICATION: PROHIBITED
- PILOT: PROHIBITED
- CONFIRMATORY: PROHIBITED

A green CI run is evidence only that the static amendment checks passed; it is not freeze approval or execution authorization.
