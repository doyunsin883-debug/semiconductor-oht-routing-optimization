from pathlib import Path
import sys,json,time
sys.path.insert(0,str(Path(__file__).parent/'src'))
from phase3 import PartialSimulator,train,FullSimulator,BASE_GRAPH,CLOSED_EDGE,QPolicy
import pandas as pd,numpy as np
from scipy.stats import binomtest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
BASE=Path(__file__).parent
OUT=BASE/'results';OUT.mkdir(exist_ok=True)
SEEDS=list(range(40001,40041)); SCENARIOS=('normal','surge','closure')
POLICIES=('full_atomic_dynamic','partial_shortest','partial_dynamic','partial_rl_untrained','partial_rl_trained')

t0=time.time();a=train(episodes=120,seed=1500,duration_s=800)
print('Training completed:',a.updates,'updates',len(a.q),'Q entries','elapsed',time.time()-t0,flush=True)
records=[];traces=[]
for sc in SCENARIOS:
 for seed in SEEDS:
  for pol in POLICIES:
   if pol=='full_atomic_dynamic':
    v=FullSimulator(sc,'dynamic',seed=seed,duration_s=1500).run();met=v.metrics()
    record=dict(scenario=sc,policy=pol,seed=seed,generated=met['generated'],completed=met['completed'],
        unfinished=met['unfinished'],completion_rate=met['completion_rate'],lead_mean=met['mean_lead_s'],
        lead_p95=met['p95_lead_s'],waiting_s=met['waiting_vehicle_s'],blocked_events=met['denied'],
        cycle_prevented=0,wait_cycles_seen=0,violations=met['safety_violations'],max_concurrent=None,moves=met['route_grants'])
   else:
    agent=a if pol=='partial_rl_trained' else QPolicy(seed=25)
    v=PartialSimulator(sc,pol,seed=seed,agent=agent,duration_s=1500).run()
    record=v.metrics()
   records.append(record)
 print('Completed scenario:',sc,'after',round(time.time()-t0,1),'seconds',flush=True)

df=pd.DataFrame(records);df.to_csv(OUT/'heldout_600_runs.csv',index=False)
summary=(df.groupby(['scenario','policy'],as_index=False).agg(n=('seed','nunique'),generated_mean=('generated','mean'),
    completed_mean=('completed','mean'),completed_sd=('completed','std'),unfinished_mean=('unfinished','mean'),
    completion_rate_mean=('completion_rate','mean'),wait_s_mean=('waiting_s','mean'),lead_mean=('lead_mean','mean'),
    p95_mean=('lead_p95','mean'),blocked_mean=('blocked_events','mean'),cycle_prevented_sum=('cycle_prevented','sum'),
    wait_cycles_seen_sum=('wait_cycles_seen','sum'),violations=('violations','sum')))
summary.to_csv(OUT/'summary_600.csv',index=False)
comparisons=[('partial_dynamic','full_atomic_dynamic'),('partial_dynamic','partial_shortest'),('partial_rl_trained','partial_rl_untrained')]
rg=np.random.default_rng(3333);out=[]
for sc in SCENARIOS:
 sub=df[df.scenario==sc].pivot(index='seed',columns='policy',values='completed')
 for treat,base in comparisons:
  dif=(sub[treat]-sub[base]).to_numpy(float)
  bs=np.mean(rg.choice(dif,(18000,len(dif)),replace=True),axis=1)
  pos=int(sum(dif>0));neg=int(sum(dif<0));tie=int(sum(dif==0))
  pv=binomtest(pos,pos+neg).pvalue if pos+neg else 1.
  out.append(dict(scenario=sc,comparison=f'{treat} - {base}',n_pairs=len(dif),mean_difference=float(dif.mean()),
      ci_low=float(np.percentile(bs,2.5)),ci_high=float(np.percentile(bs,97.5)),
      positives=pos,negatives=neg,ties=tie,p_sign=pv))
# holm correction across 9 pre-registered contrasts
ids=sorted(range(len(out)),key=lambda i:out[i]['p_sign']);maxadj=0.
for j,i in enumerate(ids):
 maxadj=max(maxadj,min(1.,(len(out)-j)*out[i]['p_sign']))
 out[i]['holm9']=maxadj
pd.DataFrame(out).to_csv(OUT/'paired_inference.csv',index=False)

# Scenario trace — actual simulator state, not independently invented animation
sim=PartialSimulator('normal','partial_dynamic',seed=40017,duration_s=800,agent=a,trace=True).run()
(OUT/'trace_800.json').write_text(json.dumps(sim.trace_points,ensure_ascii=False,separators=(',',':')),encoding='utf8')
(OUT/'model_q.json').write_text(json.dumps([{'s':list(k[0]),'a':k[1],'q':v} for k,v in a.q.items()]),encoding='utf8')
metadata=dict(date='2026-10-25',phase='3',network=dict(nodes=len(BASE_GRAPH),edges=len(BASE_GRAPH.edges)),
    conditions='same network and Poisson requests, seed common across policies',seeds=[SEEDS[0],SEEDS[-1]],
    training_seeds=[1500,1619],training_episodes=120,training_updates=a.updates,training_q_states=len(a.q),
    eval_runs=len(records),duration_s=1500,n_vehicles=9,scenarios=SCENARIOS,policies=POLICIES,
    limitations='Synthetic. Conservative lookahead WFG guard not industrial deadlock proof; independent synthetic reports, no fab access.',
    metrics='Jobs completed in 25m, denied node grants, vehicle waiting seconds, completed-only lead time subject to censoring')
(OUT/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')

fig,ax=plt.subplots(figsize=(11.3,5.2))
for i,pol in enumerate(POLICIES):
 y=[summary[(summary.scenario==s)&(summary.policy==pol)].completed_mean.iloc[0] for s in SCENARIOS]
 ax.bar(np.arange(3)+(.16*(i-2)),y,width=.15,label=pol.replace('partial_','').replace('full_atomic_dynamic','full-route'))
ax.set_xticks(np.arange(3),['Normal','Demand surge','Link closure']);ax.set_ylabel('Jobs completed in 25min')
ax.set_title('Full-route atomic versus local segment reservation (40 paired seeds per scenario)');ax.legend(fontsize=8,ncols=3,loc='upper left');ax.grid(axis='y',alpha=.2)
fig.tight_layout();fig.savefig(OUT/'completed_600.png',dpi=150);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,5.5));
for i,r in enumerate(out):
 ax.plot([r['ci_low'],r['ci_high']],[i,i],lw=3);ax.scatter([r['mean_difference']],[i],s=24)
ax.axvline(0,linestyle='--',color='gray');ax.set_yticks(range(len(out)),[f"{r['scenario']} : {r['comparison']}" for r in out],fontsize=8)
ax.invert_yaxis();ax.set_xlabel('Paired difference in jobs completed (95% CI)');ax.set_title('Prespecified contrasts, bootstrap over paired seeds');ax.grid(axis='x',alpha=.3)
fig.tight_layout();fig.savefig(OUT/'paired_600.png',dpi=150);plt.close(fig)
print('
---- SUMMARY ----
',summary.to_string(index=False,float_format=lambda x:f'{x:.3f}'))
print('
---- INFERENCE ----
',pd.DataFrame(out).to_string(index=False,float_format=lambda x:f'{x:.4f}'))
print('TOTAL ELAPSED',time.time()-t0,flush=True)
