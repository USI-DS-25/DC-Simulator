# algorithms.py

from typing import Dict
from algorithm_case import AlgorithmCase
from primary_backup import PrimaryBackupNode
from paxos_node import PaxosNode
from raft_node import RaftNode
from lowi_node import LOWINode


ALGORITHM_REGISTRY: Dict[str, AlgorithmCase] = {
    "primary_backup": AlgorithmCase(
        "primary_backup",
        PrimaryBackupNode,
        default_params={"primary_id": 0}
    ),
    "paxos": AlgorithmCase(
        "paxos",
        PaxosNode,
        default_params={}
    ),
    "raft": AlgorithmCase(
        "raft",
        RaftNode,
        default_params={}
    ),
    "lowi": AlgorithmCase(
        "lowi",
        LOWINode,
        default_params={}
    )
}
