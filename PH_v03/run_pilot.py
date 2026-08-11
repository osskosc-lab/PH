from pathlib import Path
from experiment import load_config,run_stage
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    cfg=load_config(ROOT/'preregistration'/'ph_v03.yaml')
    s,_=run_stage(cfg,'pilot',ROOT/'results')
    print(s[['mode','positive_seed_rate','K_V','K_O','R_OOD','representation_pass']].to_string(index=False))
