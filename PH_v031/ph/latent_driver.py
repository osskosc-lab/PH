from __future__ import annotations

def clamped_path_fraction(latent_ratio: float) -> float:
    return 1.0 / (1.0 + max(0.0, float(latent_ratio)))
