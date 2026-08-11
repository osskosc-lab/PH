from __future__ import annotations
import numpy as np

def dominant_pole_from_mean_impulse(Y,burn,impulse_offset=64,start_lag=10,end_lag=60):
    y=np.mean(Y,axis=0); t0=burn+impulse_offset; seg=y[t0+start_lag:t0+end_lag]
    # sign-robust exponential envelope fit; ignore near-zero/noisy points
    a=np.abs(seg); q=np.quantile(a,0.35); mask=a>max(q,1e-6)
    x=np.arange(len(seg))[mask]; z=np.log(a[mask]+1e-12)
    if len(x)<8: return float('nan')
    slope=np.polyfit(x,z,1)[0]; return float(np.clip(np.exp(slope),0.0,0.999))
