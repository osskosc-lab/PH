from pathlib import Path
import sys,yaml,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ph.imperfect_clamp import effective_lambda
from analysis.intervention_ood import causal_intervention_consistency
from experiment import load_config,masks

def test_lambda_attenuation():
    x=effective_lambda(np.array([0,.5,1.]),.2)
    assert np.allclose(x,[0,.4,.8])

def test_cic_shared_like():
    x=np.linspace(.8,1.2,40); y=2*x+np.linspace(-.02,.02,40)
    out=causal_intervention_consistency(x,y)
    assert out['R_CIC']<.2 and out['R_CIC_UCB']<1

def test_masks_disjoint():
    cfg=load_config(ROOT/'preregistration'/'ph_v031.yaml');lam,tr,ood=masks(cfg)
    assert not np.any(tr & ood)
    assert tr.sum()==4 and ood.sum()==3
