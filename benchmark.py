import time
import random
import matplotlib
matplotlib.use('Agg') # Safe headless rendering
import matplotlib.pyplot as plt
from engine import StoreEngine

def build_random_graph(V, dense=False):
    g = StoreEngine(V)
    # Assign synthetic 2D coordinates for A* heuristic
    for i in range(V):
        x = (i % 10) * 100 + random.randint(-20, 20)
        y = (i // 10) * 100 + random.randint(-20, 20)
        g.set_node_metadata(i, f"Node {i}", "Zone", "📍", x, y)

    p = 0.4 if dense else (3.5 / V if V > 4 else 0.8)
    for i in range(V):
        for j in range(i + 1, V):
            if random.random() < p:
                weight = random.randint(2, 25)
                g.add_aisle(i, j, weight)
    # Ensure connectivity from 0 to V-1 by adding a chain
    for i in range(V - 1):
        g.add_aisle(i, i + 1, random.randint(2, 10))
    return g

def run_benchmarks():
    sizes = [20, 40, 70, 100, 140, 180]
    dijkstra_sparse, bellman_sparse, astar_sparse = [], [], []
    dijkstra_dense, bellman_dense, astar_dense = [], [], []

    print("==================================================================")
    print("  Analysis of Algorithms (AOA) Empirical Benchmark Evaluation   ")
    print("  Testing Dijkstra vs. A* vs. Bellman-Ford across Graph Densities ")
    print("==================================================================")

    for v in sizes:
        print(f"-> Benchmarking graph size |V| = {v} ...")
        # 1. Sparse Graph
        g_s = build_random_graph(v, dense=False)

        t0 = time.perf_counter()
        g_s.dijkstra(0, v - 1)
        dijkstra_sparse.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        g_s.astar(0, v - 1)
        astar_sparse.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        g_s.bellman_ford(0)
        bellman_sparse.append((time.perf_counter() - t0) * 1000)

        # 2. Dense Graph
        g_d = build_random_graph(v, dense=True)

        t0 = time.perf_counter()
        g_d.dijkstra(0, v - 1)
        dijkstra_dense.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        g_d.astar(0, v - 1)
        astar_dense.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        g_d.bellman_ford(0)
        bellman_dense.append((time.perf_counter() - t0) * 1000)

    # Plot comparisons in high resolution
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), dpi=150)
    plt.style.use('dark_background')

    # Sparse Plot
    ax1.plot(sizes, dijkstra_sparse, 'c-o', label='Dijkstra (Sparse O((V+E)logV))', linewidth=2)
    ax1.plot(sizes, astar_sparse, 'm-^', label='A* Search (Sparse)', linewidth=2)
    ax1.plot(sizes, bellman_sparse, 'r-s', label='Bellman-Ford (Sparse O(VE))', linewidth=2)
    ax1.set_title('Sparse Graph Topology (|E| ≈ 3.5|V|)', fontsize=12, fontweight='bold', color='#38bdf8')
    ax1.set_xlabel('Vertices (|V|)')
    ax1.set_ylabel('Execution Time (milliseconds)')
    ax1.grid(True, linestyle='--', alpha=0.3)
    ax1.legend()

    # Dense Plot
    ax2.plot(sizes, dijkstra_dense, 'c--o', label='Dijkstra (Dense)', linewidth=2)
    ax2.plot(sizes, astar_dense, 'm--^', label='A* Search (Dense)', linewidth=2)
    ax2.plot(sizes, bellman_dense, 'r--s', label='Bellman-Ford (Dense O(V³))', linewidth=2)
    ax2.set_title('Dense Graph Topology (|E| ≈ 0.4|V|²)', fontsize=12, fontweight='bold', color='#f43f5e')
    ax2.set_xlabel('Vertices (|V|)')
    ax2.set_ylabel('Execution Time (milliseconds)')
    ax2.grid(True, linestyle='--', alpha=0.3)
    ax2.legend()

    plt.suptitle('AOA Empirical Benchmark: Dijkstra vs. A* vs. Bellman-Ford', fontsize=15, fontweight='bold', color='white')
    plt.tight_layout()
    output_img = "complexity_benchmark.png"
    plt.savefig(output_img)
    print(f"\n[SUCCESS] Benchmark plots generated and saved as '{output_img}'")

if __name__ == "__main__":
    run_benchmarks()