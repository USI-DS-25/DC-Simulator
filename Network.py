# Network.py
"""
Network simulation with support for packet loss, jitter, reordering, and partitioning.
"""

import random
from typing import Any, Dict, Optional, Set, List


class Network:
    def __init__(self, sim, config):
        """
        Initialize network with simulator and config.
        
        Config should have:
        - base_network_delay: base latency in ms
        - network_jitter: jitter variance
        - packet_loss_rate: probability of loss (0-1)
        - p_sync_violate: probability of sync violation
        - sync_delay: synchronous delivery latency
        """
        self.sim = sim
        self.config = config
        self.message_history: List[Dict] = []
        self.packets_sent = 0
        self.packets_dropped = 0
        self.packets_received = 0
        
        # Network partitions
        self.partitions: List[Set[int]] = []
        self.partition_active = False
        
        # Message reordering queue
        self.reorder_queue: List[tuple] = []

    def _sample_delay(self) -> float:
        """Sample a network delay based on config."""
        base = self.config.base_network_delay
        jitter = self.config.network_jitter
        
        if jitter > 0:
            return base + random.uniform(-jitter, jitter)
        return base

    def send(self, src: int, dst: int, msg: Any) -> None:
        """Send a message asynchronously."""
        self.packets_sent += 1
        
        # Check for partition
        if self._are_partitioned(src, dst):
            self.packets_dropped += 1
            if self.sim.logger:
                self.sim.logger.log(src, f"Message to {dst} blocked by partition")
            return
        
        # Check for packet loss
        if random.random() < self.config.packet_loss_rate:
            self.packets_dropped += 1
            if self.sim.logger:
                self.sim.logger.log(src, f"Message to {dst} dropped (packet loss)")
            return
        
        # Calculate delivery time
        delay = self._sample_delay()
        delivery_time = self.sim.time + delay
        
        # Handle reordering
        if random.random() < self.config.reorder_probability:
            self.reorder_queue.append((delivery_time, dst, msg, src))
        else:
            self.sim.schedule(delivery_time, "MESSAGE", dst, {
                "src": src,
                "msg": msg
            })
        
        self.message_history.append({
            "time": self.sim.time,
            "src": src,
            "dst": dst,
            "msg": msg,
            "delay": delay
        })

    def sync_send(self, src: int, dst: int, msg: Any, timeout: Optional[float] = None) -> None:
        """Send a message with synchronous semantics."""
        self.packets_sent += 1
        
        # Check for partition
        if self._are_partitioned(src, dst):
            self.packets_dropped += 1
            return
        
        # Violate sync bound probabilistically
        if random.random() < self.config.p_sync_violate:
            # Deliver 10x slower or drop
            if random.random() < 0.5:
                self.packets_dropped += 1
                return
            delay = self.config.sync_delay * 10
        else:
            delay = self.config.sync_delay
        
        delivery_time = self.sim.time + delay
        self.sim.schedule(delivery_time, "MESSAGE", dst, {
            "src": src,
            "msg": msg
        })

    def create_partition(self, group1: Set[int], group2: Set[int]) -> None:
        """Create a network partition between two groups."""
        self.partitions = [group1, group2]
        self.partition_active = True
        if self.sim.logger:
            self.sim.logger.log(-1, f"Partition created: {group1} <-> {group2}")

    def heal_partition(self) -> None:
        """Heal all network partitions."""
        self.partitions = []
        self.partition_active = False
        if self.sim.logger:
            self.sim.logger.log(-1, "All partitions healed")

    def _are_partitioned(self, src: int, dst: int) -> bool:
        """Check if two nodes are in different partitions."""
        if not self.partition_active or not self.partitions:
            return False
        
        for partition in self.partitions:
            if (src in partition and dst not in partition) or \
               (dst in partition and src not in partition):
                return True
        
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get network statistics."""
        delivery_rate = 1.0 - (self.packets_dropped / self.packets_sent if self.packets_sent > 0 else 0)
        
        return {
            "packets_sent": self.packets_sent,
            "packets_dropped": self.packets_dropped,
            "packets_received": self.packets_received,
            "delivery_rate": delivery_rate,
            "message_count": len(self.message_history)
        }
    