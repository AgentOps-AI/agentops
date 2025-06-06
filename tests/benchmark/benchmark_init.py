import time


"""
Benchmark script for measuring global tracer initialization time.
"""


def run_benchmark():
    """
    Run a benchmark of global tracer initialization.

    Returns:
        Dictionary with timing results
    """
    import agentops

    # Measure initialization time
    start_init = time.time()
    agentops.init()
    end_init = time.time()
    init_time = end_init - start_init

    return {
        "init": init_time,
        "total": init_time,  # Total time is just init time now
    }


def print_results(results):
    """
    Print benchmark results in a formatted way.

    Args:
        results: Dictionary with timing results
    """
    print("\n=== BENCHMARK RESULTS ===")

    print(f"\nINIT TIME: {results['init']:.6f}s")
    print(f"TOTAL TIME: {results['total']:.6f}s")


if __name__ == "__main__":
    print("Running global tracer benchmark...")
    results = run_benchmark()
    print_results(results)
