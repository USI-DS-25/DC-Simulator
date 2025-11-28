# client.py
# This is a Node subclass that acts like a real-world user/client.
# Sends requests (e.g. PUT(x, y)) to a designated server
# Waits for replies
# Tracks:
# When a request was sent
# When a reply was received
# Computes latency metrics (avg, p95, etc.)

from typing import Dict, Any, List

from node import Node
from config import Config

class Client(Node):
    def on_start(self) -> None:
        pass
    def _schedule_next_request(self) -> None:
        pass
    def on_timer(self, timer_id: str) -> None:
        pass
    def _send_request(self) -> None:
        pass
    def on_message(self, src: int, msg: Any) -> None:
        pass
    def summary(self) -> Dict[str, float]:
        pass



