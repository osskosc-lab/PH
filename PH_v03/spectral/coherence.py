from __future__ import annotations
import numpy as np
from .fft import active_fft,nearest_bins

def ensemble_coherence(U,Y,burn,freqs):
    f,FU=active_fft(U,burn); _,FY=active_fft(Y,burn); idx=nearest_bins(f,freqs);U1=FU[:,idx];Y1=FY[:,idx]
    suy=np.mean(np.conj(U1)*Y1,axis=0);suu=np.mean(np.abs(U1)**2,axis=0);syy=np.mean(np.abs(Y1)**2,axis=0)
    return f[idx],np.clip(np.abs(suy)**2/(suu*syy+1e-15),0,1)
