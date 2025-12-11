"""
Network simulation layer.
Handles message delivery, latency simulation, packet loss, jitter,
synchrony violations, and switch queuing delays.
"""

import random
from typing import Any, Dict, Optional, List

class Network:
    def __init__(self, sim, config):
        """
        Initialize the network module.
        
        Args:
            sim: Reference to the main Simulator instance.
            config: Configuration object containing network parameters:
                - base_network_delay: Base latency in ms (e.g., 1.0).
                - network_jitter: Jitter percentage (e.g., 0.1 for 10%).
                - packet_loss_rate: Probability of packet drop (0.0 - 1.0).
                - p_sync_violate: Probability of violating synchrony bounds.
                - sync_delay: The guaranteed upper bound for sync messages.
                - switch_processing_time: Serialization delay per packet.
        """
        self.sim = sim
        self.config = config
        
        # Keeps a list of messages if detailed tracking is needed
        self.message_history: List[Dict] = []
        # Total number of packets that were passed to the network
        self.packets_sent = 0
        # Number of packets that were dropped because of packet loss
        self.packets_dropped = 0
        # Number of sync messages that arrived later than the sync bound
        self.packets_delayed_sync = 0  
        
        # Simple queue model for each destination node.
        # Key: node id, Value: time when its incoming link becomes free.
        self.switch_queues: Dict[int, float] = {}

    def _sample_delay(self) -> float:
        """
        Calculates network latency including Jitter.
        
        Real datacenter networks rarely have constant latency. 
        We add a random deviation based on 'network_jitter' config.
        """
        base = self.config.base_network_delay
        
        # Jitter logic: if config has jitter, apply random variance
        # Default to 0.0 if not set in config
        jitter_rate = getattr(self.config, 'network_jitter', 0.0)
        
        if jitter_rate > 0:
            jitter_range = base * jitter_rate
            # Random float between -jitter and +jitter
            deviation = random.uniform(-jitter_range, jitter_range)
            # Ensure delay doesn't become negative or zero (physics constraint)
            return max(0.1, base + deviation)
        
        return base

    def _apply_queuing_delay(self, dst: int, arrival_time: float) -> float:
        """
        Models switch queuing (serialization delay).
        
        If multiple packets arrive at the same destination simultaneously,
        they must be processed one by one. This adds realistic congestion.
        """
        # Processing time per packet (default to 0.05ms if not in config)
        proc_time = getattr(self.config, 'switch_processing_time', 0.05)
        
        # When will the destination's link be free?
        last_free_time = self.switch_queues.get(dst, 0.0)
        
        # The packet can be processed starting from:
        # max(when it physically arrived, when the previous packet finished)
        start_processing = max(arrival_time, last_free_time)
        
        # Packet leaves the switch after the processing time
        finish_time = start_processing + proc_time
        
        # Update the queue state for this node
        self.switch_queues[dst] = finish_time
        
        return finish_time

    def send(self, src: int, dst: int, msg: Any) -> None:
        """
        Send a message asynchronously (Standard Network).
        
        Simulates:
        1. Packet Loss
        2. Network Latency (Base + Jitter)
        3. Switch Queuing (Congestion)
        """
        self.packets_sent += 1
        
        # 1. Packet Loss Check
        if random.random() < self.config.packet_loss_rate:
            self.packets_dropped += 1
            # Optional logging for debug runs
            if hasattr(self.sim, 'logger') and self.sim.logger:
                self.sim.logger.log(src, f"Message to {dst} dropped (packet loss)", level="WARN")
            return
        
        # 2. Calculate Network Travel Time (Latency + Jitter)
        travel_time = self._sample_delay()
        arrival_at_switch = self.sim.time + travel_time
        
        # 3. Apply Switch/Queuing Delay
        final_delivery_time = self._apply_queuing_delay(dst, arrival_at_switch)
        
        # 4. Add the delivery event to the simulator
        self.sim.schedule(final_delivery_time, "MESSAGE", dst, {
            "src": src,
            "msg": msg
        })
        


    def sync_send(self, src: int, dst: int, msg: Any, timeout: Optional[float] = None) -> bool:
        """
        Send a message with synchronous semantics.
        
        Per requirements:
        - Takes a probability of synchrony being violated.
        - If violated, the message is delayed significantly beyond the bound.
        - Does NOT simulate packet loss (unless specifically desired), 
          as sync models usually assume reliable channels with timing bounds.
        
        Returns:
            bool: True if handed off to network (protocols handle timeout logic).
        """
        self.packets_sent += 1
        
        # Read sync-related parameters from the config
        p_violate = getattr(self.config, 'p_sync_violate', 0.0)
        base_sync_delay = getattr(self.config, 'sync_delay', 0.5)
        
        actual_network_delay = base_sync_delay
        
        # 1. Check if synchrony guarantee should be violated
        # If violated, the network is "slow" and exceeds the guarantee
        if random.random() < p_violate:
            self.packets_delayed_sync += 1
            # Apply a large delay penalty (e.g., 5x - 10x slower)
            actual_network_delay = base_sync_delay * random.uniform(5.0, 10.0)
            
            if hasattr(self.sim, 'logger') and self.sim.logger:
                self.sim.logger.log(src, f"SYNC VIOLATION to {dst}! Delay: {actual_network_delay:.2f}ms", level="WARN")
        else:
            # Normal sync case with small random variation)
            actual_network_delay = base_sync_delay * random.uniform(0.9, 1.0)

        # 2. Apply Queuing Logic
        # Even sync messages must pass through physical switches
        arrival_time = self.sim.time + actual_network_delay
        final_delivery_time = self._apply_queuing_delay(dst, arrival_time)

        # 3. Check Timeout Logic (Simulated)
        # If the user specified a timeout and we exceed it, it's logically a failure.
        # However, physically the message still arrives (late).
        if timeout is not None and (final_delivery_time - self.sim.time) > timeout:
            pass # The protocol code (Node.py) will check the time and handle the timeout.

        # 4. Schedule the message delivery
        self.sim.schedule(final_delivery_time, "MESSAGE", dst, {
            "src": src,
            "msg": msg
        })
        
        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        Returns network statistics for benchmarking.
        """
        total = self.packets_sent if self.packets_sent > 0 else 1
        return {
            "packets_sent": self.packets_sent,
            "packets_dropped": self.packets_dropped,
            "sync_violations": self.packets_delayed_sync,
            "loss_rate": self.packets_dropped / total
        }