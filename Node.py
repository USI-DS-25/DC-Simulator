# Node.py
"""
Base node class with realistic metrics.
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
        self.store: Dict[str, Any] = {}
        
        # Metrics
        self.messages_received = 0
        self.messages_sent = 0
        self.last_checked_msgs = 0
        
        # Initial resources
        self.cpu_usage = 5.0
        self.memory_usage = 30.0
        self.disk_usage = 40.0
        self.power_watts = 0.0
        self.faults = []
        self.is_critical = False

    @abstractmethod
    def on_message(self, src: Any, msg: Any):
        pass

    @abstractmethod
    def on_timer(self, timer_id: Any):
        pass

    def send(self, dst: int, msg: Any) -> None:
        self.net.send(self.id, dst, msg)
        self.messages_sent += 1

    def sync_send(self, dst: int, msg: Any, timeout: Optional[float] = None) -> bool:
        try:
            return self.net.sync_send(self.id, dst, msg, timeout)
        except:
            return False

    def set_timer(self, delay: float, timer_id: Any) -> None:
        fire_time = self.sim.time + delay
        self.sim.schedule(fire_time, "TIMER", self.id, {"timer_id": timer_id})
    
    def update_metrics(self) -> None:
        """Update metrics based on real load."""
        delta = self.messages_received - self.last_checked_msgs
        self.last_checked_msgs = self.messages_received
        
        # CPU increases with message load
        load = 5.0 + (delta * 0.5)
        self.cpu_usage = max(5.0, min(100.0, load + random.uniform(-1, 1)))
        
        # Memory increases with store size
        mem = 30.0 + (len(self.store) * 0.1)
        self.memory_usage = max(30.0, min(90.0, mem))