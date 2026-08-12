from pathlib import Path
import importlib.util
import yaml

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('r2',ROOT/'pilot_engine.py')
r2=importlib.util.module_from_spec(spec);spec.loader.exec_module(r2)

def cfg(): return yaml.safe_load((ROOT/'preregistration'/'ph_v031_r2.yaml').read_text())

def test_seed_deterministic_and_fresh():
    c=cfg();a,_=r2.seed_for(c,'pilot','shared_boundary','compound',0);b,_=r2.seed_for(c,'pilot','shared_boundary','compound',0)
    assert a==b
    assert not any(lo<=a<=hi for lo,hi in c['seed_registry']['forbidden_ranges'])

def test_generate_first_pairing_hash_is_strength_invariant():
    c=cfg();s,_=r2.seed_for(c,'pilot','shared_boundary','compound',1);b=r2.bundle(s,len(c['lambdas']['all']));h=r2.bhash(b)
    r2.simulate(b,c,'shared_boundary','compound',0.0);r2.simulate(b,c,'shared_boundary','compound',1.0)
    assert r2.bhash(b)==h

def test_raw_saturation_is_not_k_saturation():
    c=cfg();arr,_,_=r2.data(c,'adversarial_clamp_mimic')
    _,_,_,_,clip_v,clip_o=arr
    assert clip_v.mean()<0.05 and clip_o.mean()<0.05
