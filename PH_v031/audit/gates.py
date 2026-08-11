from __future__ import annotations
import math

def positive_signature(row,cfg,require_representation=True):
    a=cfg['analysis']
    ok=(row['beta_V_LCB']>a['beta_lcb_min'] and row['beta_O_LCB']>a['beta_lcb_min'] and
        row['K_V_08']>a['K_at_08_min'] and row['K_O_08']>a['K_at_08_min'] and
        row['R_lambda_OOD_UCB']<a['R_lambda_OOD_ucb_max'] and
        row['R_CIC_UCB']<a['R_CIC_ucb_max'])
    if require_representation:
        ok=ok and bool(row['representation_pass'])
    return bool(ok)

def technical_ok(row,cfg):
    a=cfg['analysis']
    return bool(row['dynamic_range_pass'] and row['saturation_pass'] and row['finite_pass'])
