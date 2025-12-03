"""
Paxos protocol implementation for DBSIM
"""

from Node import Node

class PaxosNode(Node):
    
    # TODO: modify arguments as needed
    def __init__(self, node_id, sim, net, all_nodes=None, **kwargs):
        super().__init__(node_id, sim, net, logger=kwargs.get('logger'))
        self.all_nodes = all_nodes or []

        # TODO: Configuration (eg quorum size)
        self.quorum_size = len(self.all_nodes) // 2 + 1

        # Persistent state (if node acts as acceptor)
        self.store.setdefault('promised_id', None) # highest proposal id promised
        self.store.setdefault('accepted_prop', None) # (proposal_id, value) of highest accepted proposal

        # Proposal state (if node acts as proposer)
        self.ballot = node_id # starts as node_id to ensure uniqueness
        self.proposals = [] 

        # distinguished roles
        self.is_leader = False

    # proposal structure
    class Proposal:
        def __init__(self, ballot_num, value):
            self.ballot = ballot_num
            self.value = value
            self.acceptors = set()

    def next_ballot(self):
        """Generate the next ballot number."""
        self.ballot += len(self.all_nodes) # eg: 1, 4, 7 for node_0 in a 3-node system
        return self.ballot
    
    def create_proposal(self, value):
        """Create a new proposal with a unique ballot number."""
        proposal = PaxosNode.Proposal(self.next_ballot(), value)
        self.proposals.append(proposal)
        return proposal
        

    # Message types
    # TODO: rename to propose?
    class PrepareMsg:
        def __init__(self, ballot_num):
            self.type = "PREPARE"
            self.ballot = ballot_num
            # TODO: add server id for leader change?

    class PromiseMsg:
        def __init__(self, accepted_prop):
            self.type = "PROMISE"
            self.accepted_prop = accepted_prop # previously accepted proposal (if any)
            self.id = self.node_id

    class AcceptMsg:
        # TODO: add slot number?
        def __init__(self, proposal):
            self.type = "ACCEPT"
            self.proposal = proposal

    class AcceptedMsg:
        def __init__(self, accepted_id):
            self.type = "ACCEPTED"
            # TODO: should it send the whole proposal back?
            self.accepted_id = accepted_id
        
    def on_message(self, src, msg):
        self.messages_received += 1
        self.state = "PROCESSING"
        
        msg_type = getattr(msg, 'type', None)
        if msg_type == "PREPARE":
            # TODO: Handle prepare message
            pass
        elif msg_type == "PROMISE":
            # TODO: Handle promise message
            pass
        elif msg_type == "ACCEPT":
            # TODO: Handle accept message
            pass
        elif msg_type == "ACCEPTED":
            # TODO: Handle accepted message
            pass
        else:
            # Unknown message type
            pass
        
        self.state = "IDLE"

    # TODO
    def on_timer(self, timer_id):
        pass
    
    # def send_test_message(self, dest, msg):
    #     """Send a test message"""
    #     self.net.send(self.id, dest, msg)
    #     self.messages_sent += 1
    
    # def get_state(self):
    #     """Get current node state"""
    #     return {
    #         "id": self.id,
    #         "state": self.state,
    #         "messages_received": self.messages_received,
    #         "messages_sent": self.messages_sent
    #     }
