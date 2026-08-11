from __future__ import annotations
import numpy as np
from .fft import active_fft,nearest_bins

def transfer_at(U,Y,burn,freqs):
    f,FU=active_fft(U,burn); _,FY=active_fft(Y,burn); idx=nearest_bins(f,freqs)
    return f[idx], FY[:,idx]/(FU[:,idx]+1e-15)

def spectral_gain(U,Y,burn,freqs):
    _,H=transfer_at(U,Y,burn,freqs); return np.sqrt(np.mean(np.abs(H)**2,axis=1))
