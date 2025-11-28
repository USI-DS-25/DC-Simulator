# event.py

class Event:
    def __init__(self, time, event_type, target, **kwargs):
        self.time = time              # Scheduled delivery time
        self.event_type = event_type  # "MESSAGE", "TIMER", etc.
        self.target = target          # Node or client ID
        self.kwargs = kwargs          # Message content, timer ID, etc.

    def __lt__(self, other):
        return self.time < other.time

    def __repr__(self):
        desc = f"{self.event_type} @ t={self.time:.4f} to Node {self.target}"
        if self.kwargs:
            desc += f" | {self.kwargs}"
        return desc
