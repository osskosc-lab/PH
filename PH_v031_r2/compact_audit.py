from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parent
def compact_outputs():
 p=ROOT/'results'/'pilot_seed_registry.csv';df=pd.read_csv(p);rows=[]
 for r in df.itertuples():
  seeds=json.loads(r.seeds_json);rows.append({'stage':r.stage,'mode':r.mode,'condition':r.condition,'n':r.n,'seed_formula':'SHA256(version|stage|mode|condition|index)->uint32','first_seed':seeds[0],'last_seed':seeds[-1],'group_sha256':r.group_sha256})
 pd.DataFrame(rows).to_csv(p,index=False)
 rp=ROOT/'results'/'rng_manifest.json';obj=json.loads(rp.read_text())
 for g in obj['groups']:
  g.pop('first_bundle_sha256',None);g.pop('last_bundle_sha256',None)
 rp.write_text(json.dumps(obj,separators=(',',':')))
if __name__=='__main__':compact_outputs()
