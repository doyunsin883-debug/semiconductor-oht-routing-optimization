"""Phase 2 OHT: directed one-way FAB + atomic full-leg route reservations.

Scope: deliberately conservative deadlock-free transport planning, synthetic data.
No equipment-level safety certification. Uses route-level contextual-bandit Q updates
with gamma=0 (one-step episodic Q learning). This IS NOT multi-agent deep RL.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from functools import lru_cache
from collections import Counter
import math, random
import numpy as np
import networkx as nx

ROWS,COLS=6,8
V=4.0
A=0.8
SPACING=30.0
N_VEHICLES=9
STATIONS=(0,5,10,15,18,23,24,29,34,39,42,47)
CLOSED_EDGE=(19,27) # selected below (actual verified outgoing edge)


def travel_time(length:float, v:float=V, a:float=A)->float:
    if length<=0 or v<=0 or a<=0: raise ValueError('positive dynamics required')
    return 2*math.sqrt(length/a) if length<=v*v/a else 2*v/a+(length-v*v/a)/v


def graph_build():
    g=nx.DiGraph()
    for r in range(ROWS):
      for c in range(COLS):
        n=r*COLS+c
        g.add_node(n,x=c*SPACING,y=r*SPACING,station=n in STATIONS)
    for r in range(ROWS):
      for c in range(COLS):
        n=r*COLS+c
        if c<COLS-1:
          m=n+1;u,v=(n,m) if r%2==0 else (m,n)
          limit=3.0 if r in (2,3) else 4.0
          g.add_edge(u,v,travel_s=travel_time(SPACING,limit),length_m=SPACING,speed_limit=limit,kind='horizontal')
        if r<ROWS-1:
          m=n+COLS;u,v=(m,n) if c%2==0 else (n,m)
          limit=3.2 if c in (3,4) else 4.0
          g.add_edge(u,v,travel_s=travel_time(SPACING,limit),length_m=SPACING,speed_limit=limit,kind='vertical')
    assert nx.is_strongly_connected(g)
    return g

BASE_GRAPH=graph_build()
# pick a central edge whose removal keeps route access between all stations
CENTRAL_EDGES=[(u,v) for u,v in BASE_GRAPH.edges if 1<=u//COLS<=4 and 2<=u%COLS<=5]
CLOSED_EDGE=(19,27)  # vertical one-way crossover close to FAB center; remains connected
assert BASE_GRAPH.has_edge(*CLOSED_EDGE) and nx.is_strongly_connected(nx.restricted_view(BASE_GRAPH,[],[CLOSED_EDGE]))

@lru_cache(maxsize=6)
def scenario_graph(scenario):
    g=BASE_GRAPH.copy()
    if scenario=='closure':g.remove_edge(*CLOSED_EDGE)
    assert nx.is_strongly_connected(g), 'closure case would disconnect rail graph'
    return g

@lru_cache(maxsize=3000)
def paths(scenario,source,target,k=4):
    if source==target:return ((source,),)
    g=scenario_graph(scenario)
    from itertools import islice
    return tuple(tuple(p) for p in islice(nx.shortest_simple_paths(g,source,target,weight='travel_s'),k))

def duration(scenario,path):
    g=scenario_graph(scenario)
    return sum(g.edges[u,v]['travel_s'] for u,v in zip(path,path[1:]))

def resources(path):
    # No vehicle can hold a segment/junction already reserved by another.
    # Entire route reserved atomically; off-track station sidings are not locked.
    return frozenset(('N',int(n)) for n in path)|frozenset(('E',int(u),int(v)) for u,v in zip(path,path[1:]))

@dataclass
class Request:
    id:int
    created:int
    source:int
    target:int
    assigned:int|None=None
    delivered:int|None=None
    picked:int|None=None

@dataclass
class Vehicle:
    id:int
    node:int
    phase:str='idle'
    job:int|None=None
    until:int=0
    route:tuple=()
    started:int=0
    reserved:frozenset=field(default_factory=frozenset)
    decision:tuple|None=None
    wait:int=0
    moves:int=0

class RouteQLearner:
    """One-step episodic tabular Q (gamma=0) at each route grant.
    The RL is confined to choice among routes satisfying the same safety rules.
    """
    def __init__(self,seed=10):
        self.q={};self.rng=random.Random(seed);self.updates=0
    @staticmethod
    def state(source,target,active,scenario):
        return (source//COLS//2,target%COLS//2,min(2,active//3),int(scenario!='normal'))
    def choose(self,st,options,costs,explore=False):
        if explore and self.rng.random()<.24:return self.rng.choice(options)
        return max(options,key=lambda j:(self.q.get((st,j),0)-.028*costs[j],-j))
    def learn(self,st,action,elapsed,shortest_duration):
        key=(st,action);old=self.q.get(key,0.0)
        # Cost per leg, normalized relative to uncongested shortest path (s)
        reward=-(elapsed-shortest_duration)/12.0
        self.q[key]=old+.16*(reward-old)
        self.updates+=1

class Simulator:
    def __init__(self,scenario='normal',policy='shortest',seed=20001,duration_s=1500,demand_hour=68,
                 n_vehicles=N_VEHICLES,agent=None,training=False,trace=False,atomic=True):
        if scenario not in ('normal','surge','closure'):raise ValueError('scenario')
        if policy not in ('shortest','dynamic','rl_untrained','rl_trained'):raise ValueError('policy')
        self.scenario,self.policy,self.seed=scenario,policy,seed
        self.duration_s,self.demand_hour=duration_s,demand_hour*(1.5 if scenario=='surge' else 1)
        self.n_vehicles=n_vehicles;self.training=training;self.atomic=atomic;self.trace=trace
        self.g=scenario_graph(scenario);self.agent=agent or RouteQLearner(seed)
        self.requests=self._make_requests(seed)
        self.vehicles=[Vehicle(i,STATIONS[i%len(STATIONS)]) for i in range(n_vehicles)]
        self.reserved={};self.denied=0;self.safety_violations=0;self.deadlocks=0;self.route_grants=0
        self.trace_points=[];self.max_wait=0
    def _make_requests(self,seed):
        rng=np.random.default_rng(seed+115);t=0.0;arr=[]
        while True:
            t+=float(rng.exponential(3600/self.demand_hour))
            if t>=self.duration_s:break
            a,b=rng.choice(STATIONS,2,replace=False)
            arr.append(Request(len(arr),int(t),int(a),int(b)))
        return arr
    def _target(self,v):
        r=self.requests[v.job]
        return r.source if v.phase=='pickup' else r.target
    def _grant(self,v,t):
        target=self._target(v);p=paths(self.scenario,v.node,target)
        if v.node==target:
            self._service(v,t);return
        active=sum(w.phase!='idle' for w in self.vehicles)
        st=self.agent.state(v.node,target,active,self.scenario)
        feasible=[(j,route) for j,route in enumerate(p) if all(res not in self.reserved for res in resources(route))]
        if not feasible:
            v.wait+=1;self.denied+=1;return
        costs=[duration(self.scenario,x) for x in p]
        if self.policy=='shortest':
            # Intentional contrast: fixed first route, waits even when another is free.
            j,path=next(((j,x) for j,x in feasible if j==0),(None,None))
            if j is None:v.wait+=1;self.denied+=1;return
        elif self.policy=='dynamic':
            j,path=min(feasible,key=lambda item:(costs[item[0]],item[0]))
        else:
            options=[j for j,x in feasible]
            j=self.agent.choose(st,options,costs,explore=self.training and self.policy=='rl_trained')
            path=p[j]
        lock=resources(path)
        if any(res in self.reserved for res in lock):raise AssertionError('atomic grant conflicted')
        for res in lock:self.reserved[res]=v.id
        v.reserved=lock;v.route=path;v.started=t;v.until=t+math.ceil(costs[j]);v.phase=v.phase+'_moving'
        v.decision=(st,j,costs[0]);v.moves+=1;self.route_grants+=1
    def _service(self,v,t):
        v.phase=v.phase.replace('_moving','')
        if v.phase=='pickup':v.phase='pickup_service';v.until=t+6
        elif v.phase=='dropoff':v.phase='dropoff_service';v.until=t+8
        else:raise AssertionError('bad phase')
    def _finish_leg(self,v,t):
        assert v.phase.endswith('_moving')
        if any(self.reserved.get(res)!=v.id for res in v.reserved):
            self.safety_violations+=1;raise AssertionError('reservation ownership')
        for res in v.reserved:del self.reserved[res]
        v.reserved=frozenset();v.node=v.route[-1]
        st,action,baseline=v.decision
        if self.training and self.policy=='rl_trained':self.agent.learn(st,action,t-v.started,baseline)
        v.route=();v.decision=None
        self._service(v,t)
    def _complete_service(self,v,t):
        r=self.requests[v.job]
        if v.phase=='pickup_service':r.picked=t;v.phase='dropoff'
        else:r.delivered=t;v.phase='idle';v.job=None
    def _snapshot(self,t):
        if not self.trace:return
        for v in self.vehicles:
            if v.phase.endswith('_moving') and v.route:
                elapsed=t-v.started
                acc=0.;route=v.route
                x,y=self.g.nodes[route[0]]['x'],self.g.nodes[route[0]]['y']
                for u,w in zip(route,route[1:]):
                    dt=self.g.edges[u,w]['travel_s']
                    if elapsed<=acc+dt:
                        progress=max(0,min(1,(elapsed-acc)/dt))
                        x=self.g.nodes[u]['x']*(1-progress)+self.g.nodes[w]['x']*progress
                        y=self.g.nodes[u]['y']*(1-progress)+self.g.nodes[w]['y']*progress
                        break
                    acc+=dt
            else:x,y=self.g.nodes[v.node]['x'],self.g.nodes[v.node]['y']
            self.trace_points.append({'t':t,'vehicle':v.id,'x':round(x,2),'y':round(y,2),'phase':v.phase})
    def run(self):
        arrivals=0;queue=[]
        for t in range(self.duration_s+1):
            while arrivals<len(self.requests) and self.requests[arrivals].created<=t:
                queue.append(arrivals);arrivals+=1
            for v in self.vehicles:
                if v.phase.endswith('_moving') and v.until<=t:self._finish_leg(v,t)
                elif v.phase in ('pickup_service','dropoff_service') and v.until<=t:self._complete_service(v,t)
            while queue:
                idle=[v for v in self.vehicles if v.phase=='idle']
                if not idle:break
                rid=queue.pop(0);r=self.requests[rid]
                v=min(idle,key=lambda w:(len(paths(self.scenario,w.node,r.source)[0]),w.id))
                v.phase='pickup';v.job=rid;r.assigned=t
            # Rotate vehicle grant priority across time to avoid permanent ID ordering.
            for i in range(self.n_vehicles):
                v=self.vehicles[(i+t)%self.n_vehicles]
                if v.phase in ('pickup','dropoff'):self._grant(v,t)
            if self.trace and t%10==0:self._snapshot(t)
            # Uniqueness is guaranteed by dictionary, but validate active reservations.
            union=[res for v in self.vehicles for res in v.reserved]
            if len(union)!=len(set(union)):
                self.safety_violations+=1;raise AssertionError('overlap')
        return self
    def metrics(self):
        finished=[r for r in self.requests if r.delivered is not None]
        lat=[r.delivered-r.created for r in finished]
        return dict(scenario=self.scenario,policy=self.policy,seed=self.seed,generated=len(self.requests),
            completed=len(finished),unfinished=len(self.requests)-len(finished),
            completion_rate=len(finished)/len(self.requests) if self.requests else 1,
            mean_lead_s=float(np.mean(lat)) if lat else None,p95_lead_s=float(np.percentile(lat,95)) if lat else None,
            denied=self.denied,safety_violations=self.safety_violations,
            route_grants=self.route_grants,waiting_vehicle_s=sum(v.wait for v in self.vehicles))

def train(episodes=50,seed=4200,duration=1100):
    agent=RouteQLearner(seed)
    for ep in range(episodes):
        scen=('normal','surge','closure')[ep%3]
        Simulator(scen,'rl_trained',seed+ep,duration,agent=agent,training=True).run()
    return agent

def benchmark(agent,seeds,scenarios=('normal','surge','closure'),duration=1500):
    records=[]
    for s in scenarios:
      for seed in seeds:
        for policy in ['shortest','dynamic','rl_untrained','rl_trained']:
            a=agent if policy=='rl_trained' else RouteQLearner(seed=1)
            sim=Simulator(s,policy,seed,duration,agent=a).run()
            records.append(sim.metrics())
    return records
