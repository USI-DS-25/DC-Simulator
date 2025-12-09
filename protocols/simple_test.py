"""
Simple test protocol implementation for DBSIM
"""

from Node import Node


class SimpleTestNode(Node):
    """A basic test protocol node that inherits from base Node class"""
    
    def __init__(self, node_id, sim, net, all_nodes=None, **kwargs):
        super().__init__(node_id, sim, net, logger=kwargs.get('logger'))
        self.all_nodes = all_nodes or []
        
    def on_message(self, src, msg):
        """Handle incoming message"""
        self.messages_received += 1
        self.state = "processing"
        
        print(f"Node {self.id} received message from {src}: {msg}")
        
        # Check if this is a replicate message - don't replicate again
        if isinstance(msg, dict) and msg.get("type") == "replicate":
            self.state = "IDLE"
            return
        
        # Send acknowledgment back to sender (always)
        self.net.send(self.id, src, f"ack_{msg}")
        self.messages_sent += 1
        
        # Broadcast to all other nodes ONLY for original requests
        for node_id in self.all_nodes:
            if node_id != self.id:
                self.net.send(self.id, node_id, {"type": "replicate", "data": msg})
                self.messages_sent += 1
        
        self.state = "IDLE"
    
    def on_timer(self, timer_id):
        """Handle timer events"""
        pass
    
    def send_test_message(self, dest, msg):
        """Send a test message"""
        self.net.send(self.id, dest, msg)
        self.messages_sent += 1
    
    def get_state(self):
        """Get current node state"""
        return {
            "id": self.id,
            "state": self.state,
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent
        }
