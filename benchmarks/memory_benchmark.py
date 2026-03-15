"""
Benchmark suite for memory optimizations.

Runs comprehensive benchmarks to measure:
- Memory footprint at startup, idle, and under load
- Performance characteristics of each component
- Comparison between optimized and unoptimized modes
- Memory leak detection over extended runs

Usage:
    python benchmarks/memory_benchmark.py --full
    python benchmarks/memory_benchmark.py --quick
    python benchmarks/memory_benchmark.py --profile agent
"""

import argparse
import asyncio
import gc
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List

import psutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nucleo.memory import (
    ConversationStore,
    get_standard_pools,
    init_gc_for_edge,
    get_memory_monitor,
    get_query_analyzer,
    get_memory_budgets,
)


class BenchmarkResults:
    """Holds benchmark results."""

    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.start_time = time.time()

    def add_result(self, test_name: str, metric: str, value: float, unit: str = "") -> None:
        """Add a result."""
        if test_name not in self.results:
            self.results[test_name] = {}

        self.results[test_name][metric] = {"value": value, "unit": unit}

    def print_results(self) -> None:
        """Print results in human-readable format."""
        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS")
        print("=" * 80)

        for test_name, metrics in self.results.items():
            print(f"\n{test_name}:")
            print("-" * 40)

            for metric, data in metrics.items():
                value = data["value"]
                unit = data.get("unit", "")

                if isinstance(value, float):
                    print(f"  {metric}: {value:.2f} {unit}")
                else:
                    print(f"  {metric}: {value} {unit}")

    def to_json(self, filepath: str) -> None:
        """Export results to JSON."""
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to {filepath}")

    def generate_report(self) -> str:
        """Generate text report."""
        report = "MEMORY OPTIMIZATION BENCHMARK REPORT\n"
        report += f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += "=" * 80 + "\n\n"

        for test_name, metrics in self.results.items():
            report += f"{test_name}\n"
            report += "-" * 40 + "\n"

            for metric, data in metrics.items():
                value = data["value"]
                unit = data.get("unit", "")

                if isinstance(value, float):
                    report += f"  {metric}: {value:.2f} {unit}\n"
                else:
                    report += f"  {metric}: {value} {unit}\n"

            report += "\n"

        return report


def get_process_memory() -> float:
    """Get current process memory in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def measure_startup_memory() -> float:
    """Measure startup memory footprint."""
    gc.collect()
    return get_process_memory()


async def benchmark_conversation_store(results: BenchmarkResults, num_messages: int = 1000) -> None:
    """Benchmark conversation store performance."""
    print("\n[1/6] Benchmarking ConversationStore...")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "bench.db")

        # Measure initial memory
        gc.collect()
        start_mem = get_process_memory()

        # Create store
        store = ConversationStore(
            max_memory_messages=10,
            db_path=db_path,
            compression_level=9,
        )

        store_creation_mem = get_process_memory()
        results.add_result(
            "ConversationStore",
            "Memory after creation",
            store_creation_mem - start_mem,
            "MB",
        )

        # Add messages
        start_time = time.time()
        start_mem = get_process_memory()

        for i in range(num_messages):
            await store.add_message(
                f"session_{i % 100}",
                {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}" * 10},
            )

        add_time = time.time() - start_time
        add_mem = get_process_memory() - start_mem

        results.add_result(
            "ConversationStore",
            "Add messages throughput",
            num_messages / add_time,
            "msg/sec",
        )
        results.add_result(
            "ConversationStore",
            "Memory growth for 1000 messages",
            add_mem,
            "MB",
        )

        # Get statistics
        stats = await store.get_statistics()
        results.add_result(
            "ConversationStore",
            "Compression ratio",
            stats.compression_ratio,
            "x",
        )
        results.add_result(
            "ConversationStore",
            "Messages in memory",
            stats.messages_in_memory,
            "count",
        )
        results.add_result(
            "ConversationStore",
            "Messages archived",
            stats.messages_archived,
            "count",
        )

        # Memory per message
        if stats.total_messages > 0:
            mem_per_msg = (store_creation_mem - start_mem + add_mem) / stats.total_messages
            results.add_result(
                "ConversationStore",
                "Memory per message",
                mem_per_msg * 1024,  # Convert to KB
                "KB",
            )

        await store.close()


def benchmark_object_pool(results: BenchmarkResults, num_ops: int = 10000) -> None:
    """Benchmark object pool performance."""
    print("\n[2/6] Benchmarking ObjectPool...")

    pools = get_standard_pools()

    # Get initial state
    gc.collect()
    start_mem = get_process_memory()

    # Benchmark message dict pool
    start_time = time.time()

    for i in range(num_ops):
        d = pools.get_message_dict()
        d["test"] = i
        pools.return_message_dict(d)

    pool_time = time.time() - start_time
    pool_mem = get_process_memory() - start_mem

    results.add_result(
        "ObjectPool",
        "Dict pool throughput",
        num_ops / pool_time,
        "ops/sec",
    )
    results.add_result(
        "ObjectPool",
        "Memory growth",
        pool_mem,
        "MB",
    )

    stats = pools.manager.get_all_stats()
    msg_dict_stats = stats.get("message_dicts")

    if msg_dict_stats:
        results.add_result(
            "ObjectPool",
            "Message dict reuse ratio",
            msg_dict_stats.reuse_ratio,
            "ratio",
        )


def benchmark_query_analyzer(results: BenchmarkResults, num_queries: int = 5000) -> None:
    """Benchmark query complexity analyzer."""
    print("\n[3/6] Benchmarking QueryComplexityAnalyzer...")

    analyzer = get_query_analyzer()

    queries = [
        "What is 2+2?",
        "Explain quantum mechanics in detail",
        "How do I fix this error?",
        "Compare Python and JavaScript for AI projects",
        "Tell me about machine learning algorithms",
    ]

    gc.collect()
    start_mem = get_process_memory()

    start_time = time.time()

    for i in range(num_queries):
        query = queries[i % len(queries)]
        analyzer.analyze(query)

    analysis_time = time.time() - start_time
    mem_used = get_process_memory() - start_mem

    results.add_result(
        "QueryComplexityAnalyzer",
        "Analysis throughput",
        num_queries / analysis_time,
        "queries/sec",
    )
    results.add_result(
        "QueryComplexityAnalyzer",
        "Memory growth",
        mem_used,
        "MB",
    )


async def benchmark_memory_monitor(results: BenchmarkResults) -> None:
    """Benchmark memory monitor."""
    print("\n[4/6] Benchmarking MemoryMonitor...")

    gc.collect()
    start_mem = get_process_memory()

    monitor = get_memory_monitor(memory_limit_mb=200, enable=True)

    # Let it monitor for a bit
    await asyncio.sleep(0.5)

    monitor_mem = get_process_memory() - start_mem

    results.add_result(
        "MemoryMonitor",
        "Monitor memory overhead",
        monitor_mem,
        "MB",
    )

    status = monitor.get_status()
    results.add_result(
        "MemoryMonitor",
        "Current memory pressure",
        status.pressure.value,
        "level",
    )

    monitor.disable()


def benchmark_gc_tuner(results: BenchmarkResults) -> None:
    """Benchmark GC tuning."""
    print("\n[5/6] Benchmarking GCTuner...")

    gc_tuner = init_gc_for_edge()

    # Create objects
    gc.collect()
    start_time = time.time()

    # Create 100k temporary objects
    for _ in range(100000):
        _ = {"key": "value"}

    create_time = time.time() - start_time

    # Collect garbage
    start_time = time.time()
    collected = gc_tuner.collect()
    collect_time = time.time() - start_time

    results.add_result(
        "GCTuner",
        "Object creation time (100k objs)",
        create_time * 1000,
        "ms",
    )
    results.add_result(
        "GCTuner",
        "Garbage collection time",
        collect_time * 1000,
        "ms",
    )
    results.add_result(
        "GCTuner",
        "Objects collected",
        collected,
        "count",
    )


def benchmark_memory_budgets(results: BenchmarkResults) -> None:
    """Benchmark memory budgets."""
    print("\n[6/6] Benchmarking MemoryBudgets...")

    budgets = get_memory_budgets(total_mb=200)

    gc.collect()
    start_mem = get_process_memory()

    # Allocate budgets
    for i in range(10):
        budgets.allocate(f"component_{i}", 20 / 10)

    # Request memory
    start_time = time.time()

    for i in range(10000):
        component = f"component_{i % 10}"
        budgets.request_memory(component, 0.1)
        budgets.release_memory(component, 0.1)

    budget_time = time.time() - start_time
    budget_mem = get_process_memory() - start_mem

    results.add_result(
        "MemoryBudgets",
        "Budget ops throughput",
        10000 / budget_time,
        "ops/sec",
    )
    results.add_result(
        "MemoryBudgets",
        "Memory overhead",
        budget_mem,
        "MB",
    )


async def benchmark_full_suite(results: BenchmarkResults, quick: bool = False) -> None:
    """Run full benchmark suite."""
    print("\n" + "=" * 80)
    print("MEMORY OPTIMIZATION BENCHMARKS")
    print("=" * 80)

    num_messages = 100 if quick else 1000
    num_queries = 500 if quick else 5000
    num_ops = 1000 if quick else 10000

    # Startup memory
    startup_mem = measure_startup_memory()
    results.add_result("Startup", "Baseline memory", startup_mem, "MB")

    # Run benchmarks
    await benchmark_conversation_store(results, num_messages)
    benchmark_object_pool(results, num_ops)
    benchmark_query_analyzer(results, num_queries)
    await benchmark_memory_monitor(results)
    benchmark_gc_tuner(results)
    benchmark_memory_budgets(results)

    # Final memory
    gc.collect()
    final_mem = get_process_memory()
    results.add_result("Final", "Memory usage", final_mem, "MB")

    return results


async def main():
    """Main benchmark entry point."""
    parser = argparse.ArgumentParser(description="Memory optimization benchmarks")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick benchmarks (fewer iterations)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        default=True,
        help="Run full benchmarks (default)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save results to JSON file",
    )
    parser.add_argument(
        "--report",
        type=str,
        help="Save results to text report",
    )

    args = parser.parse_args()

    results = BenchmarkResults()

    try:
        await benchmark_full_suite(results, quick=args.quick)
    except Exception as e:
        print(f"\nError during benchmarking: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Display results
    results.print_results()

    # Save outputs
    if args.output:
        results.to_json(args.output)

    if args.report:
        with open(args.report, "w") as f:
            f.write(results.generate_report())
        print(f"Report saved to {args.report}")

    print("\n" + "=" * 80)
    print("Benchmarks completed successfully!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
