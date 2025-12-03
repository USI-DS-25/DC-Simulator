# simulator.py
"""
Core simulation engine that manages time, events, and node interactions.
"""

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
        self.nodes: Dict[int, "Node"] = {}
        self.message_history: List[Dict] = []
        self.logs: List[tuple] = []
        
        # Metrics and logger
        from logger import Logger
        self.logger = Logger()
        self.config = None

    def register_node(self, node_id: int, node: "Node") -> None:
        self.nodes[node_id] = node

    def schedule(self, time: float, kind: str, node_id: int, data: Dict[str, Any]) -> None:
        """Schedule an event at a specific time."""
        event = Event(time=time, seq=self._next_seq, kind=kind, node_id=node_id, data=data)
        self._next_seq += 1
        heapq.heappush(self._queue, event)

    def run(self, until_time: Optional[float] = None) -> None:
        """Run the simulation until until_time or until queue is empty."""
        while self._queue:
            ev = heapq.heappop(self._queue)
            
            if until_time is not None and ev.time > until_time:
                # Put it back and stop
                heapq.heappush(self._queue, ev)
                break
            
            self.time = ev.time
            self._dispatch(ev)

    def _dispatch(self, ev: Event) -> None:
        """Dispatch an event to the appropriate handler."""
        node = self.nodes.get(ev.node_id)
        if not node:
            return

        if ev.kind == "MESSAGE":
            src = ev.data.get("src")
            msg = ev.data.get("msg")
            node.on_message(src, msg)
            # Record in message history
            self.message_history.append({
                "time": self.time,
                "src": src,
                "dst": ev.node_id,
                "msg": msg
            })

        elif ev.kind == "TIMER":
            timer_id = ev.data.get("timer_id")
            node.on_timer(timer_id)

        else:
            raise ValueError(f"Unknown event kind: {ev.kind}")

    def log(self, node_id: int, message: str) -> None:
        """Log a message with timestamp."""
        self.logs.append((self.time, node_id, message))
        if len(self.logs) > 1000:
            self.logs.pop(0)
