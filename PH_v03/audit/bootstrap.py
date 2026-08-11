from __future__ import annotations
import numpy as np

def mean_ci(x,reps=1500,seed=12345):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    if len(x)==0:return (float('nan'),float('nan'),float('nan'))
    r=np.random.default_rng(seed);idx=r.integers(0,len(x),(reps,len(x)));m=np.mean(x[idx],axis=1)
    return float(np.mean(x)),float(np.quantile(m,.025)),float(np.quantile(m,.975))

def rate_ci(x,reps=1500,seed=54321):
    return mean_ci(np.asarray(x,float),reps,seed)
