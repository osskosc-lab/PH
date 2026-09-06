# ATCT-PH Phase 2B v0.1 — P1 Implementation Audit

## Current decision

```
P2B-P0_SPECIFICATION_FREEZE: PASS
P2B-P1_IMPLEMENTATION_PRESENT: YES
P2B-P1_CODE_TO_CONTRACT_STATIC_REVIEW: STARTED
P2B-P1_DETERMINISTIC_TESTS: WRITTEN_NOT_EXECUTED
P2B-P1_REPLAY_HASH_VALIDATOR: WRITTEN_NOT_EXECUTED

STOCHASTIC_QUALIFICATION_RUN: NOT_AUTHORIZED
CONFIRMATORY_RUN: NOT_AUTHORIZED
```

This P1 change writes code only. No stochastic QUAL data, no Pilot data, and no Confirmatory data are generated.

## Implemented modules

- `src/phase2b/p2b_contract.py`
  - frozen matrix construction;
  - intervention profiles;
  - SHA-256 counter stream;
  - Box-Muller Gaussian transform;
  - exact-uniform bootstrap index mapping;
  - null-swap bits;
  - Git-blob hashing;
  - execution authorization guard.

- `src/phase2b/p2b_simulator.py`
  - deterministic base simulator given explicit noise arrays;
  - exact duplicated-latent Oracle Clone;
  - CW1 reporter simulator;
  - registered trajectory signature;
  - response RMS, `d_K`, return time;
  - registered stochastic wrapper that is locked unless an external authorization file is later added.

- `src/phase2b/p2b_estimator.py`
  - frozen normalized energy distance;
  - exact 16-cell median aggregation;
  - H1 trend statistics;
  - nearest-rank quantiles;
  - paired seed bootstrap implementation;
  - label-swap null transformation;
  - diagnostic conditional-Gaussian Fisher matrix;
  - finite-difference susceptibility utility.

- `src/phase2b/p2b_validator.py`
  - P0 Git-blob lock verification;
  - frozen-contract semantic checks;
  - no-execution-authorization check;
  - prohibited library-RNG source scan;
  - absence of QUAL/CONF entrypoint check.

- `tests/test_p1_deterministic.py`
  - deterministic-only tests for matrices, profiles, hashing/RNG replay, exact-null target, signature indexing, energy distance, Oracle Clone equivalence, trend direction, and execution lock.

## Deliberate P1 execution barrier

There is **no** `run_qual.py`, **no** `run_confirmatory.py`, and **no**
`execution_authorization.json` in this directory.

The only stochastic runner in the simulator library calls an authorization guard first.
On this branch, that guard must fail by construction.

## What remains before stochastic QUAL can be authorized

1. static line-by-line code-to-contract review;
2. deterministic test execution / compile check;
3. replay/hash validator execution;
4. confirmation that P0 Git-blob locks still match;
5. explicit gate decision authorizing QUAL in a separate execution-authorization mutation.

Until those steps pass, stochastic QUAL remains prohibited.
