from __future__ import annotations
import numpy as np

def effective_lambda(lam, leakage_fraction):
    return np.clip(np.asarray(lam, float) * (1.0 - float(leakage_fraction)), 0.0, 1.0)
