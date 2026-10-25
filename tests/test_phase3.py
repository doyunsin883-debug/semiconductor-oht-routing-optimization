import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'src'))
import networkx as nx
from phase3 import PartialSimulator,detect_wait_cycles,train,scenario_graph,CLOSED_EDGE

def test_graph_direction():
    assert len(scenario_graph('normal'))==48
    assert len(scenario_graph('normal').edges)==82
    assert not scenario_graph('closure').has_edge(*CLOSED_EDGE)
    assert nx.is_strongly_connected(scenario_graph('closure'))

def test_wait_for_cycle_detection():
    assert not detect_wait_cycles([(0,1),(1,2),(2,3)])
    assert detect_wait_cycles([(0,1),(1,2),(2,0)])
    assert not detect_wait_cycles([(0,1),(1,2),(2,9)])

def test_no_double_node_occupancy():
    for s in ('normal','surge','closure'):
        for p in ('partial_shortest','partial_dynamic','partial_rl_untrained','partial_rl_trained'):
            a=PartialSimulator(s,p,seed=30002,duration_s=330,trace=True).run()
            assert a.violations==0
            assert a.moves>0
            assert len(a.trace_points)>0

def test_deterministic_common_random_numbers():
    a=PartialSimulator('normal','partial_dynamic',seed=30001,duration_s=500).run()
    b=PartialSimulator('normal','partial_dynamic',seed=30001,duration_s=500).run()
    assert a.metrics()==b.metrics()
    c=PartialSimulator('normal','partial_rl_trained',seed=30001,duration_s=500)
    assert [(x['created'],x['source'],x['target']) for x in a.requests]==[(x['created'],x['source'],x['target']) for x in c.requests]

def test_training_only_eval_seeds_disjoint():
    a=train(episodes=8,seed=1400,duration_s=350)
    assert a.updates>0
    assert len(a.q)>0

def test_proactive_wait_for_cycle_guard():
    """Would close a known 0→1→9→8→0 dependency ring."""
    sim=PartialSimulator('normal','partial_dynamic',seed=9000,duration_s=40)
    for i,(node,target) in enumerate([(0,1),(1,9),(9,8),(16,0)]):
        car=sim.cars[i];car.node=node;car.target=target;car.stage='dropoff'
        sim.node_owner[node]=i
    assert sim.graph.has_edge(16,8)
    assert sim._predicted_deadlock(sim.cars[3],8)
    sim.avoidance=False
    assert not sim._predicted_deadlock(sim.cars[3],8)
