"""
Primary-backup replication protocol node with simple message objects.
"""

from typing import Any, Dict, List
from Node import Node

class PrimaryBackupNode(Node):
    
    # Message classes that we send between primary and backups
    class HeartbeatMsg:
        def __init__(self, primary_id):
            self.type = "HEARTBEAT"
            self.primary_id = primary_id

    class RequestMsg:
        def __init__(self, client_id, request_id, data):
            self.type = "REQUEST"
            self.client_id = client_id
            self.request_id = request_id
            self.data = data

    class ReplicateMsg:
        def __init__(self, request_id, data):
            self.type = "REPLICATE"
            self.request_id = request_id
            self.data = data

    class AckMsg:
        def __init__(self, request_id):
            self.type = "ACK"
            self.request_id = request_id

    def __init__(self, node_id: int, sim, net, all_nodes=None, **kwargs):
        super().__init__(node_id, sim, net, logger=kwargs.get('logger'))
        self.all_nodes = all_nodes or []

        # Local state for the replicated data and protocol role
        self.data: List[Any] = []
        self.role = 'BACKUP'
        self.current_primary = None
        self.pending_requests: Dict[int, Dict] = {}  # maps request_id to a small dict with client_id, acks, and data

        # Timer values for heartbeats and primary election
        self.heartbeat_interval = 50.0
        self.election_timeout = 150.0

        # At startup we choose the node with the biggest id as the first primary
        if self.id == max(self.all_nodes):
            self.become_primary()
        else:
            self.current_primary = max(self.all_nodes)
            self.reset_election_timer()

    # Switch this node to PRIMARY role and start sending heartbeats
    def become_primary(self):
        self.role = 'PRIMARY'
        self.current_primary = self.id
        self.pending_requests = {}
        self.send_heartbeat()
        self.set_timer(self.heartbeat_interval, "heartbeat_timer")

    def reset_election_timer(self):
        self.set_timer(self.election_timeout, "election_timer")

    # Send a heartbeat to every other node so they know who is primary
    def send_heartbeat(self):
        msg = self.HeartbeatMsg(self.id)
        for n in self.all_nodes:
            if n != self.id:
                self.send(n, msg)
        self.set_timer(self.heartbeat_interval, "heartbeat_timer")

    # Primary sends the update to all backups using synchronous send
    def replicate_to_backups(self, req_id, data):
        msg = self.ReplicateMsg(req_id, data)
        for n in self.all_nodes:
            if n != self.id:
                self.sync_send(n, msg)

    # When we have enough ACKs, we commit the request and reply to the client
    def commit_and_reply(self, req_id):
        if req_id not in self.pending_requests: return

        req = self.pending_requests[req_id]
        self.data.append(req["data"])
        self.store['commits'] = self.store.get('commits', 0) + 1

        reply = {"type": "REPLY", "request_id": req_id, "status": "OK"}
        self.send(req["client_id"], reply)

        del self.pending_requests[req_id]

    # Main handler for all incoming messages
    def on_message(self, src: int, msg: Any):
        self.messages_received += 1

        if isinstance(msg, dict):
            mtype = msg.get("type")
            class MsgWrapper:
             def __init__(self, d):
                self.type = d.get("type")
                self.__dict__.update(d)
            msg = MsgWrapper(msg)
        else:
          mtype = getattr(msg, "type", None)
          if mtype is None:
            return 

        # 1) handle HEARTBEAT: we update who we think is primary
        if mtype == "HEARTBEAT":
            if msg.primary_id >= (self.current_primary or -1):
                self.current_primary = msg.primary_id
                self.role = 'BACKUP'
                self.reset_election_timer()

        # 2) handle REQUEST: primary processes it, backups forward to primary
        elif mtype == "REQUEST":
            if self.role == 'PRIMARY':
                req_id = msg.request_id
                self.pending_requests[req_id] = {
                    "client_id": msg.client_id,
                    "data": msg.data,
                    "acks": set()
                }
                self.replicate_to_backups(req_id, msg.data)
            elif self.current_primary is not None:
                self.send(self.current_primary, msg)

        # 3) handle REPLICATE on backups: apply data and send ACK back
        elif mtype == "REPLICATE":
            self.data.append(msg.data)
            ack_msg = self.AckMsg(msg.request_id)
            self.send(src, ack_msg)
            self.reset_election_timer()

        # 4) handle ACK on the primary: when all backups answer, we commit
        elif mtype == "ACK":
            if self.role == 'PRIMARY':
                req_id = msg.request_id
                if req_id in self.pending_requests:
                    self.pending_requests[req_id]["acks"].add(src)
                    needed = len(self.all_nodes) - 1
                    if len(self.pending_requests[req_id]["acks"]) >= needed:
                        self.commit_and_reply(req_id)

    # Timers for periodic heartbeat and simple failover
    def on_timer(self, timer_id):
        if timer_id == "heartbeat_timer" and self.role == 'PRIMARY':
            self.send_heartbeat()
        elif timer_id == "election_timer" and self.role == 'BACKUP':
            # If we are the second largest id and we do not see a primary, we take over
            if self.id == sorted(self.all_nodes)[-2]:
                self.become_primary()
            else:
                self.reset_election_timer()
