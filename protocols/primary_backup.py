"""
Primary-Backup (Passive Replication) Protocol.
Uses Synchronous Communication (sync_send) for Strong Consistency.
"""

from typing import Any, Dict, List
from Node import Node

class PrimaryBackupNode(Node):
    
    def __init__(self, node_id: int, sim, net, all_nodes=None, **kwargs):
        super().__init__(node_id, sim, net, logger=kwargs.get('logger'))
        self.all_nodes = all_nodes or []
        
        # State
        self.data: List[Any] = []
        self.role = 'BACKUP' # Default role
        self.current_primary = None
        
        # Primary state: Track pending client requests
        # request_id -> {client_id, acks_received: set(), data}
        self.pending_requests: Dict[int, Dict] = {}
        
        # Timers
        self.heartbeat_interval = 50.0
        self.election_timeout = 150.0
        
        # Initial Role Assignment (Highest ID is Primary)
        # In a real system, this is dynamic. Here we use simple Bully logic.
        if self.id == max(self.all_nodes):
            self.become_primary()
        else:
            self.current_primary = max(self.all_nodes)
            self.reset_election_timer()

    def become_primary(self):
        self.role = 'PRIMARY'
        self.current_primary = self.id
        self.pending_requests = {}
        self.send_heartbeat()
        self.set_timer(self.heartbeat_interval, "heartbeat_timer")

    def reset_election_timer(self):
        self.set_timer(self.election_timeout, "election_timer")

    def send_heartbeat(self):
        msg = {"type": "HEARTBEAT", "primary_id": self.id}
        for n in self.all_nodes:
            if n != self.id:
                self.send(n, msg) # Heartbeats are async/UDP-like
        self.set_timer(self.heartbeat_interval, "heartbeat_timer")

    def on_message(self, src: int, msg: Any):
        self.messages_received += 1
        
        # Handle dict messages
        if isinstance(msg, dict):
            mtype = msg.get("type")
        else:
            return

        # 1. HEARTBEAT (Backup Logic)
        if mtype == "HEARTBEAT":
            if msg["primary_id"] >= (self.current_primary or -1):
                self.current_primary = msg["primary_id"]
                self.role = 'BACKUP'
                self.reset_election_timer()

        # 2. REQUEST (Client -> Primary)
        elif mtype == "REQUEST":
            if self.role == 'PRIMARY':
                req_id = msg["request_id"]
                self.pending_requests[req_id] = {
                    "client_id": msg["client_id"],
                    "data": msg["data"],
                    "acks": set()
                }
                
                # Replicate to ALL backups synchronously
                replicate_msg = {
                    "type": "REPLICATE", 
                    "data": msg["data"], 
                    "request_id": req_id
                }
                
                # We need ACKs from all other nodes
                # Using sync_send to simulate strong consistency requirement
                for node in self.all_nodes:
                    if node != self.id:
                        self.sync_send(node, replicate_msg)
                        
                # Note: In this simulation, sync_send is fire-and-forget regarding return value
                # The actual reliability comes from the 'ACK' message processing below.
                
            elif self.current_primary is not None:
                # Forward to Primary
                self.send(self.current_primary, msg)

        # 3. REPLICATE (Primary -> Backup)
        elif mtype == "REPLICATE":
            # Commit locally
            self.data.append(msg["data"])
            
            # Send ACK
            ack_msg = {"type": "ACK", "request_id": msg["request_id"]}
            self.send(src, ack_msg)
            
            self.reset_election_timer()

        # 4. ACK (Backup -> Primary)
        elif mtype == "ACK":
            if self.role == 'PRIMARY':
                req_id = msg["request_id"]
                if req_id in self.pending_requests:
                    self.pending_requests[req_id]["acks"].add(src)
                    
                    # Check if all backups acked (N-1 nodes)
                    # Simplified: Just check if we have majority or all
                    needed = len(self.all_nodes) - 1
                    
                    if len(self.pending_requests[req_id]["acks"]) >= needed:
                        # ALL WRITTEN -> COMMIT
                        self.commit_and_reply(req_id)

    def commit_and_reply(self, req_id):
        if req_id not in self.pending_requests: return
        
        req = self.pending_requests[req_id]
        self.data.append(req["data"])
        self.store['commits'] = self.store.get('commits', 0) + 1
        
        # Reply to client
        reply = {"type": "REPLY", "request_id": req_id, "status": "OK"}
        self.send(req["client_id"], reply)
        
        del self.pending_requests[req_id]

    def on_timer(self, timer_id):
        if timer_id == "heartbeat_timer" and self.role == 'PRIMARY':
            self.send_heartbeat()
        elif timer_id == "election_timer" and self.role == 'BACKUP':
            # Failover logic: If I am the next highest ID, take over
            # Simplified: Just become primary for now (Bully)
            # In a real impl, we would broadcast "I AM LEADER"
            if self.id == sorted(self.all_nodes)[-2]: # Example: Second in command
                 self.become_primary()
            else:
                 # Just wait/reset for simplicity or trigger real election
                 self.reset_election_timer()