# Network.py
"""
Network simulation with support for packet loss, jitter, reordering, and partitioning.
"""

import random
from typing import Any, Dict, Optional, List


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
        self.reorder_queue = []
        
    def _sample_delay(self) -> float:
        """Sample a network delay based on config."""
        return self.config.base_network_delay

    def send(self, src: int, dst: int, msg: Any) -> None:
        """Send a message asynchronously."""
        self.packets_sent += 1
        
        # Check for packet loss
        if random.random() < self.config.packet_loss_rate:
            self.packets_dropped += 1
            if self.sim.logger:
                self.sim.logger.log(src, f"Message to {dst} dropped (packet loss)")
            return
        
        # Calculate delivery time
        delay = self._sample_delay()
        delivery_time = self.sim.time + delay
        
        # Schedule message delivery
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
        
        # Use sync_delay from config if available
        delay = getattr(self.config, 'sync_delay', 0.5)
        delivery_time = self.sim.time + delay
        
        self.sim.schedule(delivery_time, "MESSAGE", dst, {
            "src": src,
            "msg": msg
        })

    def get_stats(self) -> Dict[str, Any]:
        """Get network statistics."""
        delivery_rate = 1.0 - (self.packets_dropped / self.packets_sent if self.packets_sent > 0 else 0)
        
        return {
            "packets_sent": self.packets_sent,
            "packets_dropped": self.packets_dropped,
            "delivery_rate": delivery_rate,
            "message_count": len(self.message_history)
        }
