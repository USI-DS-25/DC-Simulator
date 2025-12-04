# config.py
"""
Simulation configuration with network, synchronization, and fault parameters.
"""

from dataclasses import dataclass

@dataclass
class Config:
    # Basic setup
    num_nodes: int = 5
    algorithm: str = "simple_test"  # "simple_test" or add new ones to ALGORITHM_REGISTRY
    
    # Network parameters
    base_network_delay: float = 1.0     # ms of simulated time
    packet_loss_rate: float = 0.0       # Probability of packet loss (0.0 - 1.0)
    
    # Synchronization parameters
    sync_delay: float = 0.5             # ms for synchronous operations
    p_sync_violate: float = 0.01        # Probability sync bound is violated
    
    # Workload
    num_clients: int = 1
    num_requests_per_client: int = 100
    inter_request_time: float = 1.0    # ms between client requests
    
    # Simulation control
    reset_on_error: bool = True
