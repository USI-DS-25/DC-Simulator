"""
Paxos protocol implementation for DBSIM
"""

from typing import List, Any
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
        # TODO: check that stored commands will eventually be proposed, rn i dont think they will
        self.potential_commands: List[Any] = [] # client requests to be proposed
        self.promises: dict = {} # ballot_num -> list of promise msgs received

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
        proposal = PaxosNode.Proposal(self.ballot, value)
        # self.proposals.append(proposal)
        self.next_ballot() # increment for next proposal
        return proposal
        

    # Message types
    # TODO: rename to propose?
    class PrepareMsg: # phase 1a
        def __init__(self, ballot_num):
            self.type = "PREPARE"
            self.ballot = ballot_num
            # TODO: add server id for leader change?

    class PromiseMsg: # phase 1b
        def __init__(self, acceptor_id, accepted_prop, ballot):
            self.type = "PROMISE"
            self.accepted_prop = accepted_prop # previously accepted proposal (if any)
            self.ballot = ballot
            self.id = acceptor_id

    class AcceptMsg: # phase 2a
        # TODO: add slot number?
        def __init__(self, proposal):
            self.type = "ACCEPT"
            self.proposal = proposal

    class AcceptedMsg: # phase 2b
        def __init__(self, accepted_id):
            self.type = "ACCEPTED"
            # TODO: should it send the whole proposal back?
            self.accepted_id = accepted_id


    def determine_value_to_propose(self, ballot_num):
        # get the promises for this ballot (all entries for this ballot number)
        promises = self.promises.get(ballot_num, [])

        highest_proposal = None
        for promise in promises:
            # accepted_prop = self.promises[msg.ballot][0].accepted_prop
            accepted_prop = promise.accepted_prop
            if accepted_prop and (highest_proposal is None or accepted_prop[0] > highest_proposal[0]):
                highest_proposal = accepted_prop

        if highest_proposal:
            # if there was a stored promisse, use the one w the highest proposal number
            value = highest_proposal[1]  # Use the value of the highest-numbered proposal
            # ballot_num = highest_proposal[0]
        else:
            # Use any value (e.g., the first potential command from a client)
            value = self.potential_commands.pop(0)
            # ballot_num = self.ballot

        return value
        
    def on_message(self, src, msg):
        # TODO: src doesnt distinguish between nodes and clients
        print(f"Node {self.id} received message from {src}: {msg}")
        self.messages_received += 1
        self.state = "PROCESSING"
        
        msg_type = getattr(msg, 'type', None)

        # TODO: this if-else chain is ugly as heck, refactor later
        if msg_type == "PREPARE":
            print(f"Node {self.id} handling PREPARE message from {src}")
            # check if node has already promised a higher ballot
            if self.store['promised_id'] is None or msg.ballot > self.store['promised_id']:
                # promise the ballot
                self.store['promised_id'] = msg.ballot
                # send promise back, including previously accepted proposal (if any)
                if self.store['accepted_prop'] is not None:
                    accepted_prop = self.store['accepted_prop']
                    ballot_num = accepted_prop[0]
                else:
                    accepted_prop = None
                    ballot_num = msg.ballot

                promise_msg = PaxosNode.PromiseMsg(self.id, accepted_prop, ballot_num)
                self.net.send(self.id, src, promise_msg)
            else:
                # ignore the prepare message
                # TODO: can remove this else block, i'll leave it rn for clarity
                pass

        elif msg_type == "PROMISE":
            # TODO: Handle promise message
            print(f"Node {self.id} handling PROMISE message from {src}")

            # Record the promise
            if msg.ballot not in self.promises:
                self.promises[msg.ballot] = []
            self.promises[msg.ballot].append(msg)

            # # if promise came with previously accepted proposal, store it
            # if msg.accepted_prop:
            #     self.potential_commands.append(msg.accepted_prop)

            # Check if a majority of promises have been received for this ballot
            if len(self.promises[msg.ballot]) >= self.quorum_size:
                # Determine the value v for the proposal
                
                # TODO: implement this
                value = self.determine_value_to_propose(ballot_num=msg.ballot)

                # Send accept requests to the quorum
                # proposal = PaxosNode.Proposal(ballot_num, value)
                proposal = self.create_proposal(value)
                accept_msg = PaxosNode.AcceptMsg(proposal)
                # send accept msgs only to the nodes that promised
                for node in self.promises[msg.ballot]:
                    print(f"Node {self.id} sending ACCEPT message to Node {node.id}")
                    self.net.send(self.id, node.id, accept_msg)

                # TODO: should we clear promises after sending accept msgs? not here
                # ofc, we might have to retransmit

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

            # TODO: this is incorrect. proposals values are selected in phase 2a
            # proposal = self.create_proposal(msg)

            # add client request to potential commands
            self.potential_commands.append(msg)

            # Send prepare messages to all acceptors
            # prepare_msg = PaxosNode.PrepareMsg(proposal.ballot)
            prepare_msg = PaxosNode.PrepareMsg(self.ballot) # use the current ballot number, will inc later
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
