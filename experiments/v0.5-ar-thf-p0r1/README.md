# PH v0.5 — Access-Relative Tri-Horizon Falsification (AR-THF)

This directory stages **P0-r1 only**.

The experiment reframes PH as three operational horizons:

- H_V: how far the system can recover/continue
- H_O: how reconstructable the internal state is under access a
- H_I: how far an intervention on the system changes future environment state

The design also retains the prior identifiability lesson: A0 is intentionally insufficient for distinguishing G0 from the G6 oracle clone.

## Main novelty

A2 no longer addresses latent nodes by model-specific names. It uses a single Gaussian spatial actuator field defined over preregistered physical coordinates. This prevents the intervention operator from encoding the ontology it is supposed to identify.

## Current authorization

P0-r1 staged for Human PI freeze review.

- Simulator implementation: prohibited
- Stochastic Qualification: prohibited
- Pilot: prohibited
- Confirmatory: prohibited

Any substantive P0 change after approval must create a fresh P0-r2.
