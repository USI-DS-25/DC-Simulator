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
    network_jitter: float = 0.0         # +/- jitter
    packet_loss_rate: float = 0.0       # Probability of packet loss (0.0 - 1.0)
    reorder_probability: float = 0.0    # Probability of message reordering
    bandwidth_mbps: float = 1000.0      # Network bandwidth in Mbps
    
    # Synchronization parameters
    sync_model: str = "asynchronous"    # "synchronous", "asynchronous", "partial_synchronous"
    sync_delay: float = 0.5             # ms for synchronous operations
    p_sync_violate: float = 0.01        # Probability sync bound is violated
    max_clock_drift: float = 0.01       # Maximum clock drift in seconds
    sync_timeout: float = 5.0           # Timeout for sync operations
    
    # Host processing
    host_processing_delay: float = 0.1  # ms
    intra_rack_delay: float = 0.5       # ms within rack
    inter_rack_delay: float = 1.0       # ms between racks
    
    # Fault injection
    hw_fault_prob: float = 0.005        # Hardware fault probability
    power_failure_prob: float = 0.5     # Power failure probability
    
    # Resource metrics
    idle_spike_prob: float = 0.1
    log_rotation_prob: float = 0.05
    fault_clear_prob: float = 0.05
    critical_threshold: float = 90.0
    disk_growth_rate: float = 0.05
    
    # Workload
    num_clients: int = 1
    num_requests_per_client: int = 100
    inter_request_time: float = 1.0    # ms between client requests
    
    # Simulation control
    reset_on_error: bool = True
