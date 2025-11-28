# node.py

# Provides:
## send(dst, msg) → schedules a delayed message via the network
## sync_send(dst, msg) → similar, but tries to mimic synchronous delivery
## set_timer(delay, id) → schedules a timer event for the node
## on_message(src, msg) → callback when a message arrives
## on_timer(timer_id) → callback when a timer fires
##  Paxos, Primary-Backup, etc. classes will subclass Node.

from typing import Any
from simulator import Simulator
from network import Network
from abc import ABC, abstractmethod


from abc import ABC, abstractmethod

class Node(ABC):
    def __init__(self, node_id, sim, net, logger=None):
        self.id = node_id            # Unique node ID
        self.sim = sim              # Reference to Simulator
        self.net = net              # Reference to Network
        self.logger = logger        # Optional logger

    @abstractmethod
    def on_message(self, src, msg):
        """
        Called when a message is delivered to this node.
        """
        pass

    @abstractmethod
    def on_timer(self, timer_id):
        """
        Called when a timer fires for this node.
        """
        pass

    def send(self, dst, msg):
        """
        Send a message to another node via the network.
        """
        self.net.send(self.id, dst, msg)

    def sync_send(self, dst, msg):
        """
        Send a synchronous message (may be delayed probabilistically).
        """
        self.net.sync_send(self.id, dst, msg)

    def set_timer(self, delay, timer_id):
        """
        Set a timer that will trigger after the given delay.
        """
        event_time = self.sim.time + delay
        self.sim.schedule(event_time, "TIMER", self.id, timer_id=timer_id)

