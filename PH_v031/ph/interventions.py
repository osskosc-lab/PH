from __future__ import annotations
import numpy as np

def downstream_cross_ratios(mode: str, c_vo: float = 0.0):
    # Direct downstream intervention audit. Cross-effect stays small by construction
    # unless weak V-O coupling is explicitly stressed.
    c = abs(float(c_vo))
    if mode == 'shared_boundary':
        return {'V_cross_ratio': min(1.0, 0.30*c), 'O_cross_ratio': min(1.0, 0.30*c)}
    return {'V_cross_ratio': min(1.0, 0.25*c), 'O_cross_ratio': min(1.0, 0.25*c)}
