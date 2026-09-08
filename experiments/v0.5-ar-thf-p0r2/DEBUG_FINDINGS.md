# P0-r1 Debug Audit — Findings and Fixes

No simulator or stochastic experiment was run during debugging.

## DBG-01 — CRITICAL — CRN seed contradiction

P0-r1 derived seeds from namespace|phase|generator|access|cell|... while simultaneously requiring G0/G6 and other contrasts to share plant noise. Those requirements are incompatible if implemented literally.

Fix: P0-r2 introduces stream_type and pair_group. Paired PLANT seeds omit generator/access names outside the pair_group.

## DBG-02 — MAJOR — A0 input underfreeze

Finite-pulse start time and the PRBS realization were unspecified.

Fix: all A0 profiles are active only on [20,25); pulses start at 20.0; PRBS-like signs are a fixed 10-dwell sequence.

## DBG-03 — CRITICAL — H3 chirp absolute-time bug

P0-r1 used phase 0.15*t + 0.5*(0.30/5)*t^2 over global t=20..25. The instantaneous frequency is therefore ~1.35..1.65 Hz, not the intended 0.15..0.45 Hz.

Fix: tau=t-20.0 and phase 0.15*tau+0.5*0.06*tau^2.

## DBG-04 — CRITICAL — H3 shared-noise leakage

P0-r1 did not force feature-side and target-side stochastic streams to be independent. Ridge improvement could therefore exploit shared nuisance realization.

Fix: FEATURE and H3_TARGET are disjoint stream types. Only intervention/control within the H3 target pair share plant noise.

## DBG-05 — MAJOR — H3 estimability

With one fixed G0 parameterization, cross-seed variation in H_V/H_O/H_I is mostly Monte Carlo noise. That is a poor test of incremental mechanistic information.

Fix: a fully balanced 40-cell G0-HET lattice varies influence, viability and observation axes independently and repeats each combination five times. Train/test are complete-lattice repeats.

## DBG-06 — MAJOR — H4 test ambiguity

"paired/permutation" was not implementation-complete.

Fix: q_i=d_G5-d_G4, median statistic, 20,000 frozen Rademacher sign flips, exact Monte Carlo p formula.

## DBG-07 — MAJOR — Q8 null ambiguity

P0-r1 asked for an FWER false-positive rate from 200 null seeds without defining five null experiments.

Fix: Q8 is now an explicit five-canary suite, one null for each H1-H5 decision rule.

## DBG-08 — MAJOR — CI only checked JSON parsing

The P0-r1 workflow could pass while cross-file contradictions remained.

Fix: P0-r2 adds a static contract auditor checking version/locks, seed-range disjointness, deterministic profile markers, local-time chirp, H3 stream separation, H4 permutation count, null-canary presence, experiment-cell uniqueness and ontology-leak strings.

## Decision

P0-r1 is retained as an immutable debug precursor.
P0-r2 is the only candidate for Human PI freeze review.
P1, Qualification, Pilot and Confirmatory remain prohibited.
