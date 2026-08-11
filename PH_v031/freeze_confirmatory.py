from pathlib import Path
import pandas as pd
from experiment import load_config,make_freeze
ROOT=Path(__file__).resolve().parent
cfg=load_config(ROOT/'preregistration'/'ph_v031.yaml')
core=pd.read_csv(ROOT/'results'/'pilot_core_summary.csv');rob=pd.read_csv(ROOT/'results'/'pilot_robustness_curve.csv')
fr=make_freeze(ROOT,cfg,core,rob);print(fr['freeze_sha256'])
