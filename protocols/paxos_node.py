"""
Full Paxos implementation with Correct Message Counting.
"""
import random
from typing import List, Any
from Node import Node

class PaxosNode(Node):
    
    # Message objects that we send between Paxos nodes
    class PrepareMsg:
        def __init__(self, ballot):
            self.type = "PREPARE"; self.ballot = ballot
    class PromiseMsg:
        def __init__(self, acceptor_id, ballot, accepted_prop=None):
            self.type = "PROMISE"; self.id = acceptor_id; self.ballot = ballot; self.accepted_prop = accepted_prop
    class AcceptMsg:
        def __init__(self, ballot, value):
            self.type = "ACCEPT"; self.ballot = ballot; self.value = value
    class LearnMsg:
        def __init__(self, acceptor_id, ballot, value):
            self.type = "LEARN"; self.id = acceptor_id; self.ballot = ballot; self.value = value
    class HeartbeatMsg:
        def __init__(self, leader_id, ballot):
            self.type = "HEARTBEAT"; self.leader_id = leader_id; self.ballot = ballot
    class NackMsg:
        def __init__(self, ballot):
            self.type = "NACK"; self.ballot = ballot

    def __init__(self, node_id, sim, net, all_nodes=None, **kwargs):
        super().__init__(node_id, sim, net, logger=kwargs.get('logger'))
        self.all_nodes = all_nodes or []
        self.quorum_size = len(self.all_nodes) // 2 + 1
        
        # Local Paxos state that this node keeps in memory
        self.store.setdefault('promised_ballot', 0)  # largest prepare ballot where we already gave a promise
        self.store.setdefault('accepted_prop', None)  # last proposal that this node accepted
        self.store.setdefault('commits', 0)
        
        self.is_leader = False
        self.current_leader = None
        # self.ballot = 0
        self.ballot = self.id  # we start ballots from our node id to avoid simple clashes
        
        self.potential_commands = [] 
        self.promises_received = {}
        self.learn_received = {}
        
        # Timing configuration for election and heartbeat logic
        self.heartbeat_interval = 50.0
        self.election_timeout = 200.0 + random.uniform(0, 100)
        self.reset_election_timer()

        # self.clear_file_commands()


    # Write one committed command as a new line in a text file for this node
    def execute_command(self, command):
        # write the command to a new line of a file (named after the node id)
        filename = f"paxos_node_{self.id}_commands.txt"
        with open(filename, "a") as f:
            f.write(f"{command}\n")

    # Remove old commands from the file of this node so we start with a clean log
    def clear_file_commands(self):
        filename = f"paxos_node_{self.id}_commands.txt"
        with open(filename, "w") as f:
            f.write("")

    def reset_election_timer(self):
        self.set_timer(self.election_timeout, "election_timer")

    def start_election(self):
        self.is_leader = True
        self.current_leader = self.id
        self.ballot += len(self.all_nodes) 
        self.promises_received[self.ballot] = []
        
        # msg = self.PrepareMsg(self.ballot)
        # for n in self.all_nodes:
        #     we should use self.send in this simulator
        #     self.send(n, msg)
        # self.reset_election_timer()

    def broadcast_prepare(self):
        """Send a PREPARE message with the current ballot to all nodes."""
        msg = self.PrepareMsg(self.ballot)
        for n in self.all_nodes:
            # we send prepare to every node through the simulator API
            self.send(n, msg)
        # after one round, we jump the ballot by the cluster size
        self.ballot += len(self.all_nodes)

    def broadcast_accept(self, value):
        """Send an ACCEPT message with the chosen value to all nodes."""
        msg = self.AcceptMsg(self.ballot, value)
        for n in self.all_nodes:
            # we send accept so every node can try to accept this value
            self.send(n, msg)

    def on_message(self, src: int, msg: Any):
        self.messages_received += 1
        
        if isinstance(msg, dict):
            mtype = msg.get("type")
        else:
            mtype = getattr(msg, 'type', None)

        # React to HEARTBEAT messages from the current leader
        if mtype == "HEARTBEAT":
            if msg.ballot >= self.store['promised_ballot']:
                self.store['promised_ballot'] = msg.ballot
                self.current_leader = msg.leader_id
                self.reset_election_timer()
                if self.is_leader and msg.leader_id != self.id:
                    self.is_leader = False

        # Handle PREPARE messages when we are in the acceptor role
        elif mtype == "PREPARE":
            if msg.ballot > self.store['promised_ballot']:
                self.store['promised_ballot'] = msg.ballot
                self.current_leader = src
                self.reset_election_timer()
                reply = self.PromiseMsg(self.id, msg.ballot, self.store['accepted_prop'])
                # send back a PROMISE to the node that started this prepare
                self.send(src, reply)
            else:
                # reply with NACK and tell the proposer about our higher ballot
                self.send(src, self.NackMsg(self.store['promised_ballot']))

        # Handle PROMISE messages when we are the leader
        elif mtype == "PROMISE":
            if not self.is_leader: return
            if msg.ballot not in self.promises_received: self.promises_received[msg.ballot] = []
            self.promises_received[msg.ballot].append(msg)
            
            # we continue only when we see a full quorum of promises
            if len(self.promises_received[msg.ballot]) != self.quorum_size:
                return

            # choose the value to propose; if we have nothing, we send a noop
            if self.potential_commands:
                val = self.potential_commands[0]
            else:
                val = (-1, -1, f"noop_{self.ballot}")
            
            self.broadcast_accept(val)
            self.set_timer(self.heartbeat_interval, "heartbeat_timer")

        # Handle ACCEPT messages as an acceptor node
        elif mtype == "ACCEPT":
            if msg.ballot >= self.store['promised_ballot']:
                self.store['promised_ballot'] = msg.ballot
                self.store['accepted_prop'] = (msg.ballot, msg.value)
                self.current_leader = src
                self.reset_election_timer()
                
                reply = self.LearnMsg(self.id, msg.ballot, msg.value)
                for n in self.all_nodes:
                    # send LEARN so all nodes can see that we accepted this value
                    self.send(n, reply)

        # Handle LEARN messages when nodes count accepted values
        elif mtype == "LEARN":
            prop = (msg.ballot, msg.value)
            if prop not in self.learn_received: self.learn_received[prop] = set()
            self.learn_received[prop].add(msg.id)

            # we wait until enough acceptors report the same value
            if len(self.learn_received[prop]) != self.quorum_size:
                return

            committed_val = msg.value

            # we could log this command to a file if we want external trace
            # self.execute_command(committed_val[2])

            if committed_val in self.potential_commands:
                self.potential_commands.remove(committed_val)
                self.store['commits'] = self.store.get('commits', 0) + 1
                
                client_id, req_id, _ = committed_val
                if client_id >= 0:
                    reply = {
                        "type": "REPLY",
                        "request_id": req_id,
                        "status": "COMMITTED"
                    }
                    self.send(client_id, reply)

        # Handle client REQUEST messages, either as leader or follower
        elif mtype == "REQUEST":
            if self.is_leader:
                cmd_tuple = (msg["client_id"], msg["request_id"], msg["data"])
                if cmd_tuple not in self.potential_commands:
                    self.potential_commands.append(cmd_tuple)
                    # we start a new prepare round for this command
                    self.broadcast_prepare()
                    
            elif self.current_leader is not None:
                # if we are not leader, we just forward the request to the leader
                self.send(self.current_leader, msg)

    def on_timer(self, timer_id):
        if timer_id == "election_timer":
            if not self.is_leader: self.start_election()
            else: self.reset_election_timer()
        elif timer_id == "heartbeat_timer" and self.is_leader:
            msg = self.HeartbeatMsg(self.id, self.ballot)
            for n in self.all_nodes:
                    self.send(n, msg)
            self.set_timer(self.heartbeat_interval, "heartbeat_timer")
