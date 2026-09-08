# PH v0.5 AR-THF — Frozen Access Operators

## Canonical physical surface

s=(x1,x2,v,etaO*o,mB,r).
etaO=1.0 except G9 where etaO=0.35.

A0 and A1 access operators act only on this physical surface; they do not receive model identity or latent-node names.

## A0 — external-only coarse access

Inputs: uF,uS.
Observation interval: 0.10 s.
Delay: 0.
Observation:
yV=v+0.25*r+noise
yO=etaO*o+0.20*x2+noise
R=diag(0.05,0.05).

Registered A0 profiles for equivalence replay:
1. zero
2. uF finite pulse amplitude 1.0, duration 1.0 s
3. uS finite pulse amplitude 1.0, duration 1.0 s
4. uF multisine: 0.5*sin(2*pi*0.20*t)+0.5*sin(2*pi*0.37*t)
5. uS PRBS amplitude +/-0.7, dwell 0.5 s

## A1 — multi-resolution observation

a_high:
- sample interval 0.01 s
- delay 0
- observe all six canonical surface coordinates
- R=0.01*I6

a_mid:
- sample interval 0.05 s
- delay 0.05 s
- observe (v,etaO*o,mB)
- R=0.05*I3

a_low:
- sample interval 0.20 s
- delay 0.20 s
- observe (v+0.25*r,etaO*o+0.20*x2)
- R=0.20*I2

G3 artifact operator:
Only for G3 under a_low, replace the second noiseless channel with
yO_artifact=(etaO*o+0.20*x2)+0.40*(v+0.25*r).
No other operator changes are allowed.

## A2 — model-independent spatial local intervention

A2 is NOT allowed to address x5, zV or zO by name.

A synthetic actuator field is defined in physical coordinate r:
K(r;r_c)=exp(-(r-r_c)^2/(2*sigma_loc^2))
with sigma_loc=0.20.

Registered actuator centers:
r_c in {-0.50,0.00,+0.50}.

Pulse:
u_loc(t)=2.0 for 1.0 s starting at t=20.0 s, otherwise 0.

For every mediator node j having preregistered physical position r_j:
q_local,j(t)=u_loc(t)*K(r_j;r_c).

The field equation is identical for all models. Model identity is not an argument to the actuator.

H5 A2 separation aggregates all three centers by arithmetic mean; no post-hoc best-center selection is permitted.

## A3 — environment reach probe

Use the common external Fast channel, not a latent node:
uF=2.0 for t in [20.0,21.0), uS=0.
Observe e1..e8 every 0.10 s from t=20.1 through 25.0 inclusive (50 samples).
The counterfactual control uses uF=0 with common random numbers.

## H4 synthetic matched-observed-state reset

This is a qualification operator, not a claimed real-world access mode.

History +:
uF=+0.8 during [5,15) s.
History -:
uF=-0.8 during [5,15) s.

At t=15.0 s both trajectories have the canonical surface s and e1..e8 overwritten to the same baseline-reference values obtained from the paired zero-input path at t=15.0 s.
For G5, hidden h is explicitly NOT reset.
For G4 there is no hidden h.
Immediate post-reset canonical maximum absolute mismatch must be <=1e-10.
Future comparison window: [15.0,20.0] s with uF=uS=0.
