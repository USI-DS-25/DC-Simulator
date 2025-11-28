# main.py
from config import Config
from simulator import Simulator
from network import Network
from client import Client
from algorithms import ALGORITHM_REGISTRY
# from Algorithms.paxos_node import PaxosNode
# from Algorithms.lowi_node import LOWINode
# from Algorithms.ping_node import PingNode

def main():
    cfg = Config()
    sim = Simulator()
    net = Network(sim, cfg)

    algo = ALGORITHM_REGISTRY[cfg.algorithm]

    node_ids = list(range(cfg.num_nodes))
    for nid in node_ids:
        node = algo.create_node(nid, sim, net, all_nodes=node_ids)
        sim.register_node(nid, node)

    # Clients
    ...

# Initializes the simulator and network.

# Creates node instances (e.g. clients and servers).

# Registers all nodes in the simulator.

# Starts the simulation with .run().