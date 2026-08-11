from __future__ import annotations

def final_decision(core,robustness,cfg):
    idx=core.set_index('mode')
    if not bool(core['technical_pass'].all()): return 'INCONCLUSIVE'
    shared=bool(idx.loc['shared_boundary','positive'])
    key=['separate_boundary','common_driver','adversarial_clamp_mimic']
    fps={m:bool(idx.loc[m,'positive']) for m in key}
    if (not shared) or any(fps.values()): return 'PH-v0.3.1 FALSIFIED'
    req=float(cfg['stress']['compound']['confirmatory_level'])
    q=robustness[(robustness.factor=='compound') & (robustness.strength==req)]
    if q.empty:return 'INCONCLUSIVE'
    acc=float(q.iloc[0].P_correct)
    return 'PH-v0.3.1 ROBUST' if acc>=cfg['analysis']['operating_accuracy_min'] else 'PH-v0.3.1 FRAGILE'
