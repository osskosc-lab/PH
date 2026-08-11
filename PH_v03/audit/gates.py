from __future__ import annotations

def confirmatory_gates(shared,controls,cfg,pilot):
    a=cfg['analysis']
    g={}
    g['G0_freeze']=bool(shared['freeze_ok'])
    g['G1_dynamic_range']=bool(shared['dynamic_range_pass'])
    g['G2_saturation']=bool(shared['saturation_pass'])
    g['G3_spectral_excitation']=bool(shared['spectral_excitation_pass'] and shared['leakage_pass'])
    g['G4_positive_control_recovery']=bool(pilot['positive_detection_rate']>=a['pilot_positive_power_min'])
    g['G5_negative_control']=bool(controls['max_core_negative_fp']<=a['negative_false_positive_max'])
    g['G6_boundary_clamp']=bool(shared['K_V_LCB']>a['clamp_lcb_min'] and shared['K_O_LCB']>a['clamp_lcb_min'])
    g['G7_ood_generalization']=bool(shared['R_OOD_UCB']<a['ood_ratio_ucb_max'])
    g['G8_adversarial_mimic']=bool(controls['adversarial_fp']<=a['adversarial_false_positive_max'])
    g['G9_representation_independence']=bool(shared['representation_pass'])
    g['downstream_specificity']=bool(shared['V_cross_ratio_UCB']<a['downstream_cross_ratio_max'] and shared['O_cross_ratio_UCB']<a['downstream_cross_ratio_max'])
    return g
