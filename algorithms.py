# algorithms.py

from typing import Dict
from algorithm_case import AlgorithmCase
from protocols.simple_test import SimpleTestNode
from protocols.paxos_node import PaxosNode


ALGORITHM_REGISTRY: Dict[str, AlgorithmCase] = {
    "simple_test": AlgorithmCase(
        "simple_test",
        SimpleTestNode,
        default_params={}
    ),
    "paxos": AlgorithmCase(
        "paxos",
        PaxosNode,
        default_params={}
    ),
}
