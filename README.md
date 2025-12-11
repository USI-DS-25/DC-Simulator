
## Architecture

### Core Components

| File | Purpose |
|------|---------|
| `simulator.py` | Event scheduler & simulation engine |
| `Network.py` | Network layer with latency/loss simulation |
| `Node.py` | Base node class with message primitives |
| `client.py` | Workload generator |
| `config.py` | Configuration & defaults |
| `logger.py` | Logging utilities |

### Protocol Implementations


Available implementations:
- ✅ **SimpleTestNode** (`protocols/simple_test.py`) - Basic test protocol
- ✅ **PaxosNode** (`protocols/paxos_node.py`) - Paxos consensus
- ✅ **PrimaryBackupNode** (`protocols/primary_backup.py`) - Primary-Backup replication


New protocol implementations should extend the `Node` base class and implement:
- `on_message(src, msg)` - Handle incoming messages
- `on_timer(timer_id)` - Handle timeout events

### Benchmarking System

| Module | Purpose |
|--------|---------|
| `benchmark.py` | Benchmarking engine with metric collection & CSV export |
| `algorithms.py` | Protocol registry and management |
| `algorithm_case.py` | Algorithm case definitions |

## How It Works

1. **Initialization**: Nodes start with consensus protocol logic
2. **Client requests**: `Client` sends request to primary/leader
3. **Network delivery**: `Network.send()` schedules MESSAGE with configurable latency
4. **Message processing**: Protocol handles message and updates state
5. **Replication**: Primary/leader replicates to other nodes
6. **Acknowledgments**: Backups/followers send ACKs
7. **Reply**: Primary/leader replies to client after sufficient replication
8. **Metrics**: Latency, throughput, and resource usage recorded

## How to Use

### Run Default Benchmark

```bash
python3 benchmark.py
```
Results are saved to `benchmark_results/benchmark_*.csv`

### Customize Configuration

Edit `config.py` to adjust defaults:

```python
@dataclass
class Config:
    num_nodes: int = 5                          # Number of nodes
    algorithm: list[str] = ["paxos"]            # Protocols to test
    
    # Network parameters
    base_network_delay: float = 1.0             # milliseconds
    network_jitter: float = 0.1                 # percentage (0.1 = 10%)
    packet_loss_rate: float = 0.0               # 0-1 scale
    switch_processing_time: float = 0.05        # milliseconds
    
    # Sync parameters
    sync_delay: float = 0.5                     # guaranteed upper bound
    p_sync_violate: float = 0.01                # probability of violation
    
    # Workload parameters
    num_clients: int = 1
    num_requests_per_client: int = 100
    inter_request_time: float = 10.0            # milliseconds
```

### Run Custom Simulation

```bash
python3 benchmark.py
```
(After changing the requirements in config file)

### Implement a New Protocol

1. Create your protocol class in `protocols/my_protocol.py`:

```python
from Node import Node

class MyProtocolNode(Node):
    def __init__(self, node_id, sim, net, all_nodes=None, **kwargs):
        super().__init__(node_id, sim, net, logger=kwargs.get('logger'))
        self.all_nodes = all_nodes or []
    
    def on_message(self, src, msg):
        """Handle incoming messages"""
        self.messages_received += 1
        # Your protocol logic here
    
    def on_timer(self, timer_id):
        """Handle timeout events"""
        # Your timeout logic here
```

2. Register in `algorithms.py`:

```python
from protocols.my_protocol import MyProtocolNode

ALGORITHM_REGISTRY['my_protocol'] = AlgorithmCase(
    'my_protocol',
    MyProtocolNode,
    default_params={}
)
```

3. Update `config.py`:

```python
algorithm: list[str] = ["my_protocol"]
```

4. Run benchmark:

```bash
python3 benchmark.py
```

## Environment

- **Python**: 3.13

