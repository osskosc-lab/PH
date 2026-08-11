from __future__ import annotations
import numpy as np

def breakpoint(levels,accuracy,threshold=.80):
    levels=np.asarray(levels,float); acc=np.asarray(accuracy,float)
    ok=levels[acc>=threshold]
    return float(ok.max()) if len(ok) else None
