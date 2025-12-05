# Node.py
"""
Base node class for distributed algorithms with metrics and synchronization support.
"""

from typing import Any, Optional, Dict, List, TYPE_CHECKING
from Network import Network
from abc import ABC, abstractmethod
import random

if TYPE_CHECKING:
    from simulator import Simulator


class Node(ABC):
    def __init__(self, node_id: int, sim: "Simulator", net: Network, logger=None):
        self.id = node_id
        self.sim = sim
        self.net = net
        self.logger = logger
        
        # State management
        self.store: Dict[str, Any] = {}  # Persistent storage for algorithm
        
        # Metrics
        self.messages_received = 0
        self.messages_sent = 0
        self.is_critical = False
        self.faults: List[str] = []
        
        # Resource simulation
        self.cpu_usage = random.randint(5, 25)
        self.memory_usage = random.randint(30, 50)
        self.disk_usage = random.randint(40, 60)
        self.power_watts = 0

    @abstractmethod
    def on_message(self, src: Any, msg: Any):
        """Called when a message is delivered to this node."""
        print(f"Node {self.id} received message from {src}: {msg}")
        pass

    @abstractmethod
    def on_timer(self, timer_id: Any):
        """Called when a timer fires for this node."""
        pass

    def send(self, dst: int, msg: Any) -> None:
        """Send a message asynchronously to another node."""
        self.net.send(self.id, dst, msg)
        self.messages_sent += 1

    def sync_send(self, dst: int, msg: Any, timeout: Optional[float] = None) -> bool:
        """Send a message synchronously (with delivery guarantee)."""
        self.net.sync_send(self.id, dst, msg, timeout)
        self.messages_sent += 1
        return True

    def set_timer(self, delay: float, timer_id: Any) -> None:
        """Set a timer that will fire after delay time units."""
        fire_time = self.sim.time + delay
        self.sim.schedule(fire_time, "TIMER", self.id, {"timer_id": timer_id})
    
    def update_metrics(self) -> None:
        """Update node resource usage metrics."""
        # Note: self.state is not defined; skipping CPU update based on state
        self.cpu_usage = max(5, min(100, self.cpu_usage + random.randint(-10, 15)))

        self.memory_usage = max(30, min(85, self.memory_usage + random.randint(-5, 5)))
        self.disk_usage = min(98, self.disk_usage + random.uniform(0, 0.05))

