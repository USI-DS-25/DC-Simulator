from typing import Dict
from algorithm_case import AlgorithmCase
from protocols.simple_test import SimpleTestNode
from protocols.paxos_node import PaxosNode

from protocols.primary_backup import PrimaryBackupNode

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
    "primary_backup": AlgorithmCase(
        "primary_backup",
        PrimaryBackupNode,
        default_params={}
    ),
}