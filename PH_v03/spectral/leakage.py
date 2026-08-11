from __future__ import annotations
import numpy as np
from .fft import active_fft,nearest_bins

def leakage_fraction(U,burn,freqs):
    f,F=active_fft(U,burn); idx=set(nearest_bins(f,freqs).tolist()); p=np.abs(F)**2; keep=np.zeros(p.shape[-1],bool)
    for j in idx: keep[j]=True
    total=np.sum(p,axis=1)+1e-15; outside=np.sum(p[:,~keep],axis=1); return outside/total

def min_registered_power(U,burn,freqs):
    f,F=active_fft(U,burn); idx=nearest_bins(f,freqs); p=(np.abs(F[:,idx])/(U.shape[-1]-burn))**2; return np.min(p,axis=1)
