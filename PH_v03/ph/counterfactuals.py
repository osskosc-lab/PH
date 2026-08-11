from __future__ import annotations
import numpy as np

def paired_effect(free,intervened):
    return np.asarray(intervened)-np.asarray(free)
