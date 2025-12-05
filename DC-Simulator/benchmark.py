"""
Comprehensive benchmarking module for DBSIM.
Runs controlled experiments with the algorithm specified in config.py
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
    throughput_mps: float
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
    
    def run_experiment(self, config: Config) -> Optional[BenchmarkResult]:
        """Run a single experiment with the given config"""
        try:
            print(f"\n🔬 Running: {config.algorithm} | "
                  f"N={config.num_nodes} | "
                  f"delay={config.base_network_delay}ms | "
                  f"loss={config.packet_loss_rate*100:.1f}%")
            
            # Setup simulator
            sim = Simulator()
            sim.config = config
            net = Network(sim, config)
            
            # Get algorithm from ALGORITHM_REGISTRY
            algo_case = ALGORITHM_REGISTRY.get(config.algorithm)
            if not algo_case:
                print(f"❌ Unknown algorithm: {config.algorithm}")
                return None
            
            # Create nodes using algorithm from config
            node_ids = list(range(config.num_nodes))
            nodes = {}
            
            for nid in node_ids:
                node = algo_case.create_node(nid, sim, net, node_ids)
                if nid == 0:
                    node.store['role'] = 'PRIMARY'
                else:
                    node.store['role'] = 'BACKUP'
                nodes[nid] = node
                sim.nodes[nid] = node

            
            
            # Create and start clients
            clients = []
            for i in range(config.num_clients):
                client = Client(config.num_nodes + i, sim, net, logger=self.logger)
                sim.register_node(client.id, client)
                clients.append(client)
                client.on_start()  

        # Run simulation
            sim.run(until_time=config.inter_request_time * config.num_requests_per_client * 2)
            
            # Collect metrics
            result = self._collect_metrics(
                config=config,
                sim=sim,
                clients=clients,
                nodes=nodes
            )
            
            self.results.append(result)
            self._print_result_summary(result)
            return result
            
        except Exception as e:
            import traceback
            print(f"❌ Error in experiment: {e}")
            traceback.print_exc()
            return None
    
    def _collect_metrics(
        self,
        config: Config,
        sim: Simulator,
        clients: List[Client],
        nodes: Dict
    ) -> BenchmarkResult:
        """Collect and aggregate metrics from simulation"""
        
        # Count total messages
        total_messages = sum(getattr(node, 'messages_sent', 0) for node in nodes.values())
        print("DEBUGGG", total_messages)
        # Calculate throughput
        duration = sim.time if sim.time > 0 else 1
        throughput_mps = total_messages / duration if duration > 0 else 0
        
        # Collect latencies
        latencies = []
        for client in clients:
            summary = client.summary()
            if summary:
                latencies.extend([summary['min_latency'], summary['avg_latency'], summary['max_latency']])
        
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
            latency_stats = {
                'min': 0, 'max': 0, 'avg': 0,
                'median': 0, 'p95': 0, 'p99': 0
            }
        ## print all values in node for debug
        for node in nodes.values():
            print("Node ID:", node.id)
            print("Messages Sent:", getattr(node, 'messages_sent', 0))
            print("Store Contents:", node.store)
            print("CPU Usage:", getattr(node, 'cpu_usage', 0))
            print("Memory Usage:", getattr(node, 'memory_usage', 0))
            print("-----")            
        # Count commits
        commits = sum(node.store.get('commits', 0) for node in nodes.values())
        commit_rate = commits / duration if duration > 0 else 0
        
        # Calculate average CPU and memory
        cpu_values = [getattr(node, 'cpu_usage', 0) for node in nodes.values()]
        mem_values = [getattr(node, 'memory_usage', 0) for node in nodes.values()]
        avg_cpu = statistics.mean(cpu_values) if cpu_values else 0
        avg_memory = statistics.mean(mem_values) if mem_values else 0
        
        return BenchmarkResult(
            protocol=config.algorithm,
            num_nodes=config.num_nodes,
            network_delay=config.base_network_delay,
            packet_loss=config.packet_loss_rate,
            num_requests=config.num_requests_per_client,
            duration=duration,
            total_messages=total_messages,
            throughput_mps=throughput_mps,
            latency_min=latency_stats['min'],
            latency_max=latency_stats['max'],
            latency_avg=latency_stats['avg'],
            latency_median=latency_stats['median'],
            latency_p95=latency_stats['p95'],
            latency_p99=latency_stats['p99'],
            commits=commits,
            commit_rate=commit_rate,
            avg_cpu=avg_cpu,
            avg_memory=avg_memory
        )
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not data:
            return 0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]
    
    def _print_result_summary(self, result: BenchmarkResult):
        """Print summary of a benchmark result"""
        print(f"  ✓ Throughput: {result.throughput_mps:.2f} msg/s")
        print(f"  ✓ Latency avg: {result.latency_avg:.4f}ms (p95: {result.latency_p95:.4f}ms)")
        print(f"  ✓ Total messages: {result.total_messages}")
    
    def export_csv(self, filename: Optional[str] = None) -> str:
        """Export results to CSV"""
        if not filename:
            filename = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = [f.name for f in BenchmarkResult.__dataclass_fields__.values()]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.results:
                writer.writerow(asdict(result))
        
        print(f"\n📊 CSV exported: {filepath}")
        return str(filepath)


def main():
    """Run benchmark using algorithm from config.py"""
    print("\n" + "="*70)
    print("🚀 DBSIM Benchmark Suite")
    print("="*70)
    
    runner = BenchmarkRunner(output_dir="benchmark_results")
    
    # Load config - uses algorithm specified in config.py
    config = Config()
    
    print(f"\nℹ️  Using algorithm: {config.algorithm}")
    print(f"ℹ️  Config: {config.num_nodes} nodes, delay={config.base_network_delay}ms, loss={config.packet_loss_rate}")
    
    # Run single experiment with config
    runner.run_experiment(config)
    
    # Export results
    csv_file = runner.export_csv()
    
    print("\n" + "="*70)
    print("✅ Benchmark complete!")
    print("="*70)


if __name__ == "__main__":
    main()
