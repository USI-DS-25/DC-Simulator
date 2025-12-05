"""
Paxos protocol implementation for DBSIM
"""

import random
from typing import List, Any
from Node import Node
import time

# Outstanding TODOs:
# - Phase 2a: If P does not receive any accepted operation from any of the acceptors, it will forward its own proposal for acceptance by sending accept(t, o) to all acceptors.
# - Msg loss/timeout are not being handled
# - Multi leader paxos doesnt work (yet) (leader 2 will receive an accept from 1 and accept it, since its highest promised_ballot is 1)



class PaxosNode(Node):
    
    # TODO: modify arguments as needed
    def __init__(self, node_id, sim, net, all_nodes=None, **kwargs):
        super().__init__(node_id, sim, net, logger=kwargs.get('logger'))
        self.all_nodes = all_nodes or []

        # TODO: Configuration (eg quorum size)
        self.quorum_size = len(self.all_nodes) // 2 + 1
        # TODO: add resend time for messages/timeouts

        # Persistent state (if node acts as acceptor)
        self.store.setdefault('promised_ballot', None) # highest ballot _promised_
        self.store.setdefault('accepted_prop', None) # (proposal_id, value) of highest _accepted_ proposal, if any

        # Proposal state (if node acts as proposer)
        self.ballot = node_id # starts as node_id to ensure uniqueness
        # TODO: check that stored commands will eventually be proposed, rn i dont think they will
        self.potential_commands: List[Any] = [] # client requests to be proposed
        self.promises: dict = {} # ballot_num -> list of promise msgs received
        self.learn_requests_received: dict = {} # proposal_id -> list of learn msgs received

        # distinguished roles
        self.is_leader = False
        # if im the node with the lowest id, start as leader
        # this is hacky, TODO: implement real leader election
        if self.id == max(self.all_nodes):
            self.is_leader = True
        # if self.is_leader:
        #     print(f"Node {self.id} starting as leader")

        # Uncomment to test execution
        # self.clear_file_commands()

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
        # def __init__(self, acceptor_id, accepted_prop, ballot):
        def __init__(self, acceptor_id, ballot, accepted_prop=None):
            self.type = "PROMISE"
            # previously accepted proposal (if any)
            self.accepted_prop = accepted_prop 
            self.ballot = ballot # promised ballot number
            self.id = acceptor_id

    class AcceptMsg: # phase 2a
        # TODO: add slot number?
        def __init__(self, proposal):
            self.type = "ACCEPT"
            self.proposal = proposal

    class LearnMsg:
        def __init__(self, proposal):
            self.type = "LEARN"
            self.proposal = proposal


    def determine_value_to_propose(self, ballot_num):
        # get the promises for this ballot (all entries for this ballot number)
        promises = self.promises.get(ballot_num, [])

        highest_proposal = None
        for promise in promises:
            accepted_prop = promise.accepted_prop
            if accepted_prop and (highest_proposal is None or accepted_prop[0] > highest_proposal[0]):
                highest_proposal = accepted_prop

        if highest_proposal:
            # if there was a stored promisse, use the one w the highest proposal number
            value = highest_proposal[1] # value
        else:
            # Use any value (e.g., the first potential command from a client)
            value = self.potential_commands.pop(0)

        return value
    
    def should_accept_proposal(self, proposal):
        # TODO: implement the logic here
        return False  # Placeholder for acceptance condition
    
    def should_learn_proposal(self, proposal):
        # TODO: implement the logic here
        return False  # Placeholder for learning condition
        
    def on_message(self, src, msg):
        # TODO: src doesnt distinguish between nodes and clients
        # print(f"Node {self.id} received message from {src}: {msg}")
        self.messages_received += 1
        self.state = "PROCESSING"
        
        msg_type = getattr(msg, 'type', None)

        # TODO: this if-else chain is ugly as heck, refactor later
        if msg_type == "PREPARE":
            # print(f"Node {self.id} handling PREPARE message from {src}")
            # check if node has already promised a higher ballot
            if self.store['promised_ballot'] is None or msg.ballot > self.store['promised_ballot']:
                # promise the ballot
                self.store['promised_ballot'] = msg.ballot
                # send promise back, including previously accepted proposal (if any)
                if self.store['accepted_prop'] is not None:
                    accepted_prop = self.store['accepted_prop']
                else:
                    accepted_prop = None

                if accepted_prop:
                    promise_msg = PaxosNode.PromiseMsg(self.id, msg.ballot, accepted_prop)
                else:
                    promise_msg = PaxosNode.PromiseMsg(self.id, msg.ballot)
                # promise_msg = PaxosNode.PromiseMsg(self.id, msg.ballot, accepted_prop)
                self.net.send(self.id, src, promise_msg)
                # print(f"<PROM, {msg.ballot}, n_{self.id} -> S_{src}>")
            else:
                # ignore the prepare message
                # TODO: can remove this else block, i'll leave it rn for clarity
                pass

        elif msg_type == "PROMISE":
            # print(f"Node {self.id} handling PROMISE message from {src}")

            # Record the promise
            if msg.ballot not in self.promises:
                self.promises[msg.ballot] = []
            promisors = self.promises[msg.ballot]


            # check that we haven't already received the necessary number of promises
            # to trigger the accept phase for this ballot
            # if we do, ignore this promise, otherwise it leads to unintended extra accept msgs
            if len(self.promises[msg.ballot]) >= self.quorum_size:
                # print(f"Node {self.id} already has quorum of promises for ballot {msg.ballot}, ignoring additional promise from {src}")
                self.state = "IDLE"
                return
            
            promisors.append(msg)

            # Check if a majority of promises have been received for this ballot
            if len(self.promises[msg.ballot]) >= self.quorum_size:
                # Determine the value v for the proposal
                
                value = self.determine_value_to_propose(ballot_num=msg.ballot)

                # Send accept requests to the quorum
                proposal = self.create_proposal(value)
                accept_msg = PaxosNode.AcceptMsg(proposal)
                # send accept msgs only to the nodes that promised
                
                for promise in promisors:
                    # print(f"Node {self.id} sending ACCEPT message to Node {node.id}")
                    self.net.send(self.id, promise.id, accept_msg)
                    # print(f"<ACC, S_{self.id} -> n_{promise.id}, {proposal.ballot}, {proposal.value}>")

                # TODO: should we do the same +1 logic here as in learn msgs? since the node itself is also an acceptor
                # it seems to be working without it for now tho, idk

                # TODO: should we clear promises after sending accept msgs? not here
                # ofc, we might have to retransmit

        elif msg_type == "ACCEPT":
            # TODO: Handle accept message
            # print(f"Node {self.id} handling ACCEPT message from {src}")

            # check if node has already responded to a prepare request with a greater ballot
            if self.store['promised_ballot'] is None or msg.proposal.ballot >= self.store['promised_ballot']:
                # accept the proposal
                self.store['promised_ballot'] = msg.proposal.ballot
                self.store['accepted_prop'] = (msg.proposal.ballot, msg.proposal.value)

                # send learn msg to all learners so they execute the command
                learn_msg = PaxosNode.LearnMsg(msg.proposal)
                for node in self.all_nodes:
                    if node != self.id:
                        self.net.send(self.id, node, learn_msg)
                        # print(f"<LRN, n_{self.id} -> S_{node}, {msg.proposal.ballot}, {msg.proposal.value}>")

                # since theoretically all processes play the roles of proposer, acceptor, and learner,
                # the node should also learn the proposal itself by sending it. we can simulate this by
                # incrementing the learn_requests_received count by one immediately
                proposal_id = msg.proposal.ballot
                if proposal_id not in self.learn_requests_received:
                    self.learn_requests_received[proposal_id] = []
                self.learn_requests_received[proposal_id].append(msg)
                
            else:
                # ignore the accept message
                # can skip this block, leaving it for clarity
                pass

        elif msg_type == "LEARN":
            # print(f"Node {self.id} handling LEARN message from {src}")

            proposal_id = msg.proposal.ballot
            if proposal_id not in self.learn_requests_received:
                self.learn_requests_received[proposal_id] = []
            self.learn_requests_received[proposal_id].append(msg)

            # Check if a majority of learn requests have been received for this proposal
            if len(self.learn_requests_received[proposal_id]) >= self.quorum_size:
                # Execute the learned command
                # TODO: implement a proper command execution mechanism
                # print(f"Node {self.id} learned and executing command: {msg.proposal.value}")

                # Uncomment to test execution
                # self.execute_command(msg.proposal.value)
                
                # Forget about the learned proposal
                self.learn_requests_received.pop(proposal_id, None)
                # clear the accepted proposal if it matches
                if (self.store['accepted_prop'] is not None and 
                    self.store['accepted_prop'][0] == proposal_id):
                    self.store['accepted_prop'] = None

                # check if there are pending commands to be executed. if so, propose them
                # note: this is not exactly how paxos is supposed to work, but for simplicity we do it this way
                # TODO: implement proper command queueing and execution

                # note: no need to check if node is leader, since only leaders store potential commands
                if len(self.potential_commands) > 0:

                    # Send prepare messages to all acceptors
                    prepare_msg = PaxosNode.PrepareMsg(self.ballot) # use the current ballot number, will inc later
                    # TODO: right now it sends to all, optimization: send to a (randomly selected?) quorum only
                    for node in self.all_nodes:
                        if node != self.id:
                            # print(f"<PREP, S_{self.id} -> n_{node}, b: {self.ballot}>")
                            self.net.send(self.id, node, prepare_msg)
                
        else:
            # Client request, prepare to propose it 
            # print(f"Node {self.id} handling CLIENT REQUEST message from {src}")

            # TODO: let distinguished leader handle client requests by fowarding them to it
            if not self.is_leader:
                # print(f"Node {self.id} is not leader, forwarding request to leader")
                # find leader (node with highest id)
                leader_id = max(self.all_nodes) # TODO: leader identification defined in two places, stinky antipattern!
                self.net.send(self.id, leader_id, msg)
                self.state = "IDLE"
                return

            # only leader reaches here
            # add client request to potential commands
            self.potential_commands.append(msg)

            # Send prepare messages to all acceptors
            prepare_msg = PaxosNode.PrepareMsg(self.ballot) # use the current ballot number, will inc later
            # TODO: right now it sends to all, optimization: send to a (randomly selected?) quorum only
            for node in self.all_nodes:
                if node != self.id:
                    # print(f"<PREP, S_{self.id} -> n_{node}>, b: {self.ballot}")
                    self.net.send(self.id, node, prepare_msg)
        
        self.state = "IDLE"

    # test execution. see if entries match across node logs
    def execute_command(self, command):
        # write the command to a new line of a file (named after the node id)
        filename = f"paxos_node_{self.id}_commands.txt"
        with open(filename, "a") as f:
            f.write(f"{command}\n")

    def clear_file_commands(self):
        filename = f"paxos_node_{self.id}_commands.txt"
        with open(filename, "w") as f:
            f.write("")

    # TODO
    def on_timer(self, timer_id):
        pass