# config.py

# Holds your simulation settings:
# Number of nodes/clients
# Network delays
# Synchrony violation probability
# Number of requests, etc.

from dataclasses import dataclass

@dataclass
class Config:
    num_nodes: int = 5
    
    algorithm: str = "primary_backup"  # or "paxos", "raft", "lowi"


    # Network parameters (v1: very simple)
    base_network_delay: float = 1.0    # ms of simulated time
    network_jitter: float = 0.0        # +/- jitter, optional for later

    # Datacenter-ish parameters (for later)
    host_processing_delay: float = 0.1 # ms
    intra_rack_delay: float = 0.5
    inter_rack_delay: float = 1.0
    sync_delay: float = 0.5            # for sync_send
    p_sync_violate: float = 0.01       # probability sync bound is violated

    # Workload
    num_clients: int = 1
    num_requests_per_client: int = 100
    inter_request_time: float = 1.0    # ms between client requests
