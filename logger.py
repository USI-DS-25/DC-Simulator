import time
from typing import Optional


class Logger:
    def __init__(self):
        self.logs = []
    
    def log(self, node_id: int, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = time.time()
        log_entry = {
            "timestamp": timestamp,
            "node_id": node_id,
            "level": level,
            "message": message
        }
        self.logs.append(log_entry)
        
        # Print to console
        print(f"[{node_id}] {level}: {message}")
