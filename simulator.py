# simulator.py

# This is the core time controller.
# Keeps:
## Global simulation time (self.time)
## Event queue (self._queue) — ordered by event time
## Event types:
### MESSAGE: deliver a message to a node
### TIMER: fire a timer for a node
## .run():
### Repeatedly pops the next event (earliest time)
### Delivers it to the right node

import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

@dataclass(order=True)
class Event:
    time: float
    seq: int
    kind: str = field(compare=False)       # "MESSAGE" | "TIMER"
    node_id: int = field(compare=False)
    data: Dict[str, Any] = field(compare=False)


class Simulator:
    def __init__(self):
        self.time: float = 0.0
        self._queue: List[Event] = []
        self._next_seq: int = 0
        self.nodes: Dict[int, "Node"] = {}   # filled later from main

    def register_node(self, node_id: int, node: "Node") -> None:
        self.nodes[node_id] = node

    def schedule(self, time: float, kind: str, node_id: int, data: Dict[str, Any]) -> None:
        pass
    def run(self, until_time: Optional[float] = None) -> None:
        pass

    def _dispatch(self, ev: Event) -> None:
        pass
