from pathlib import Path
import sys,yaml,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ph.stimuli import multisine
from ph.dynamics import simulate
from spectral.leakage import leakage_fraction

def cfg(): return yaml.safe_load((ROOT/'preregistration'/'ph_v03.yaml').read_text())
def test_multisine_shape_and_leakage():
 c=cfg();seeds=np.array([1,2]);u,_=multisine(seeds,c['time']['T'],c['time']['burn_in'],c['stimuli']['train_multisine_frequencies'],c['stimuli']['train_amplitude']);assert u.shape==(2,c['time']['T']);assert np.max(leakage_fraction(u,c['time']['burn_in'],c['stimuli']['train_multisine_frequencies']))<1e-8
def test_shared_simulation_finite():
 c=cfg();u=np.zeros((2,c['time']['T']));x=simulate(u,np.array([1,2]),c,'shared_boundary');assert np.isfinite(x['M_V']).all() and np.isfinite(x['M_O']).all()
def test_adversarial_is_structurally_separate():
 c=cfg();u=np.zeros((1,c['time']['T']));a=simulate(u,np.array([4]),c,'adversarial_mimic',False,noise_code=10);b=simulate(u,np.array([4]),c,'adversarial_mimic',True,noise_code=10);assert np.allclose(a['M_V'],b['M_V']) and np.allclose(a['M_O'],b['M_O'])
