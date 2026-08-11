from __future__ import annotations
import numpy as np

def mean_ci(x,reps,seed):
    x=np.asarray(x,float); rng=np.random.default_rng(seed); vals=np.empty(reps)
    for b in range(reps):
        idx=rng.integers(0,len(x),len(x)); vals[b]=x[idx].mean()
    return float(x.mean()),float(np.quantile(vals,.025)),float(np.quantile(vals,.975))

def ratio_rms_ci(num2,den2,reps,seed):
    num2=np.asarray(num2,float); den2=np.asarray(den2,float); rng=np.random.default_rng(seed); vals=np.empty(reps)
    for b in range(reps):
        idx=rng.integers(0,len(num2),len(num2))
        vals[b]=np.sqrt(num2[idx].mean())/max(np.sqrt(den2[idx].mean()),1e-12)
    point=np.sqrt(num2.mean())/max(np.sqrt(den2.mean()),1e-12)
    return float(point),float(np.quantile(vals,.025)),float(np.quantile(vals,.975))
