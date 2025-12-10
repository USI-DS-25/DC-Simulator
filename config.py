# config.py
from dataclasses import dataclass,field

@dataclass
class Config:
    num_nodes: int = 5
    algorithm: list[str] = field(default_factory=lambda: ["paxos"])    
    
    
    # Network
    base_network_delay: float = 1.0
    network_jitter: float = 0.1          
    packet_loss_rate: float = 0.0
    switch_processing_time: float = 0.05 
    
    # Sync
    sync_delay: float = 0.5
    p_sync_violate: float = 0.01
    
    # Workload
    num_clients: int = 1
    num_requests_per_client: int = 100
    inter_request_time: float = 10.0    
    
    reset_on_error: bool = True