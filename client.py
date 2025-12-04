"""
Client node that sends requests and measures latency.
"""

from typing import Dict, Any, List
from Node import Node
from config import Config
import random


class Client(Node):
    """A client that sends requests to a server and tracks latencies."""
    
    def __init__(self, node_id: int, sim, net, logger=None):
        super().__init__(node_id, sim, net, logger)
        self.request_count = 0
        self.reply_count = 0
        self.latencies: List[float] = []
        self.pending_requests: Dict[int, float] = {}  # request_id -> send_time
        self.primary_id = 0  # Assume primary is node 0
    
    def on_start(self) -> None:
        """Called when simulation starts - schedule first request."""
        self._schedule_next_request()
    
    def _schedule_next_request(self) -> None:
        """Schedule the next client request."""
        delay = self.sim.config.inter_request_time if hasattr(self.sim, 'config') and self.sim.config else 1.0
        self.set_timer(delay, f"request_{self.request_count}")
    
    def on_timer(self, timer_id: str) -> None:
        """Handle timer events."""
        if timer_id.startswith("request_"):
            self._send_request()
            self._schedule_next_request()
    
    def _send_request(self) -> None:
        """Send a request to the primary."""
        self.request_count += 1
        request_id = self.request_count
        
        # Record send time
        self.pending_requests[request_id] = self.sim.time
        
        # Create request message
        msg = {
            "type": "REQUEST",
            "client_id": self.id,
            "request_id": request_id,
            "data": f"operation_{request_id}"
        }
        
        # Send to primary
        self.send(self.primary_id, msg)
        
        if self.logger:
            self.logger.log(self.id, f"Sent request {request_id}")
    
    def on_message(self, src: int, msg: Any) -> None:
        """Handle incoming messages."""
        if isinstance(msg, dict) and msg.get("type") == "REPLY":
            request_id = msg.get("request_id")
            
            if request_id in self.pending_requests:
                # Calculate latency
                send_time = self.pending_requests[request_id]
                latency = self.sim.time - send_time
                self.latencies.append(latency)
                self.reply_count += 1
                
                del self.pending_requests[request_id]
                
                if self.logger:
                    self.logger.log(self.id, f"Received reply for request {request_id}, latency={latency:.2f}")
    
    def summary(self) -> Dict[str, float]:
        """Return latency summary statistics."""
        if not self.latencies:
            return {}
        
        import statistics
        return {
            "min_latency": min(self.latencies),
            "max_latency": max(self.latencies),
            "avg_latency": statistics.mean(self.latencies),
            "median_latency": statistics.median(self.latencies),
            "request_count": self.request_count,
            "reply_count": self.reply_count
        }



