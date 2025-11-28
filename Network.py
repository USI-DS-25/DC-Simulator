# Network.py
# This file simulates message delivery between nodes.
# send(src, dst, msg):
# Adds a MESSAGE event to the simulator, scheduled with random or fixed delay.
# sync_send(src, dst, msg):
# Same idea, but obeys strict timing rules (fixed latency unless a sync violation occurs).
from typing import Any

class Nerwork:
    def __init__(self):
        pass

    def _samp_delay_(self) -> float:
        pass

    def send(self, src: int, dst: int, msg: Any) -> None:   
        pass

    def sync_send(self, src: int, dst: int, msg: Any) -> None:
        """
        Synchronous-style send:
        - With prob 1 - p_violate: delivered after exactly sync_delay
        - With prob p_violate: delivered 'late' (here: 10x slower) or you could drop.
        """
        pass
    