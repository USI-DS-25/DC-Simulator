# Node.py
"""
Base node class for distributed algorithms with metrics and synchronization support.
"""

from typing import Any, Optional, Dict, List
from simulator import Simulator
from Network import Network
from abc import ABC, abstractmethod
import random


class Node(ABC):
    def __init__(self, node_id: int, sim: Simulator, net: Network, logger=None):
        self.id = node_id
        self.sim = sim
        self.net = net
        self.logger = logger
        
        # State management
        self.inbox: List[Any] = []
        self.store: Dict[str, Any] = {}  # Persistent storage for algorithm
        self.state = "IDLE"  # "IDLE", "PROCESSING", "SHUTDOWN"
        
        # Metrics
        self.messages_received = 0
        self.messages_sent = 0
        self.is_shutdown = False
        self.is_critical = False
        self.faults: List[str] = []
        
        # Resource simulation
        self.cpu_usage = random.randint(5, 25)
        self.memory_usage = random.randint(30, 50)
        self.disk_usage = random.randint(40, 60)
        self.power_watts = 0
        
        # Clock and timers
        self.local_clock = 0.0
        self.timers: Dict[str, tuple] = {}  # timer_id -> (callback, args, kwargs)
        self.pending_sync_sends: Dict[str, tuple] = {}  # msg_id -> (timestamp, callback)

    @abstractmethod
    def on_message(self, src: int, msg: Any):
        """Called when a message is delivered to this node."""
        pass

    @abstractmethod
    def on_timer(self, timer_id: str):
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

    def set_timer(self, delay: float, timer_id: str) -> None:
        """Schedule a timer that will fire after delay."""
        event_time = self.sim.time + delay
        self.sim.schedule(event_time, "TIMER", self.id, {"timer_id": timer_id})

    def cancel_timer(self, timer_id: str) -> None:
        """Cancel a scheduled timer."""
        if timer_id in self.timers:
            del self.timers[timer_id]

    def receive_message(self, message: Any) -> None:
        """Receive a message in the inbox."""
        self.inbox.append(message)
        self.messages_received += 1
        self.state = "PROCESSING"
        if self.sim:
            self.sim.schedule(self.sim.time + 0.1, "TIMER", self.id, {"timer_id": "_finish_processing"})

    def update_metrics(self) -> None:
        """Update node resource usage metrics."""
        if self.is_shutdown:
            self.cpu_usage = 0
            self.memory_usage = 0
            self.disk_usage = 0
            self.power_watts = 0
            return

        if self.state == "PROCESSING":
            self.cpu_usage = min(100, self.cpu_usage + random.randint(5, 15))
        else:
            self.cpu_usage = max(5, self.cpu_usage - random.randint(0, 10))

        self.memory_usage = max(30, min(85, self.memory_usage + random.randint(-5, 5)))
        self.disk_usage = min(98, self.disk_usage + random.uniform(0, 0.05))

        # Detect faults
        if self.cpu_usage > 90:
            if "High CPU Load" not in self.faults:
                self.faults.append("High CPU Load")
        elif "High CPU Load" in self.faults:
            self.faults.remove("High CPU Load")

        if self.memory_usage > 90:
            if "Memory Exhaustion" not in self.faults:
                self.faults.append("Memory Exhaustion")
        elif "Memory Exhaustion" in self.faults:
            self.faults.remove("Memory Exhaustion")

        if self.disk_usage > 90:
            if "Disk Space Low" not in self.faults:
                self.faults.append("Disk Space Low")
        elif "Disk Space Low" in self.faults:
            self.faults.remove("Disk Space Low")

        # Random hardware faults
        if random.random() < 0.005 and len(self.faults) < 3:
            fault_types = ["Network Interface Down", "Memory Error", "Disk I/O Error"]
            for ft in fault_types:
                if random.random() < 0.1 and ft not in self.faults:
                    self.faults.append(ft)

        self.is_critical = len(self.faults) > 0
        
        # Power calculation
        base_power = 120 + 30  # Base power estimate
        self.power_watts = base_power * (0.3 + 0.7 * (self.cpu_usage / 100))

