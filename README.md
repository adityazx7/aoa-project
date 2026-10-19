# Store Navigator Pro (AOA Spatial Routing Engine)

> **Analysis of Algorithms (AOA) Enterprise Project**: Indoor Retail Spatial Graph Navigation, Multi-Algorithm Pathfinding, Dynamic Telemetry Injection, and Multi-Stop Order Picking Optimization.

---

## 🌟 Key Features

### 1. High-Performance Graph Engine (`engine.py`)
- **Dijkstra's Algorithm with Min-Heap Priority Queue**: $O((|V| + |E|) \log |V|)$ single-source shortest paths with early exit optimization.
- **A\* Search Algorithm**: Goal-directed heuristic search using admissible Euclidean distance $f(n) = g(n) + h(n)$.
- **Bellman-Ford Algorithm**: $O(|V| \cdot |E|)$ dynamic programming edge relaxation with negative-weight cycle detection.
- **Breadth-First Search (BFS)**: $O(|V| + |E|)$ unweighted shortest hop pathfinder.
- **Floyd-Warshall All-Pairs Shortest Path (APSP)**: $O(|V|^3)$ dynamic programming with full predecessor matrix path reconstruction.
- **Held-Karp Dynamic Programming (Exact TSP)**: $O(n^2 2^n)$ bitmask dynamic programming for multi-item grocery order picking with intermediate aisle walk paths.

### 2. Next-Gen Cyber-Slate Interactive Frontend (`index.html`)
- **Retina-Ready High-DPI Canvas**: Smooth pan, zoom, click-to-set start (🚩) and target (🏁) nodes.
- **Dynamic Neon Laser Route Animation**: Flowing particle beam tracing the exact aisle trajectory.
- **Animated Shopper Cart Avatar**: Real-time position interpolation along calculated paths.
- **Step-by-Step Traversal Inspector & Player**:
  - Step Forward / Step Backward / Play / Pause / Scrub slider.
  - Live Priority Queue / Min-Heap frontier viewer.
  - Step description narrative explaining edge relaxations and distance updates.
- **Dynamic Telemetry & Congestion Simulator**: Click any aisle or edge to adjust foot traffic penalties in real time.
- **Live Empirical Benchmark Arena**: Side-by-side performance showdown (runtime, edge relaxations, operation counts) across algorithms.
- **Turn-by-Turn Navigation Itinerary**: Leg-by-leg directions with distance breakdowns.
- **Web Audio FX**: Synthesized audio feedback (step, edge relaxation, destination arrived) with mute toggle.

---

## 📐 Algorithm Complexity Comparison

| Algorithm | Time Complexity | Space Complexity | Optimality Guarantee | Best Use Case |
|---|---|---|---|---|
| **Dijkstra** | $O((V+E)\log V)$ | $O(V+E)$ | Exact (Non-negative) | Standard single-source routing |
| **A\* Search** | $O(E)$ to $O((V+E)\log V)$ | $O(V)$ | Exact (Admissible $h$) | Fast goal-directed navigation |
| **Bellman-Ford** | $O(V \cdot E)$ | $O(V)$ | Exact (Handles negative) | Edge relaxation & cycle checks |
| **BFS** | $O(V+E)$ | $O(V)$ | Hop-count minimal | Unweighted aisle hop routing |
| **Floyd-Warshall** | $O(V^3)$ | $O(V^2)$ | All-Pairs exact | Precomputing multi-stop distances |
| **Held-Karp (TSP)**| $O(n^2 2^n)$ | $O(n 2^n)$ | Exact order picking | Multi-stop shopping list routing |

---

## 🚀 Quick Start

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Launch the Web Application
```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```
- **Web Interface**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger Interactive API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📊 Offline Demonstrations & Benchmarks

### Standalone Network Visualizer
Generates a dark-themed floorplan topology map highlighting the optimal path:
```powershell
python main.py
```
*Output: `store_route.png`*

### Empirical Benchmark Suite
Runs empirical trials across varying graph sizes ($|V| \in [20, 180]$) and topologies (Sparse vs. Dense):
```powershell
python benchmark.py
```
*Output: `complexity_benchmark.png`*

---

## 📡 REST API Reference

- `GET /api/graph`: Returns current layout nodes, retail metadata, and aisles.
- `POST /api/route`: Computes shortest path with choice of `dijkstra`, `astar`, `bellman-ford`, or `bfs`, returning complete step traces and explanations.
- `POST /api/optimize-shopping-list`: Computes exact Held-Karp order picking sequence and stitches intermediate aisle paths.
- `POST /api/aisle/update`: Dynamic telemetry injection to update aisle weights.
- `POST /api/benchmark/live`: Evaluates all algorithms concurrently on the active graph.
- `POST /api/graph/preset`: Switch between `mega` (13 zones) and `classic` (6 zones) layouts.
- `POST /api/graph/reset`: Resets graph topology to default baseline.
- `GET /api/algorithms/info`: Educational theory, history, and complexity formulas.
