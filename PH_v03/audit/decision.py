from __future__ import annotations

def decide(gates,shared,controls,cfg):
    if all(gates.values()): return 'PH-v0.3 SUPPORTED'
    # Explicit causal falsification patterns on estimable data.
    if gates.get('G1_dynamic_range') and gates.get('G2_saturation') and gates.get('G3_spectral_excitation'):
        if shared['K_V_UCB']<=0.30 or shared['K_O_UCB']<=0.30: return 'PH-v0.3 FALSIFIED'
        if shared['R_OOD_LCB']>=1.0: return 'PH-v0.3 FALSIFIED'
        if controls['max_core_negative_fp']>cfg['analysis']['negative_false_positive_max']: return 'PH-v0.3 FALSIFIED'
        if controls['adversarial_fp']>cfg['analysis']['adversarial_false_positive_max']: return 'PH-v0.3 FALSIFIED'
    return 'INCONCLUSIVE'
