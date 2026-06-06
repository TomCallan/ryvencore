import time
import threading
from collections import defaultdict
from typing import Dict, List, Optional, Any


class Metrics:
    """
    Centralized metrics collection for benchmarking and performance analysis.

    Tracks compilation times, execution times per algorithm mode,
    node/edge counts, data volume, and provides comparison summaries
    that demonstrate compilation speedup over naive interpretation.

    Usage:
        metrics = Metrics()

        metrics.start_compile('my_flow')
        # ... compilation work ...
        metrics.stop_compile('my_flow', 42, 18)  # nodes, edges

        metrics.start_execution('my_flow', 'data')
        # ... execution work ...
        metrics.stop_execution('my_flow', 'data', bytes_processed=1_000_000)

        print(metrics.summary())
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Compilation records: flow_name -> {compile_time_s, nodes, edges, timestamp}
        self._compilations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Execution records: flow_name -> {mode -> [exec_time_s, bytes_processed, timestamp]}
        self._executions: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

        # Per-session accumulators
        self._compile_starts: Dict[str, float] = {}
        self._exec_starts: Dict[str, float] = {}

    # ---- Compilation timing ----

    def start_compile(self, flow_name: str) -> None:
        """Begin timing a compilation."""
        with self._lock:
            self._compile_starts[flow_name] = time.perf_counter()

    def stop_compile(self, flow_name: str, node_count: int = 0, edge_count: int = 0) -> float:
        """
        Stop timing a compilation and record results.
        Returns the elapsed time in seconds.
        """
        elapsed = time.perf_counter() - self._compile_starts.pop(flow_name, time.perf_counter())
        with self._lock:
            self._compilations[flow_name].append({
                'elapsed_s': elapsed,
                'nodes': node_count,
                'edges': edge_count,
                'timestamp': time.time(),
            })
        return elapsed

    def last_compile_time(self, flow_name: str) -> Optional[float]:
        """Get the most recent compilation time for a flow."""
        recs = self._compilations.get(flow_name, [])
        return recs[-1]['elapsed_s'] if recs else None

    # ---- Execution timing ----

    def start_execution(self, flow_name: str, mode: str) -> None:
        """Begin timing an execution in a given algorithm mode."""
        key = f"{flow_name}:{mode}"
        self._exec_starts[key] = time.perf_counter()

    def stop_execution(self, flow_name: str, mode: str,
                       bytes_processed: int = 0, rows_processed: int = 0,
                       iterations: int = 1) -> float:
        """
        Stop timing an execution and record results.
        Returns the elapsed time in seconds.
        """
        key = f"{flow_name}:{mode}"
        elapsed = time.perf_counter() - self._exec_starts.pop(key, time.perf_counter())
        with self._lock:
            self._executions[flow_name][mode].append({
                'elapsed_s': elapsed,
                'bytes_processed': bytes_processed,
                'rows_processed': rows_processed,
                'iterations': iterations,
                'timestamp': time.time(),
            })
        return elapsed

    def avg_execution_time(self, flow_name: str, mode: str) -> Optional[float]:
        """Average execution time for a flow/mode combination."""
        recs = self._executions.get(flow_name, {}).get(mode, [])
        if not recs:
            return None
        return sum(r['elapsed_s'] for r in recs) / len(recs)

    # ---- Speedup analysis ----

    def speedup_over_naive(self, flow_name: str, mode: str) -> Optional[float]:
        """
        Compute speedup of a given mode over naive data flow.
        speedup = naive_time / mode_time.  >1 means faster.
        """
        naive_avg = self.avg_execution_time(flow_name, 'data')
        mode_avg = self.avg_execution_time(flow_name, mode)
        if naive_avg and mode_avg and mode_avg > 0:
            return naive_avg / mode_avg
        return None

    def compilation_speedup_over_naive(self, flow_name: str) -> Optional[float]:
        """
        Speedup of compiled mode vs naive data flow execution.
        Compares average compiled execution time vs average naive execution time.
        """
        return self.speedup_over_naive(flow_name, 'compiled')

    # ---- Throughput ----

    def throughput_mb_s(self, flow_name: str, mode: str) -> Optional[float]:
        """Compute throughput in MB/s for a flow/mode."""
        recs = self._executions.get(flow_name, {}).get(mode, [])
        if not recs:
            return None
        total_bytes = sum(r.get('bytes_processed', 0) for r in recs)
        total_time = sum(r['elapsed_s'] for r in recs)
        if total_time > 0:
            return (total_bytes / (1024 * 1024)) / total_time
        return None

    # ---- Summary ----

    def summary(self, flow_name: Optional[str] = None) -> str:
        """
        Return a human-readable metrics summary.
        If flow_name is omitted, summarize all tracked flows.
        """
        lines = []
        flows = [flow_name] if flow_name else list(
            set(self._compilations.keys()) | set(self._executions.keys())
        )

        for fn in flows:
            lines.append(f"\n{'='*60}")
            lines.append(f"  Flow: {fn}")
            lines.append(f"{'='*60}")

            # Compilation info
            comps = self._compilations.get(fn, [])
            if comps:
                last = comps[-1]
                lines.append(f"  Compilation: {last['elapsed_s']*1000:.2f} ms "
                             f"(nodes={last['nodes']}, edges={last['edges']})")

            # Per-mode execution info
            modes = self._executions.get(fn, {})
            if modes:
                lines.append(f"  Execution Times:")
                for mode in ['data', 'data opt', 'exec', 'compiled']:
                    recs = modes.get(mode, [])
                    if recs:
                        avg = sum(r['elapsed_s'] for r in recs) / len(recs)
                        lines.append(f"    {mode:12s}: avg {avg*1000:10.3f} ms  "
                                     f"(n={len(recs)})")

                # Speedup table
                naive_avg = self.avg_execution_time(fn, 'data')
                if naive_avg and naive_avg > 0:
                    lines.append(f"  Speedup vs naive data flow:")
                    for mode in ['data opt', 'exec', 'compiled']:
                        sp = self.speedup_over_naive(fn, mode)
                        if sp is not None:
                            lines.append(f"    {mode:12s}: {sp:.2f}x")

                # Throughput
                lines.append(f"  Throughput (MB/s):")
                for mode in modes:
                    tp = self.throughput_mb_s(fn, mode)
                    if tp is not None:
                        lines.append(f"    {mode:12s}: {tp:.2f} MB/s")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Return all metrics as a serializable dictionary."""
        result = {
            'compilations': dict(self._compilations),
            'executions': {},
        }
        for flow_name, modes in self._executions.items():
            result['executions'][flow_name] = dict(modes)
        return result

    def reset(self) -> None:
        """Clear all collected metrics."""
        with self._lock:
            self._compilations.clear()
            self._executions.clear()
            self._compile_starts.clear()
            self._exec_starts.clear()


# Global singleton for convenience
_global_metrics = Metrics()


def global_metrics() -> Metrics:
    """Return the global Metrics singleton."""
    return _global_metrics
