"""FAB FLOW Phase 3 | partial segment reservations + wait-for graph.
Synthetic one-way OHT graph; node-level mutual exclusion, simulated travel ticks.
Education/research prototype, NOT physical OHT safety assurance.
"""
from __future__ import annotations
import sys, math, random
from pathlib import Path
from functools import lru_cache
from collections import defaultdict
from dataclasses import dataclass
import numpy as np
import networkx as nx
from phase2_reference import BASE_GRAPH,scenario_graph,STATIONS,CLOSED_EDGE,travel_time,Simulator as FullSimulator,paths

POLICIES=('partial_shortest','partial_dynamic','partial_rl_untrained','partial_rl_trained')

@lru_cache(maxsize=20000)
def candidate_paths(scenario,src,dst,k=5):
    if src==dst:return ((src,),)
    return paths(scenario,src,dst,k)

@lru_cache(maxsize=4)
def directed_cycles(scenario):
    return tuple(frozenset(c) for c in nx.simple_cycles(scenario_graph(scenario),length_bound=12))

def detect_wait_cycles(wait_edges):
    """Only vehicle->vehicle dependencies. Exclude occupied objects that are moving."""
    wg=nx.DiGraph()
    wg.add_edges_from((int(a),int(b)) for a,b in wait_edges if a!=b)
    return list(nx.simple_cycles(wg))

@dataclass
class Car:
    id:int
    node:int
    stage:str='idle'
    job:int=-1
    until:int=0
    target:int=-1
    upcoming:int=-1
    route:tuple=()
    pos:int=0
    last_decision:tuple|None=None
    denied:int=0
    waiting:int=0
    distance:float=0.
    arrived:int=0
    current_edge:tuple|None=None

class QPolicy:
    def __init__(self,seed=21):
        self.q={};self.rng=random.Random(seed);self.updates=0
    @staticmethod
    def key(node,target,scenario,busy):
        return (node,target//8//2,target%8//2,int(scenario!='normal'),min(3,busy//3))
    def val(self,key,neighbor):return self.q.get((key,neighbor),0.)
    def update(self,key,action,reward,next_key,next_actions,terminal=False):
        bootstrap=0 if terminal or not next_actions else max(self.val(next_key,n) for n in next_actions)
        old=self.val(key,action)
        self.q[key,action]=old+.22*(reward+.87*bootstrap-old)
        self.updates+=1

class PartialSimulator:
    def __init__(self,scenario='normal',policy='partial_dynamic',seed=30001,duration_s=1500,
                 n_vehicles=9,demand_hour=68,agent=None,training=False,trace=False,
                 avoidance=True):
        if policy not in POLICIES:raise ValueError('invalid policy')
        if scenario not in ('normal','surge','closure'):raise ValueError('invalid scenario')
        self.scenario,self.policy,self.seed=scenario,policy,seed
        self.duration_s=duration_s;self.n_vehicles=n_vehicles;self.training=training
        self.trace=trace;self.avoidance=avoidance
        self.graph=scenario_graph(scenario)
        self.agent=agent or QPolicy(seed)
        self.cars=[Car(i,STATIONS[i%len(STATIONS)]) for i in range(n_vehicles)]
        self.requests=self._make_requests(seed,duration_s,demand_hour*(1.5 if scenario=='surge' else 1))
        self.node_owner={};self.target_reservation={};self.edge_owner={}
        self.pending=[];self.arrivals=0;self.trace_points=[]
        self.block_events=0;self.wait_cycles_seen=0;self.cycle_prevented=0
        self.unsafe_grants=0;self.violations=0;self.moves=0;self.max_concurrent=0;self.max_wait_chain=0
        self.waiting_samples=[];self.path_changes=0
    @staticmethod
    def _make_requests(seed,duration_s,rate):
        rng=np.random.default_rng(seed+115);t=0.;jobs=[]
        while True:
            t+=float(rng.exponential(3600/rate))
            if t>=duration_s:break
            src,dst=rng.choice(STATIONS,2,replace=False)
            jobs.append(dict(id=len(jobs),created=int(t),source=int(src),target=int(dst),assigned=None,picked=None,delivered=None))
        return jobs
    def _other_options(self,c):
        """Return shortest simple paths, ranked by prefix but never violate one-way edges."""
        target=c.target
        if c.node==target:return []
        pp=candidate_paths(self.scenario,c.node,target)
        return [(i,p) for i,p in enumerate(pp) if len(p)>1]
    def _active_count(self):return sum(c.stage!='idle' for c in self.cars)
    def _edge_time(self,u,v):return math.ceil(self.graph.edges[u,v]['travel_s'])
    def _path_cost(self,p):return sum(self.graph.edges[u,v]['travel_s'] for u,v in zip(p,p[1:]))
    def _blocked(self,c,nxt):
        if (c.node,nxt) in self.edge_owner:return self.edge_owner[(c.node,nxt)]
        if nxt in self.node_owner and self.node_owner[nxt]!=c.id:return self.node_owner[nxt]
        if nxt in self.target_reservation and self.target_reservation[nxt]!=c.id:return self.target_reservation[nxt]
        return None
    def _predicted_deadlock(self,c,nxt):
        """Wait-for graph lookahead: refuse a grant if it would leave a
        fully occupied *next-hop dependency cycle* at the next junction.
        Uses intended shortest next hops, and is conservative, not a proof of
        global no-deadlock under every physical control policy.
        """
        if not self.avoidance:return False
        # Maintain at least one free position on each short directed loop.
        # This is a local operational safeguard (not industrial verification).
        occupied=(set(self.node_owner)|set(self.target_reservation))
        if self.node_owner.get(c.node)==c.id:occupied.discard(c.node)
        occupied.add(nxt)
        if any(cycle.issubset(occupied) for cycle in directed_cycles(self.scenario)):
            return True
        poss={car.id:car.node for car in self.cars
              if self.node_owner.get(car.node)==car.id and car.id!=c.id}
        poss[c.id]=nxt
        owners={n:i for i,n in poss.items()}
        deps=[]
        for car in self.cars:
            if car.id not in poss:continue
            at=poss[car.id]
            if at==car.target or car.target<0:continue
            pp=candidate_paths(self.scenario,at,car.target)
            if not pp or len(pp[0])<2:continue
            want=pp[0][1]
            if want in owners and owners[want]!=car.id:
                deps.append((car.id,owners[want]))
        return bool(detect_wait_cycles(deps))
    def _choose(self,c,feasible,opts):
        if not feasible:return None
        if self.policy=='partial_shortest':
            return next(((i,p) for i,p in feasible if i==0),None)
        if self.policy=='partial_dynamic':
            return min(feasible,key=lambda t:(self._path_cost(t[1]),t[0]))
        key=self.agent.key(c.node,c.target,self.scenario,self._active_count())
        # Safe RL action shield: forbid detours more than 30% above the
        # shortest feasible remainder; clamp Q residual contribution.
        minimum=min(self._path_cost(p) for _,p in feasible)
        shield=[(j,p) for j,p in feasible if self._path_cost(p)<=1.30*minimum +1e-9]
        if self.training and self.policy=='partial_rl_trained' and self.agent.rng.random()<.20:
            return self.agent.rng.choice(shield)
        return max(shield,key=lambda item:(
            -.025*self._path_cost(item[1])
            +.35*max(-2.,min(2.,self.agent.val(key,item[1][1]))),
            -item[0]))
    def _start(self,c,t):
        opts=self._other_options(c)
        if not opts:
            if c.node==c.target:self._arrive(c,t)
            else:self.violations+=1
            return
        feas=[];wg=[]
        for idx,p in opts:
            dest=p[1]
            owner=self._blocked(c,dest)
            if owner is None:
                feas.append((idx,p))
            else:wg.append((c.id,owner))
        selected=self._choose(c,feas,opts)
        if selected is None:
            c.waiting+=1;c.denied+=1;self.block_events+=1
            return
        idx,path=selected;nxt=path[1]
        c.route=tuple(path);c.pos=0
        if self._predicted_deadlock(c,nxt):
            self.cycle_prevented+=1;c.waiting+=1;c.denied+=1
            return
        # atomic node claim; source node stays owned until movement finishes
        if nxt in self.node_owner or nxt in self.target_reservation:
            self.unsafe_grants+=1;raise AssertionError('node double reservation')
        self.target_reservation[nxt]=c.id
        self.edge_owner[c.node,nxt]=c.id
        key=self.agent.key(c.node,c.target,self.scenario,self._active_count())
        c.last_decision=(key,nxt,t)
        c.upcoming=nxt;c.current_edge=(c.node,nxt);c.until=t+self._edge_time(c.node,nxt)
        c.stage=c.stage.replace('_waiting','')+'_moving'
        self.moves+=1
    def _arrive(self,c,t):
        assert c.node==c.target
        # A siding vehicle must never release another vehicle's occupied track node.
        if self.node_owner.get(c.node)==c.id:
            del self.node_owner[c.node]
        c.route=();c.pos=0
        c.stage=('pickup_service' if c.stage.startswith('pickup') else 'dropoff_service')
        c.until=t+(6 if c.stage=='pickup_service' else 8)
    def _finish_segment(self,c,t):
        u,v=c.current_edge
        assert self.target_reservation.get(v)==c.id
        assert self.edge_owner.get((u,v))==c.id
        del self.target_reservation[v];del self.edge_owner[u,v]
        if self.node_owner.get(u)==c.id:del self.node_owner[u]
        if v in self.node_owner:raise AssertionError('occupied destination')
        c.node=v;self.node_owner[v]=c.id;c.current_edge=None;c.upcoming=-1
        c.stage=c.stage.replace('_moving','')
        if self.training and self.policy=='partial_rl_trained' and c.last_decision:
            key,action,depart=c.last_decision
            terminal=(c.node==c.target)
            next_key=self.agent.key(c.node,c.target,self.scenario,self._active_count())
            next_actions=[p[1] for _,p in self._other_options(c)] if not terminal else []
            self.agent.update(key,action,-float(t-depart),next_key,next_actions,terminal)
        c.last_decision=None
        if c.node==c.target:self._arrive(c,t)
    def _service_done(self,c,t):
        j=self.requests[c.job]
        if c.stage=='pickup_service':
            j['picked']=t;c.stage='dropoff';c.target=j['target']
        else:
            j['delivered']=t;c.stage='idle';c.job=-1;c.target=-1
    def _snapshot(self,t):
        if not self.trace:return
        for c in self.cars:
            x,y=self.graph.nodes[c.node]['x'],self.graph.nodes[c.node]['y']
            if c.current_edge:
                u,v=c.current_edge
                dur=self._edge_time(u,v)
                f=1-max(0,c.until-t)/dur
                x=x*(1-f)+self.graph.nodes[v]['x']*f
                y=y*(1-f)+self.graph.nodes[v]['y']*f
            self.trace_points.append(dict(t=t,vehicle=c.id,x=round(x,3),y=round(y,3),stage=c.stage,job=c.job))
    def run(self):
        for t in range(self.duration_s+1):
            while self.arrivals<len(self.requests) and self.requests[self.arrivals]['created']<=t:
                self.pending.append(self.arrivals);self.arrivals+=1
            for c in self.cars:
                if c.stage.endswith('_moving') and c.until<=t:self._finish_segment(c,t)
                elif c.stage in ('pickup_service','dropoff_service') and c.until<=t:self._service_done(c,t)
            while self.pending:
                idle=[c for c in self.cars if c.stage=='idle']
                if not idle:break
                rid=self.pending.pop(0);j=self.requests[rid]
                car=min(idle,key=lambda c: (self._path_cost(candidate_paths(self.scenario,c.node,j['source'])[0]),c.id))
                car.stage='pickup';car.job=rid;car.target=j['source'];j['assigned']=t
            # release stations from track after service; station siding does not consume node
            for offset in range(self.n_vehicles):
                c=self.cars[(t+offset)%self.n_vehicles]
                if c.stage in ('pickup','dropoff'):
                    if c.node==c.target:self._arrive(c,t)
                    elif c.node not in self.node_owner:
                        # vehicle at off-track siding: does not block other vehicles at station
                        pass
                    self._start(c,t) if c.stage in ('pickup','dropoff') else None
            # WFG over vehicles that are occupying nodes and waiting for target
            wg=[]
            for c in self.cars:
                if c.stage in ('pickup','dropoff') and c.node in self.node_owner and self.node_owner[c.node]==c.id:
                    for _,p in self._other_options(c)[:1]:
                        own=self._blocked(c,p[1]);
                        if own is not None:wg.append((c.id,own))
            cycles=detect_wait_cycles(wg)
            if cycles:self.wait_cycles_seen+=1
            self.max_wait_chain=max(self.max_wait_chain,len(wg))
            if self.trace and t%8==0:self._snapshot(t)
            self.max_concurrent=max(self.max_concurrent,len(self.edge_owner))
            occ=list(self.node_owner.values())
            if len(occ)!=len(set(occ)) or any(n in self.node_owner and self.node_owner[n]!=i for n,i in self.target_reservation.items()):
                self.violations+=1;raise AssertionError('unsafe double node grant')
        return self
    def metrics(self):
        done=[j for j in self.requests if j['delivered'] is not None]
        lead=[j['delivered']-j['created'] for j in done]
        return dict(scenario=self.scenario,policy=self.policy,seed=self.seed,generated=len(self.requests),completed=len(done),
            unfinished=len(self.requests)-len(done),completion_rate=len(done)/len(self.requests) if self.requests else 1.,
            lead_mean=float(np.mean(lead)) if lead else float('nan'),lead_p95=float(np.percentile(lead,95)) if lead else float('nan'),
            waiting_s=sum(c.waiting for c in self.cars),blocked_events=self.block_events,cycle_prevented=self.cycle_prevented,
            wait_cycles_seen=self.wait_cycles_seen,violations=self.violations,max_concurrent=self.max_concurrent,moves=self.moves)

def train(episodes=90,seed=1400,duration_s=750):
    a=QPolicy(seed)
    for ep in range(episodes):
        s=['normal','surge','closure'][ep%3]
        PartialSimulator(s,'partial_rl_trained',seed=seed+ep,duration_s=duration_s,agent=a,training=True).run()
    return a
