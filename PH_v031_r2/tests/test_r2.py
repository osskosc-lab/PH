from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ph_v031_r2 import seed32,rng_bundle,rng_hash,load_cfg,seed_registry,overlap_count
def test_seed_deterministic():assert seed32('PH-v0.3.1-r2','pilot','shared_boundary','core|official1',1)==seed32('PH-v0.3.1-r2','pilot','shared_boundary','core|official1',1)
def test_rng_pairing():assert rng_hash(rng_bundle(123))==rng_hash(rng_bundle(123))
def test_fresh_seed_registry():
 c=load_cfg();r=seed_registry(c,'pilot');assert overlap_count(r.seed,c['legacy_seed_ranges'])==0
