"""
Comprehensive benchmarking module for DBSIM.
Runs controlled experiments across protocols, measures performance metrics,
and generates comparative analysis reports.
"""

import json
import time
import statistics
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
import csv
from pathlib import Path

from simulator import Simulator
from Network import Network
from client import Client
from metrics import MetricsCollector, LatencyTracker, ThroughputTracker
from logger import Logger
from algorithms import ALGORITHM_REGISTRY
from config import Config


@dataclass
class BenchmarkResult:
    """Stores results from a single benchmark run"""
    protocol: str
    num_nodes: int
    network_delay: float  # milliseconds
    packet_loss: float  # 0-1
    num_requests: int
    duration: float  # simulation time
    
    # Throughput metrics
    total_messages: int
    throughput_mps: float  # messages per second
    
    # Latency metrics
    latency_min: float
    latency_max: float
    latency_avg: float
    latency_median: float
    latency_p95: float
    latency_p99: float
    
    # Protocol-specific metrics
    commits: int = 0
    aborts: int = 0
    commit_rate: float = 0.0  # commits per second
    
    # Resource metrics
    avg_cpu: float = 0.0
    avg_memory: float = 0.0
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark suite"""
    protocols: List[str] = field(default_factory=lambda: ['primary_backup', 'paxos', 'raft', 'lowi'])
    num_nodes_list: List[int] = field(default_factory=lambda: [3, 5, 7])
    network_delays: List[float] = field(default_factory=lambda: [1.0, 5.0, 10.0])  # ms
    packet_losses: List[float] = field(default_factory=lambda: [0.0, 0.01, 0.05])  # 0-1
    num_requests: int = 1000
    duration: float = 100.0
    repeats: int = 3


class BenchmarkRunner:
    """Runs controlled experiments and collects metrics"""
    
    def __init__(self, output_dir: str = "benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: List[BenchmarkResult] = []
        self.logger = Logger()
        self.protocol_map = ALGORITHM_REGISTRY
    
    def run_benchmark(self, config: BenchmarkConfig) -> List[BenchmarkResult]:
        """Run complete benchmark suite"""
        print("\n" + "="*70)
        print("🔬 DBSIM Benchmark Suite - Starting")
        print("="*70)
        
        total_experiments = (
            len(config.protocols) * 
            len(config.num_nodes_list) * 
            len(config.network_delays) * 
            len(config.packet_losses) * 
            config.repeats
        )
        print(f"\n📊 Total experiments: {total_experiments}")
        print(f"📁 Results directory: {self.output_dir}\n")
        
        experiment_num = 0
        
        for protocol in config.protocols:
            if not self._protocol_available(protocol):
                print(f"⚠️  Skipping {protocol} (not available)")
                continue
            
            print(f"\n{'─'*70}")
            print(f"Protocol: {protocol}")
            print(f"{'─'*70}")
            
            for num_nodes in config.num_nodes_list:
                for network_delay in config.network_delays:
                    for packet_loss in config.packet_losses:
                        for repeat in range(config.repeats):
                            experiment_num += 1
                            print(f"\n[{experiment_num}/{total_experiments}] "
                                  f"{protocol} | N={num_nodes} | "
                                  f"delay={network_delay}ms | "
                                  f"loss={packet_loss*100:.1f}% | "
                                  f"run {repeat+1}/{config.repeats}")
                            
                            result = self._run_single_experiment(
                                protocol=protocol,
                                num_nodes=num_nodes,
                                network_delay=network_delay,
                                packet_loss=packet_loss,
                                num_requests=config.num_requests,
                                duration=config.duration
                            )
                            
                            if result:
                                self.results.append(result)
                                self._print_result_summary(result)
        
        print("\n" + "="*70)
        print("✅ Benchmark suite completed!")
        print("="*70)
        
        return self.results
    
    def _protocol_available(self, protocol: str) -> bool:
        """Check if protocol implementation is available"""
        return protocol in self.protocol_map
    
    def _run_single_experiment(
        self,
        protocol: str,
        num_nodes: int,
        network_delay: float,
        packet_loss: float,
        num_requests: int,
        duration: float
    ) -> Optional[BenchmarkResult]:
        """Run a single benchmark experiment"""
        try:
            # Setup
            cfg = Config()
            cfg.algorithm = protocol
            cfg.num_nodes = num_nodes
            cfg.base_network_delay = network_delay
            cfg.packet_loss_rate = packet_loss
            
            sim = Simulator()
            sim.config = cfg
            net = Network(sim, cfg)
            sim.metrics = MetricsCollector()
            
            # Create nodes
            node_ids = list(range(num_nodes))
            nodes = {}
            
            for nid in node_ids:
                algorithm_case = self.protocol_map[protocol]
                node = algorithm_case.create_node(nid, sim, net, node_ids)
                if nid == 0:
                    node.store['role'] = 'PRIMARY'
                else:
                    node.store['role'] = 'BACKUP'
                nodes[nid] = node
                sim.nodes[nid] = node
            
            # Create clients
            clients = [Client(i, sim, net, sim.logger) for i in range(num_requests)]
            for i, client in enumerate(clients):
                # sim.schedule(0.1 * (i % 10), "CLIENT_START", client.id, {})
                sim.schedule(0.1 * (i % 10), "MESSAGE", client.id, {"src": client.id, "msg": f"request_from_client_{i}"})
            
            # Run simulation
            start_time = time.time()
            sim.run(until_time=duration)
            elapsed = time.time() - start_time
            
            # Collect metrics
            result = self._collect_metrics(
                protocol=protocol,
                num_nodes=num_nodes,
                network_delay=network_delay,
                packet_loss=packet_loss,
                num_requests=num_requests,
                sim=sim,
                clients=clients,
                nodes=nodes,
                duration=sim.time
            )
            
            return result
            
        except Exception as e:
            print(f"❌ Error in experiment: {e}")
            return None
    
    def _collect_metrics(
        self,
        protocol: str,
        num_nodes: int,
        network_delay: float,
        packet_loss: float,
        num_requests: int,
        sim: Simulator,
        clients: List[Client],
        nodes: Dict,
        duration: float
    ) -> BenchmarkResult:
        """Collect and aggregate metrics from simulation"""
        
        # Count total messages
        total_messages = sum(node.messages_sent for node in nodes.values())
        
        # Calculate throughput
        throughput_mps = total_messages / duration if duration > 0 else 0
        
        # Collect latencies
        latencies = [client.latency for client in clients if hasattr(client, 'latency') and client.latency > 0]
        
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
        
        # Count commits (protocol-specific)
        commits = sum(node.store.get('commits', 0) for node in nodes.values())
        commit_rate = commits / duration if duration > 0 else 0
        
        # Calculate average CPU and memory
        avg_cpu = statistics.mean([node.cpu_usage for node in nodes.values()]) if nodes else 0
        avg_memory = statistics.mean([node.memory_usage for node in nodes.values()]) if nodes else 0
        
        return BenchmarkResult(
            protocol=protocol,
            num_nodes=num_nodes,
            network_delay=network_delay,
            packet_loss=packet_loss,
            num_requests=num_requests,
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
        print(f"  ✓ Latency avg: {result.latency_avg:.4f}ms "
              f"(p95: {result.latency_p95:.4f}ms, p99: {result.latency_p99:.4f}ms)")
        print(f"  ✓ Total messages: {result.total_messages}")
        print(f"  ✓ CPU: {result.avg_cpu:.1f}%, Memory: {result.avg_memory:.1f}%")
    
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
    
    def export_json(self, filename: Optional[str] = None) -> str:
        """Export results to JSON"""
        if not filename:
            filename = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.output_dir / filename
        
        data = [asdict(result) for result in self.results]
        
        with open(filepath, 'w') as jsonfile:
            json.dump(data, jsonfile, indent=2)
        
        print(f"📄 JSON exported: {filepath}")
        return str(filepath)
    
    def generate_report(self, filename: Optional[str] = None) -> str:
        """Generate comprehensive markdown report"""
        if not filename:
            filename = f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        filepath = self.output_dir / filename
        
        report = self._build_report()
        
        with open(filepath, 'w') as f:
            f.write(report)
        
        print(f"📋 Report generated: {filepath}")
        return str(filepath)
    
    def _build_report(self) -> str:
        """Build comprehensive markdown report"""
        report = "# DBSIM Benchmark Report\n\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Summary statistics
        report += "## Summary\n\n"
        if self.results:
            protocols = set(r.protocol for r in self.results)
            report += f"- **Protocols tested**: {', '.join(protocols)}\n"
            report += f"- **Total experiments**: {len(self.results)}\n"
            report += f"- **Date**: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        
        # Results by protocol
        report += "## Results by Protocol\n\n"
        
        for protocol in set(r.protocol for r in self.results):
            protocol_results = [r for r in self.results if r.protocol == protocol]
            report += f"### {protocol.upper()}\n\n"
            
            # Throughput comparison
            report += "#### Throughput (messages/second)\n\n"
            report += "| Nodes | Delay (ms) | Loss (%) | Throughput |\n"
            report += "|-------|-----------|----------|------------|\n"
            
            for result in sorted(protocol_results, key=lambda x: (x.num_nodes, x.network_delay, x.packet_loss)):
                report += f"| {result.num_nodes} | {result.network_delay} | {result.packet_loss*100:.1f} | {result.throughput_mps:.2f} |\n"
            
            report += "\n"
            
            # Latency comparison
            report += "#### Latency (milliseconds)\n\n"
            report += "| Nodes | Delay (ms) | Loss (%) | Avg | P95 | P99 |\n"
            report += "|-------|-----------|----------|-----|-----|-----|\n"
            
            for result in sorted(protocol_results, key=lambda x: (x.num_nodes, x.network_delay, x.packet_loss)):
                report += f"| {result.num_nodes} | {result.network_delay} | {result.packet_loss*100:.1f} | {result.latency_avg:.4f} | {result.latency_p95:.4f} | {result.latency_p99:.4f} |\n"
            
            report += "\n"
        
        # Protocol comparison
        report += "## Protocol Comparison\n\n"
        report += "### Throughput (baseline: 3 nodes, 1ms delay, 0% loss)\n\n"
        report += "| Protocol | Throughput (msg/s) |\n"
        report += "|----------|------------------|\n"
        
        baseline = [r for r in self.results if r.num_nodes == 3 and r.network_delay == 1.0 and r.packet_loss == 0.0]
        for result in sorted(baseline, key=lambda x: x.protocol):
            report += f"| {result.protocol} | {result.throughput_mps:.2f} |\n"
        
        report += "\n"
        
        # Effect of network conditions
        report += "## Effect of Network Conditions\n\n"
        report += "### Impact of Packet Loss (Primary-Backup, 5 nodes, 5ms delay)\n\n"
        report += "| Loss (%) | Throughput | Latency (avg) |\n"
        report += "|----------|-----------|---------------|\n"
        
        pb_results = [r for r in self.results if r.protocol == 'primary_backup' and r.num_nodes == 5 and r.network_delay == 5.0]
        for result in sorted(pb_results, key=lambda x: x.packet_loss):
            report += f"| {result.packet_loss*100:.1f} | {result.throughput_mps:.2f} | {result.latency_avg:.4f} |\n"
        
        report += "\n"
        
        # Scalability analysis
        report += "## Scalability Analysis\n\n"
        report += "### Impact of Node Count (Primary-Backup, 1ms delay, 0% loss)\n\n"
        report += "| Nodes | Throughput | Latency (avg) |\n"
        report += "|-------|-----------|---------------|\n"
        
        scale_results = [r for r in self.results if r.protocol == 'primary_backup' and r.network_delay == 1.0 and r.packet_loss == 0.0]
        for result in sorted(scale_results, key=lambda x: x.num_nodes):
            report += f"| {result.num_nodes} | {result.throughput_mps:.2f} | {result.latency_avg:.4f} |\n"
        
        report += "\n"
        
        # Recommendations
        report += "## Recommendations\n\n"
        
        best_throughput = max(self.results, key=lambda r: r.throughput_mps) if self.results else None
        if best_throughput:
            report += f"- **Best throughput**: {best_throughput.protocol} with {best_throughput.throughput_mps:.2f} msg/s\n"
        
        best_latency = min(self.results, key=lambda r: r.latency_avg) if self.results else None
        if best_latency:
            report += f"- **Best latency**: {best_latency.protocol} with {best_latency.latency_avg:.4f}ms average\n"
        
        report += "\n---\n"
        report += "Generated by DBSIM Benchmark Suite\n"
        
        return report


def main():
    """Run benchmark suite with default configuration"""
    print("\n🚀 DBSIM Simple Test Benchmarking Suite\n")
    
    # Create benchmark configuration
    config = BenchmarkConfig(
        # protocols=['simple_test', 'paxos'],
        protocols=['paxos'],
        num_nodes_list=[3, 5],
        network_delays=[1.0, 5.0],
        packet_losses=[0.0, 0.01],
        num_requests=100,
        duration=50.0,
        repeats=1
    )
    
    # Run benchmarks
    runner = BenchmarkRunner(output_dir="benchmark_results")
    results = runner.run_benchmark(config)
    
    # Export results (CSV only)
    csv_file = runner.export_csv()
    
    print(f"\n✅ Benchmark complete!")
    print(f"   Results: {csv_file}")


if __name__ == "__main__":
    main()
