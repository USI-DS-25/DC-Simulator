"""
Metrics collection and analysis for distributed system simulation.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import statistics
import json
from datetime import datetime


@dataclass
class LatencyStats:
    """Statistical summary of latencies"""
    count: int = 0
    min: float = float('inf')
    max: float = 0.0
    avg: float = 0.0
    median: float = 0.0
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "count": self.count,
            "min": self.min,
            "max": self.max,
            "avg": self.avg,
            "median": self.median,
            "p50": self.p50,
            "p95": self.p95,
            "p99": self.p99
        }


@dataclass
class ThroughputStats:
    """Throughput statistics"""
    total_messages: int = 0
    messages_per_second: float = 0.0
    bytes_per_second: float = 0.0
    time_window: float = 1.0
    
    def to_dict(self) -> Dict:
        return {
            "total_messages": self.total_messages,
            "messages_per_second": self.messages_per_second,
            "bytes_per_second": self.bytes_per_second,
            "time_window": self.time_window
        }


class LatencyTracker:
    """Track and analyze message latencies"""
    
    def __init__(self):
        self.latencies: List[float] = []
        self.send_times: Dict[str, float] = {}
    
    def record_send(self, msg_id: str, send_time: float):
        """Record when a message was sent"""
        self.send_times[msg_id] = send_time
    
    def record_receive(self, msg_id: str, receive_time: float):
        """Record when a message was received and calculate latency"""
        if msg_id in self.send_times:
            latency = receive_time - self.send_times[msg_id]
            self.latencies.append(latency)
    
    def get_stats(self) -> LatencyStats:
        """Calculate latency statistics"""
        if not self.latencies:
            return LatencyStats()
        
        sorted_latencies = sorted(self.latencies)
        count = len(sorted_latencies)
        
        return LatencyStats(
            count=count,
            min=sorted_latencies[0],
            max=sorted_latencies[-1],
            avg=statistics.mean(sorted_latencies),
            median=statistics.median(sorted_latencies),
            p50=sorted_latencies[int(count * 0.50)] if count > 0 else 0.0,
            p95=sorted_latencies[int(count * 0.95)] if count > 1 else sorted_latencies[-1],
            p99=sorted_latencies[int(count * 0.99)] if count > 1 else sorted_latencies[-1]
        )
    
    def reset(self):
        """Reset all tracked latencies"""
        self.latencies.clear()
        self.send_times.clear()


class ThroughputTracker:
    """Track message throughput over time"""
    
    def __init__(self, window_size: float = 1.0):
        self.window_size = window_size
        self.message_times: List[float] = []
        self.message_sizes: List[int] = []
    
    def record_message(self, timestamp: float, size_bytes: int = 0):
        """Record a message at the given timestamp"""
        self.message_times.append(timestamp)
        self.message_sizes.append(size_bytes)
    
    def get_stats(self, current_time: float) -> ThroughputStats:
        """Calculate throughput for the current time window"""
        window_start = max(0, current_time - self.window_size)
        
        recent_messages = [t for t in self.message_times if t >= window_start]
        recent_sizes = [self.message_sizes[i] for i, t in enumerate(self.message_times) if t >= window_start]
        
        total_msgs = len(recent_messages)
        total_bytes = sum(recent_sizes)
        
        mps = total_msgs / self.window_size if self.window_size > 0 else 0.0
        bps = total_bytes / self.window_size if self.window_size > 0 else 0.0
        
        return ThroughputStats(
            total_messages=total_msgs,
            messages_per_second=mps,
            bytes_per_second=bps,
            time_window=self.window_size
        )
    
    def reset(self):
        self.message_times.clear()
        self.message_sizes.clear()


class MetricsCollector:
    """Collect and analyze simulation metrics"""
    
    def __init__(self):
        self.start_time: float = 0.0
        self.latency_trackers: Dict[str, LatencyTracker] = {}
        self.throughput_trackers: Dict[str, ThroughputTracker] = {}
        
        self.packets_sent = 0
        self.packets_dropped = 0
        self.packets_received = 0
        self.sync_violations = 0
        self.sync_timeouts = 0
        self.node_failures = 0
        self.partition_events = 0
    
    def reset(self):
        """Reset all metrics"""
        self.start_time = 0.0
        self.latency_trackers.clear()
        self.throughput_trackers.clear()
        self.packets_sent = 0
        self.packets_dropped = 0
        self.packets_received = 0
        self.sync_violations = 0
        self.sync_timeouts = 0
        self.node_failures = 0
        self.partition_events = 0
    
    def record_send(self, src_id: str, dst_id: str, msg_id: str, timestamp: float, size_bytes: int = 100):
        """Record a message send"""
        self.packets_sent += 1
        
        key = f"{src_id}_{dst_id}"
        if key not in self.latency_trackers:
            self.latency_trackers[key] = LatencyTracker()
        if key not in self.throughput_trackers:
            self.throughput_trackers[key] = ThroughputTracker()
        
        self.latency_trackers[key].record_send(msg_id, timestamp)
        self.throughput_trackers[key].record_message(timestamp, size_bytes)
    
    def record_receive(self, dst_id: str, msg_id: str, timestamp: float):
        """Record a message receive"""
        self.packets_received += 1
        
        for tracker in self.latency_trackers.values():
            tracker.record_receive(msg_id, timestamp)
    
    def record_packet_drop(self):
        """Record a dropped packet"""
        self.packets_dropped += 1
    
    def record_sync_violation(self):
        """Record a synchronization violation"""
        self.sync_violations += 1
    
    def record_sync_timeout(self):
        """Record a synchronization timeout"""
        self.sync_timeouts += 1
    
    def record_node_failure(self):
        """Record a node failure"""
        self.node_failures += 1
    
    def record_partition_event(self):
        """Record a network partition event"""
        self.partition_events += 1
    
    def get_global_stats(self, current_time: float) -> Dict[str, Any]:
        """Get global statistics"""
        delivery_rate = 1.0 - (self.packets_dropped / self.packets_sent if self.packets_sent > 0 else 0)
        
        latency_stats = {}
        for key, tracker in self.latency_trackers.items():
            latency_stats[key] = tracker.get_stats().to_dict()
        
        throughput_stats = {}
        for key, tracker in self.throughput_trackers.items():
            throughput_stats[key] = tracker.get_stats(current_time).to_dict()
        
        return {
            "packets_sent": self.packets_sent,
            "packets_dropped": self.packets_dropped,
            "packets_received": self.packets_received,
            "delivery_rate": delivery_rate,
            "sync_violations": self.sync_violations,
            "sync_timeouts": self.sync_timeouts,
            "node_failures": self.node_failures,
            "partition_events": self.partition_events,
            "latency_stats": latency_stats,
            "throughput_stats": throughput_stats
        }
    
    def get_node_stats(self, node_id: str, current_time: float) -> Dict[str, Any]:
        """Get per-node statistics"""
        node_latencies = {}
        node_throughput = {}
        
        for key, tracker in self.latency_trackers.items():
            if key.startswith(node_id):
                node_latencies[key] = tracker.get_stats().to_dict()
            if key.endswith(node_id):
                node_throughput[key] = tracker.get_stats(current_time).to_dict()
        
        return {
            "node_id": node_id,
            "latencies": node_latencies,
            "throughput": node_throughput
        }
    
    def export_to_json(self, filepath: str, current_time: float):
        """Export metrics to JSON"""
        stats = self.get_global_stats(current_time)
        
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def export_to_csv(self, filepath: str, current_time: float):
        """Export metrics to CSV"""
        import csv
        
        stats = self.get_global_stats(current_time)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])
            
            for key, value in stats.items():
                if not isinstance(value, dict):
                    writer.writerow([key, value])
