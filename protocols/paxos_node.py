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
        self.store.setdefault('accepted_prop', None) # (proposal_id, value) of highest accepted proposal, if any

        # Proposal state (if node acts as proposer)
        self.ballot = node_id # starts as node_id to ensure uniqueness
        self.proposals = [] 
        self.acceptors_responded = {} # mapping from proposal id to set of acceptors that responded

        # distinguished roles
        self.is_leader = False
        # if im the node with the lowest id, start as leader
        # this is hacky, TODO: implement real leader election
        if self.id == max(self.all_nodes):
            self.is_leader = True
        if self.is_leader:
            print(f"Node {self.id} starting as leader")

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
        def __init__(self, acceptor_id, accepted_prop):
            self.type = "PROMISE"
            self.accepted_prop = accepted_prop # previously accepted proposal (if any)
            self.id = acceptor_id

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
        # TODO: src doesnt distinguish between nodes and clients
        print(f"Node {self.id} received message from {src}: {msg}")
        self.messages_received += 1
        self.state = "PROCESSING"
        
        msg_type = getattr(msg, 'type', None)

        # TODO: this if-else chain is ugly as heck, refactor later
        if msg_type == "PREPARE":
            # TODO: Handle prepare message
            print(f"Node {self.id} handling PREPARE message from {src}")
            # check if node has already promised a higher ballot
            if self.store['promised_id'] is None or msg.ballot > self.store['promised_id']:
                # promise the ballot
                self.store['promised_id'] = msg.ballot
                # send promise back, including previously accepted proposal (if any)
                if self.store['accepted_prop'] is not None:
                    accepted_prop = self.store['accepted_prop']
                else:
                    accepted_prop = None
                promise_msg = PaxosNode.PromiseMsg(self.id, accepted_prop)
                print("here")
                self.net.send(self.id, src, promise_msg)
            else:
                # ignore the prepare message
                # TODO: can remove this else block, i'll leave it rn for clarity
                pass

        elif msg_type == "PROMISE":
            # TODO: Handle promise message
            print(f"Node {self.id} handling PROMISE message from {src}")
            pass
        elif msg_type == "ACCEPT":
            # TODO: Handle accept message
            print(f"Node {self.id} handling ACCEPT message from {src}")
            pass
        elif msg_type == "ACCEPTED":
            # TODO: Handle accepted message
            print(f"Node {self.id} handling ACCEPTED message from {src}")
            pass
        else:
            # Client request, create proposal
            print(f"Node {self.id} handling CLIENT REQUEST message from {src}")
            # pass

            # TODO: let distinguished leader handle client requests by fowarding them to it
            if not self.is_leader:
                print(f"Node {self.id} is not leader, forwarding request to leader")
                # find leader (node with highest id)
                leader_id = max(self.all_nodes)
                self.net.send(self.id, leader_id, msg)
                return

            proposal = self.create_proposal(msg)
            # Send prepare messages to all acceptors
            prepare_msg = PaxosNode.PrepareMsg(proposal.ballot)
            # TODO: right now it sends to all, optimization: send to a (randomly selected?) quorum only
            for node in self.all_nodes:
                if node != self.id:
                    self.net.send(self.id, node, prepare_msg)

        # # Echo back to sender
        # if src >= 0:
        #     self.net.send(self.id, src, f"ack_{msg}")
        
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
