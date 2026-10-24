# PH v0.5 AR-THF — Frozen Synthetic Generator Specification (P0-r2)

Status: specification/debug hardening only. No simulator is authorized.

## 1. Numerical integration

All stochastic generators use Euler-Maruyama.

- dt = 0.01 s
- default run length = 30.0 s
- sigma_core = 0.08
- sigma_med = 0.08
- sigma_env = 0.10
- sigma_h = 0.05
- sigma_c = 0.12
- divergence STOP: ||state||_2 > 1e4
- all finite checks mandatory

Initial physical core:
(x1,x2,v,o,r)=(0,0,1.40,0,0).
All mediators, environment states, hidden memory and common driver start at 0.
The first 20.0 s are burn-in unless a metric defines another protocol.

## 2. External input

uS_eff(t)=Integral_0^t 1.5*exp(-1.5*(t-s))*uS(s) ds.
u_eff(t)=0.70*uF(t)+0.30*uS_eff(t).

## 3. Common physical equations

For mediator summaries mB,mV,mO,mI:

dx1=[-0.70*x1+0.55*tanh(x2)+0.20*mB+0.10*uF]dt+0.08dW1

dx2=[-0.65*x2-0.50*tanh(x1)+0.15*mB+0.10*uS_eff]dt+0.08dW2

dv=[aV*v-0.45*v^3+0.20*x1+0.40*mV+0.10*r]dt+0.08dWv

do=[-0.85*o+0.35*x2+0.45*mO]dt+0.08dWo

dr=[-0.60*r+0.30*mB+0.15*v]dt+0.08dWr

A standard mediator z obeys:
dz=[-0.75*z+0.25*x1+0.25*x2+0.20*tanh(v)+0.25*u_eff+q_local]dt+0.08dWz.

Default aV=0.90.

## 4. Environment equations

Default gamma1=0.50, gamma2=0.40.

de1=[-1.00*e1+gamma1*mI]dt+0.10dWe1

de2=[-1.10*e2+gamma2*mI+0.20*e1]dt+0.10dWe2

de3=[-1.00*e3+0.30*e1+0.20*e2]dt+0.10dWe3

de4=[-1.05*e4+0.35*e2]dt+0.10dWe4

de5=[-0.90*e5+0.25*e3+0.20*e4]dt+0.10dWe5

de6=[-0.95*e6+0.30*e4]dt+0.10dWe6

de7=[-0.85*e7+0.25*e5+0.15*e6]dt+0.10dWe7

de8=[-0.80*e8+0.30*e6+0.20*e7]dt+0.10dWe8

## 5. Generator definitions

### G0_shared
One standard mediator b.
mV=mO=mI=mB=b.
r_b=0.00.

### G1_separate
Three standard mediators zV,zO,zI with independent mediator innovations.
mV=zV, mO=zO, mI=zI, mB=(zV+zO)/2.
r_zV=-0.25, r_zO=+0.25, r_zI=+0.75.

### G2_common_driver
dc=-0.25*c dt+0.12dWc.
zV,zO,zI are standard mediators plus +0.20*c drift, with independent mediator innovations.
mV=zV, mO=zO, mI=zI, mB=(zV+zO)/2.
Positions as G1.

### G3_access_artifact
Plant dynamics are byte-for-byte G0_shared.
Only the registered G3 a_low observation operator differs.

### G4_historyless
Plant dynamics are byte-for-byte G0_shared.
This is the H4 Markov/null control.

### G5_history_dependent
dh=[-0.40*h+0.60*x1]dt+0.05dWh.
The shared mediator b receives additional +0.35*h drift.
mV=mO=mI=mB=b.
The H4 observed-state reset never resets h.

### G6_oracle_clone
Two mediators zV,zO.
Both start equal, receive the same u_eff and standard mediator drift, and under A0 receive the exact same mediator Brownian increment from the paired plant stream.
mV=zV, mO=zO, mI=(zV+zO)/2, mB=(zV+zO)/2.
r_zV=-0.25, r_zO=+0.25.
Under A0 q_local=0, so zV(t)=zO(t)=b_G0(t) pathwise under the frozen G0/G6 pair_group.
Under A2 the same spatial field acts everywhere and can drive zV/zO unequally.

### G7_influence_targeted
G0 except gamma1=0.90 and gamma2=0.72.

### G8_viability_targeted
G0 except aV=0.65.

### G9_observability_targeted
G0 dynamics. etaO=0.35 instead of 1.00 in observation surfaces.

## 6. H3 balanced heterogeneity subfamily G0-HET

G0-HET is not a new ontology class. It is a preregistered parameterized subfamily used only for H3 predictive non-redundancy.

For Pilot master offset j=0..199:
- lambda_I=[0.70,0.85,1.00,1.15,1.30][j mod 5]
- lambda_V=[0.85,1.00,1.15,1.30][floor(j/5) mod 4]
- lambda_O=[0.75,1.25][floor(j/20) mod 2]

Apply:
- gamma1=0.50*lambda_I
- gamma2=0.40*lambda_I
- aV=0.90*lambda_V
- etaO=lambda_O

This gives 5*4*2=40 combinations repeated exactly five times over 200 Pilot master indices.
Train uses the first three repeats (120 master indices); test uses the final two repeats (80 master indices).
No lattice value is selected or changed after observing outcomes.

## 7. Randomness

All Brownian/noise streams must be generated from seed_manifest.json.
For registered paired comparisons the PLANT stream is shared by pair_group and does not include generator/access names.
Measurement noise and H3 target streams are separate.
No implementation may infer or alter stream mapping from outcomes.
