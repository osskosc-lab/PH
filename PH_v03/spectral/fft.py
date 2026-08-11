from __future__ import annotations
import numpy as np

def active_fft(x,burn):
    z=np.asarray(x)[...,burn:]; return np.fft.rfftfreq(z.shape[-1]),np.fft.rfft(z,axis=-1)

def nearest_bins(freq_grid,freqs):
    return np.array([int(np.argmin(np.abs(freq_grid-f))) for f in freqs],dtype=int)
