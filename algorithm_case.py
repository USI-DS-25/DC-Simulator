# algorithm_case.py

from typing import Type, Dict, Any
from Node import Node

class AlgorithmCase:
    def __init__(self, name: str, node_class: Type[Node], default_params: Dict[str, Any]):
        self.name = name
        self.node_class = node_class
        self.default_params = default_params

    def create_node(self, node_id: int, sim, net, all_nodes: list[int], **overrides) -> Node:
        params = {**self.default_params, **overrides, "all_nodes": all_nodes}
        return self.node_class(node_id, sim, net, **params)