"""
Comprehensive benchmarking module for DBSIM.
Updated to measure TPS (Transactions Per Second) and automate experiments.
"""

import statistics
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
import csv
from pathlib import Path

from simulator import Simulator
from Network import Network
from client import Client
from logger import Logger
from algorithms import ALGORITHM_REGISTRY
from config import Config


@dataclass
class BenchmarkResult:
    """Stores results from a single benchmark run"""
    protocol: str
    num_nodes: int
    network_delay: float
    packet_loss: float
    num_requests: int
    duration: float
    total_messages: int
    throughput_mps: float # Messages per second (Network Load)
    throughput_tps: float # Transactions per second (REAL Performance) [YENİ]
    latency_min: float
    latency_max: float
    latency_avg: float
    latency_median: float
    latency_p95: float
    latency_p99: float
    commits: int = 0
    aborts: int = 0
    commit_rate: float = 0.0
    avg_cpu: float = 0.0
    avg_memory: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BenchmarkRunner:
    """Runs controlled experiments and collects metrics"""
    
    def __init__(self, output_dir: str = "benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: List[BenchmarkResult] = []
        self.logger = Logger()
    
    def run_experiment(self, config: Config, inject_failure: bool = False) -> Optional[BenchmarkResult]:
        """Run a single experiment with the given config"""
        try:
            print(f"\n🔬 Running: {config.algorithm} | "
                  f"Nodes={config.num_nodes} | "
                  f"Loss={config.packet_loss_rate*100:.1f}% | "
                  f"Failure={'YES' if inject_failure else 'NO'}")
            
            # Setup simulator
            sim = Simulator()
            sim.config = config
            net = Network(sim, config)
            
            # Get algorithm
            algo_case = ALGORITHM_REGISTRY.get(config.algorithm)
            if not algo_case:
                print(f"❌ Unknown algorithm: {config.algorithm}")
                return None
            
            # Create nodes
            node_ids = list(range(config.num_nodes))
            nodes = {}
            for nid in node_ids:
                node = algo_case.create_node(nid, sim, net, node_ids)
                # Helper: Set initial roles if needed (mostly for PB, Paxos handles itself)
                if config.algorithm == 'primary_backup':
                    if nid == max(node_ids):
                        node.role = 'PRIMARY'
                    else:
                        node.role = 'BACKUP'
                
                sim.register_node(nid, node)
                nodes[nid] = node
            
            # Create Clients
            clients = []
            for i in range(config.num_clients):
                client_id = 1000 + i # Give clients high IDs
                client = Client(client_id, sim, net, sim.logger)
                # Client needs to know who to contact (Usually max ID initially)
                client.primary_id = max(node_ids) 
                clients.append(client)
                sim.register_node(client_id, client)
                client.on_start() # Schedule first request
            
            # --- FAILURE INJECTION SCENARIO ---
            # We run slightly longer to allow recovery
            max_time = config.inter_request_time * config.num_requests_per_client * 2.5
            
            if inject_failure:
                # 1. Run for half the time (let system stabilize)
                half_time = max_time / 3.0
                sim.run(until_time=half_time)
                
                # 2. Kill the Leader (Node with max ID usually starts as leader)
                victim_id = max(node_ids)
                print(f"⚡ CRASH: Killing Node {victim_id} (Leader) at t={sim.time:.1f}ms")
                
                # Remove from simulator so it stops processing events
                if victim_id in sim.nodes:
                    sim.nodes.pop(victim_id)
                
                # 3. Resume simulation
                sim.run(until_time=max_time)
            else:
                # Normal run
                sim.run(until_time=max_time)
            
            # Collect metrics
            result = self._collect_metrics(config, sim, clients, nodes)
            
            self.results.append(result)
            self._print_result_summary(result)
            return result
            
        except Exception as e:
            import traceback
            print(f"❌ Error in experiment: {e}")
            traceback.print_exc()
            return None
    
    def _collect_metrics(self, config: Config, sim: Simulator, clients: List[Client], nodes: Dict) -> BenchmarkResult:
        
        # 1. Throughput Calculation
        # Count total messages sent by all nodes (including crashed ones if tracked)
        total_messages = sum(getattr(node, 'messages_sent', 0) for node in nodes.values())
        
        # Count COMMITS (Real work done)
        # We sum commits from CLIENTS (replies received) to be sure
        total_replies = sum(client.reply_count for client in clients)
        
        duration = sim.time if sim.time > 0 else 1
        
        throughput_mps = total_messages / duration
        throughput_tps = (total_replies / duration) * 1000 # Transactions per second
        
        # 2. Latency Stats
        latencies = []
        for client in clients:
            if hasattr(client, 'latencies'):
                latencies.extend(client.latencies)
        
        if latencies:
            latency_stats = {
                'min': min(latencies),
                'max': max(latencies),
                'avg': statistics.mean(latencies),
                'median': statistics.median(latencies),
                'p95': self._percentile(latencies, 95),
                'p99': self._percentile(latencies, 99),
            }
        else:
            latency_stats = {'min': 0, 'max': 0, 'avg': 0, 'median': 0, 'p95': 0, 'p99': 0}
        
        # 3. Resource Usage (Avg of alive nodes)
        # Filter out crashed nodes from stats if they were removed from 'nodes' dict? 
        # No, 'nodes' dict still has reference, sim.nodes doesn't.
        cpu_values = [getattr(node, 'cpu_usage', 0) for node in nodes.values()]
        mem_values = [getattr(node, 'memory_usage', 0) for node in nodes.values()]
        
        return BenchmarkResult(
            protocol=config.algorithm,
            num_nodes=config.num_nodes,
            network_delay=config.base_network_delay,
            packet_loss=config.packet_loss_rate,
            num_requests=config.num_requests_per_client,
            duration=duration,
            total_messages=total_messages,
            throughput_mps=throughput_mps,
            throughput_tps=throughput_tps, # Added TPS
            latency_min=latency_stats['min'],
            latency_max=latency_stats['max'],
            latency_avg=latency_stats['avg'],
            latency_median=latency_stats['median'],
            latency_p95=latency_stats['p95'],
            latency_p99=latency_stats['p99'],
            commits=total_replies, # Use client replies as confirmed commits
            commit_rate=total_replies / config.num_requests_per_client if config.num_requests_per_client > 0 else 0,
            avg_cpu=statistics.mean(cpu_values) if cpu_values else 0,
            avg_memory=statistics.mean(mem_values) if mem_values else 0
        )
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        if not data: return 0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]
    
    def _print_result_summary(self, result: BenchmarkResult):
        print(f"  ✓ TPS (Real Speed): {result.throughput_tps:.2f} ops/sec")
        print(f"  ✓ Latency Avg:      {result.latency_avg:.2f} ms")
        print(f"  ✓ Success Rate:     {result.commits} commits")
        print(f"  ✓ Network Load:     {result.total_messages} messages")
    
    def export_csv(self, filename: Optional[str] = None):
        if not filename:
            filename = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = [f.name for f in BenchmarkResult.__dataclass_fields__.values()]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for result in self.results:
                writer.writerow(asdict(result))
        
        print(f"\n📊 CSV exported to: {filepath}")


def main():
    print("="*60)
    print("🚀 DBSIM Automated Benchmark Suite")
    print("="*60)
    
    runner = BenchmarkRunner()
 
    protocols = ['paxos', 'primary_backup']
    
    for proto in protocols:
        print(f"\n--- Testing Protocol: {proto.upper()} ---")
        
    
        cfg = Config(num_nodes=5, algorithm=proto)
        runner.run_experiment(cfg)
        
   
        print(f"--- Crash Test: {proto.upper()} ---")
        cfg_fail = Config(num_nodes=5, algorithm=proto)
        runner.run_experiment(cfg_fail, inject_failure=True)

    runner.export_csv()
    print("\n✅ All benchmarks completed.")

if __name__ == "__main__":
    main()