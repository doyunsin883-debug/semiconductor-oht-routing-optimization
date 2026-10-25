from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent/'src'))
import pandas as pd
from phase3 import PartialSimulator
out=Path(__file__).parent/'results'
rows=[]
for sc in ('normal','surge','closure'):
 for n in (6,9,12):
  for useguard in (False,True):
   for seed in range(50001,50021):
    sim=PartialSimulator(sc,'partial_shortest',seed=seed,n_vehicles=n,duration_s=1500,avoidance=useguard).run()
    d=sim.metrics();d['guard']=useguard;d['n_vehicles']=n;rows.append(d)
df=pd.DataFrame(rows);df.to_csv(out/'guard_ablation_360.csv',index=False)
print(df.groupby(['scenario','n_vehicles','guard']).agg(completed_mean=('completed','mean'),wait_cycles_mean=('wait_cycles_seen','mean'),guard_prevents=('cycle_prevented','sum'),violations=('violations','sum')).to_string())
