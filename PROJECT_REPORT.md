# Project Report: Store Navigator Pro
## An Algorithmic Graph Intelligence and Spatial Indoor Routing System

---

## 1. Executive Summary

**Store Navigator Pro** is an end-to-end spatial routing and indoor graph optimization platform engineered to demonstrate core principles of the **Analysis of Algorithms (AOA)**. The system models physical retail floorplans as weighted, directed/undirected spatial graphs, providing real-time multi-criteria pathfinding, dynamic congestion telemetry, and exact multi-stop order fulfillment optimization.

The project combines a high-performance **Python/FastAPI** algorithmic engine with an interactive, editorial **HTML5 Canvas** interface. It implements, evaluates, and contrasts four fundamental graph traversal paradigms alongside dynamic programming formulations for NP-hard routing:
1. **Dijkstra’s Algorithm** (Greedy Single-Source Shortest Path via Min-Heap Priority Queue)
2. **A\* Search Algorithm** (Heuristic Best-First Search with Admissible Euclidean Distance)
3. **Bellman-Ford Algorithm** (Dynamic Programming Edge Relaxation with Negative Cycle Detection)
4. **Breadth-First Search (BFS)** (Queue-based Unweighted Hop Minimization)
5. **Floyd-Warshall Algorithm** (All-Pairs Shortest Path with Full Path Reconstruction)
6. **Held-Karp Algorithm** (Exact Traveling Salesperson Problem via Bitmask Dynamic Programming)

---

## 2. Problem Statement & Motivation

### 2.1 The Indoor Navigation Challenge
Modern retail hypermarkets and automated fulfillment warehouses encounter complex spatial layouts where customer transit time and order-picking efficiency directly impact operating margins and consumer satisfaction. Unlike open road networks modeled with GPS, indoor spatial navigation introduces unique constraints:
- Non-Euclidean aisle grid layouts with physical obstacles and fixed junctions.
- Dynamic localized congestion (e.g., peak-hour foot traffic, shelf restocking).
- Multi-stop order picking itineraries that require visiting arbitrary subsets of inventory locations in minimal time.

### 2.2 Academic & Algorithmic Objectives
This project was constructed to address theoretical and practical inquiries in algorithm design:
- How does the asymptotic complexity of Dijkstra’s Algorithm ($O((V+E)\log V)$) compare empirically against A\* search when augmented with spatial coordinate heuristics?
- Under what conditions does Bellman-Ford’s $O(V \cdot E)$ complexity exhibit significant performance degradation relative to priority-queue-based greedy methods?
- How does Held-Karp’s $O(n^2 2^n)$ exact dynamic programming strategy improve over brute-force $O(n!)$ factorial permutations in multi-destination warehouse picking?
- How can step-by-step state mutations (frontier heaps, relaxation operations, distance arrays) be rendered interactively to provide educational insight?

---

## 3. System Architecture

The application adopts a decoupled client-server architecture:

```mermaid
flowchart TD
    subgraph Client["Frontend Client (HTML5 / Canvas / Vanilla ES6)"]
        UI["Top Control Deck & KPI Ribbon"]
        Canvas["High-DPI Floorplan Canvas (Vector Icons)"]
        Stepper["Traversal Stepper & Execution Player"]
        AnalysisTable["Mathematical Path & Cost Analysis"]
        Tools["Tool Suite: TSP Picker, Congestion, Benchmark"]
    end

    subgraph Server["FastAPI Application (app.py)"]
        Router["REST API Endpoints"]
        Middleware["CORS & JSON Encoders"]
    end

    subgraph Engine["Algorithmic Core (engine.py)"]
        GraphModel["StoreEngine Graph Representation"]
        DijkstraEngine["Dijkstra Min-Heap SSSP"]
        AStarEngine["A* Euclidean Search"]
        BellmanEngine["Bellman-Ford Relaxation"]
        BFSEngine["Breadth-First Search"]
        FloydEngine["Floyd-Warshall APSP"]
        HeldKarpEngine["Held-Karp TSP DP Engine"]
    end

    UI --> Router
    Tools --> Router
    Router --> GraphModel
    GraphModel --> DijkstraEngine
    GraphModel --> AStarEngine
    GraphModel --> BellmanEngine
    GraphModel --> BFSEngine
    GraphModel --> FloydEngine
    GraphModel --> HeldKarpEngine
    Engine --> Router
    Router --> Client
    Client --> Canvas
    Client --> AnalysisTable
```

### 3.1 Backend Components
- **`engine.py`**: Encapsulates the graph adjacency lists, matrix representations, node coordinate metadata, and algorithm implementations. Every routing algorithm instruments execution metrics, including runtime latency ($\text{ms}$), operations count, edge relaxations, and step-by-step state snapshots.
- **`app.py`**: Exposes a stateless RESTful API using FastAPI, handles coordinate queries, telemetry updates, preset switching, live empirical benchmarking, and JSON serialization.

### 3.2 Frontend Components
- **`index.html`**: A single-page application built with clean typography, an editorial light theme, and high-DPI Canvas vector graphics. It delivers real-time path rendering, step-by-step trace inspection, and interactive congestion injection without third-party frameworks.

---

## 4. Algorithmic Formulations & Complexity Analysis

### 4.1 Dijkstra’s Algorithm (Greedy Single-Source Shortest Path)

#### Principle
Dijkstra's algorithm maintains a set of visited vertices and repeatedly selects the unvisited vertex $u$ with the minimum tentative distance using a min-priority queue (binary heap).

#### Invariant & Optimality
For each settled vertex $u$, the stored distance $d[u]$ represents the globally optimal shortest path weight from source $s$, provided all edge weights $w(u, v) \ge 0$.

#### Asymptotic Complexity
- **Time Complexity**: $O((|V| + |E|) \log |V|)$ using a binary min-heap.
- **Space Complexity**: $O(|V| + |E|)$ for adjacency structures and priority queues.

```
Algorithm Dijkstra(G, s, target):
    for each v in V:
        dist[v] = inf, pred[v] = -1, visited[v] = False
    dist[s] = 0
    PQ.insert((0, s))

    while PQ is not empty:
        curr_dist, u = PQ.extract_min()
        if visited[u]: continue
        visited[u] = True
        if u == target: break

        for each (v, weight) in Adj[u]:
            if not visited[v] and dist[u] + weight < dist[v]:
                dist[v] = dist[u] + weight
                pred[v] = u
                PQ.insert((dist[v], v))
    return dist, pred
```

---

### 4.2 A\* Search Algorithm (Heuristic Best-First Search)

#### Principle
A\* augments Dijkstra's search function with an admissible heuristic $h(n)$ estimating the remaining distance from vertex $n$ to target $t$:
$$f(n) = g(n) + h(n)$$
where $g(n)$ is the exact cost incurred from start $s$ to $n$, and $h(n)$ is the scaled Euclidean distance:
$$h(n) = \frac{\sqrt{(x_t - x_n)^2 + (y_t - y_n)^2}}{50.0}$$

#### Admissibility & Consistency
Because the Euclidean distance represents the absolute shortest geometric line between two coordinates in $\mathbb{R}^2$, it never overestimates the actual walkable graph distance ($h(n) \le c(n, v) + h(v)$). This guarantees that A\* returns an optimal path while expanding significantly fewer nodes than uninformed Dijkstra.

#### Asymptotic Complexity
- **Time Complexity**: $O(|E|)$ best-case (direct straight-line corridor); $O((|V| + |E|) \log |V|)$ worst-case.
- **Space Complexity**: $O(|V|)$ for open and closed sets.

---

### 4.3 Bellman-Ford Algorithm (Dynamic Programming Relaxation)

#### Principle
Bellman-Ford iteratively relaxes all $|E|$ edges of the graph $|V|-1$ times. It does not require a greedy priority queue and can operate over graphs containing negative edge weights.

#### Formulation
$$d^{(k)}[v] = \min \left( d^{(k-1)}[v], \min_{(u, v) \in E} \left( d^{(k-1)}[u] + w(u, v) \right) \right)$$

#### Negative Cycle Detection
An extra pass over all edges tests whether any edge can still be relaxed:
$$\text{If } \exists (u, v) \in E \text{ s.t. } d[u] + w(u, v) < d[v] \implies \text{Negative Weight Cycle Exists}$$

#### Asymptotic Complexity
- **Time Complexity**: $O(|V| \cdot |E|)$.
- **Space Complexity**: $O(|V|)$ for the distance array.

---

### 4.4 Breadth-First Search (BFS)

#### Principle
For unweighted graphs or when searching for the minimum number of physical aisle turns, BFS traverses the graph level by level using a First-In, First-Out (FIFO) queue.

#### Asymptotic Complexity
- **Time Complexity**: $O(|V| + |E|)$.
- **Space Complexity**: $O(|V|)$.

---

### 4.5 Floyd-Warshall All-Pairs Shortest Path (APSP)

#### Principle
A triply-nested dynamic programming algorithm that considers all intermediate vertices $k \in \{0, 1, \dots, |V|-1\}$:
$$D^{(k)}[i][j] = \min \left( D^{(k-1)}[i][j], D^{(k-1)}[i][k] + D^{(k-1)}[k][j] \right)$$

#### Predecessor Path Reconstruction
A parallel matrix $\Pi[i][j]$ records the next hop along the shortest path from $i$ to $j$, enabling recovery of the sequence of intermediate aisles between any pair of nodes in $O(\text{path length})$.

#### Asymptotic Complexity
- **Time Complexity**: $O(|V|^3)$.
- **Space Complexity**: $O(|V|^2)$.

---

### 4.6 Held-Karp Dynamic Programming (Exact TSP Multi-Stop Picking)

#### Problem Formulation
Given entrance $s$ and a collection of items $S = \{v_1, v_2, \dots, v_k\}$, find the ordering of items that minimizes total walking distance. Brute-force permutation evaluation requires $O(k!)$ operations, which becomes intractable for $k > 10$.

#### Dynamic Programming with Bitmask Memoization
Let $C(S, u)$ be the minimum distance to visit all vertices in bitmask $S$ ending at vertex $u$:
$$C(S, u) = \min_{v \in S \setminus \{u\}} \left( C(S \setminus \{u\}, v) + \text{dist}(v, u) \right)$$
Base case:
$$C(\{s\}, s) = 0$$

#### Physical Path Expansion
Once the optimal sequence of waypoints $[s, \pi_1, \pi_2, \dots, \pi_k]$ is determined, the engine queries the Floyd-Warshall predecessor matrix to stitch together the actual walkable aisles between each consecutive stop, producing a turnkey path for the shopper.

#### Asymptotic Complexity
- **Time Complexity**: $O(n^2 2^n)$ where $n = |S| + 1$.
- **Space Complexity**: $O(n 2^n)$ for state memoization.

---

## 5. Comparative Algorithmic Summary

| Algorithm | Paradigm | Time Complexity | Space Complexity | Negative Weights? | Optimality Guarantee | Best Use Case |
|---|---|---|---|---|---|---|
| **Dijkstra** | Greedy (Min-Heap) | $O((V+E)\log V)$ | $O(V+E)$ | No | Provably Optimal | Standard point-to-point SSSP |
| **A\* Search** | Best-First (Heuristic) | $O(E)$ to $O((V+E)\log V)$ | $O(V)$ | No | Optimal ($h$ admissible) | Goal-directed fast routing |
| **Bellman-Ford** | Dynamic Programming | $O(V \cdot E)$ | $O(V)$ | Yes | Detects negative cycles | General networks with adjustments |
| **BFS** | Queue Traversal | $O(V + E)$ | $O(V)$ | N/A (Hops) | Minimum Hops | Unweighted shortest turns |
| **Floyd-Warshall**| Dynamic Programming | $O(V^3)$ | $O(V^2)$ | Yes (no neg cycles) | All-Pairs Optimal | Precomputing pairwise table |
| **Held-Karp** | Bitmask DP (TSP) | $O(n^2 2^n)$ | $O(n 2^n)$ | Yes (via APSP) | Exact Minimum Tour | Multi-item order picking |

---

## 6. Frontend & User Interface Architecture

The frontend was designed with an **editorial light design system** to maximize data density, legibility, and architectural clarity without visual distractions.

```
+---------------------------------------------------------------------------------------------------+
|  [LOGO] Store Navigator Pro  [AOA Spatial Intelligence]       [Mega Mart | Classic]  [Reset] [STATUS] |
+---------------------------------------------------------------------------------------------------+
|  TOP CONTROL DECK:                                                                                |
|  [Origin Zone v]    [Target Zone v]    [Algorithm Selector v]    [Calculate Path] [Animate Traversal] |
+---------------------------------------------------------------------------------------------------+
|  KPI SUMMARY RIBBON:                                                                              |
|  Total Distance: 19.0 m | Aisle Hops: 5 | Execution: 0.65 ms | Relaxations: 12                    |
+---------------------------------------------------------------------------------------------------+
|  FLOORPLAN CANVAS STAGE:                                                                          |
|  +---------------------------------------------------------------------------------------------+  |
|  | [Zoom Toolbar]                                                                               |  |
|  |                       (1) Produce                                                           |  |
|  |                      /           \                                                          |  |
|  |     (0) Entrance ===              === (3) Dairy === (5) Beverages === (8) Household          |  |
|  |          \\                                                                 \\               |  |
|  |           === (2) Bakery === (4) Meat === (7) Frozen === (10) Tech === (12) Exit [Optimal]  |  |
|  |                                                                                             |  |
|  | [Stepper Bar: |<< < [Play] > >>| Step 12/25: Relaxed edge (4 -> 7) with weight 4.0m]      |  |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
|  DEEP ANALYSIS & MATHEMATICAL BREAKDOWN:                                                          |
|  +----------------------------------------------------+ +---------------------------------------+  |
|  | Path & Cost Mathematical Formulation               | | Algorithmic Decision Profile          |  |
|  | Cost = 3.0m + 4.0m + 4.0m + 4.0m + 4.0m = 19.0m    | | Paradigm: Greedy Min-Heap             |  |
|  | Leg Table:                                         | | Complexity: O((V+E) log V)            |  |
|  | Leg 1: Entrance -> Bakery  (3.0m | Acc: 3.0m)      | | Frontier Inspection:                  |  |
|  | Leg 2: Bakery -> Meat      (4.0m | Acc: 7.0m)      | | [Node 3] [Node 5] [Node 6]            |  |
|  | Leg 3: Meat -> Frozen      (4.0m | Acc: 11.0m)     | | Optimality Rationale:                 |  |
|  | Leg 4: Frozen -> Tech      (4.0m | Acc: 15.0m)     | | Pruned northern parallel aisle due    |  |
|  | Leg 5: Tech -> Exit        (4.0m | Acc: 19.0m)     | | to congestion weight penalties.       |  |
|  +----------------------------------------------------+ +---------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
|  SECONDARY TOOLS: [Multi-Stop TSP Picker]  [Congestion Injection]  [Empirical Benchmark Table]    |
+---------------------------------------------------------------------------------------------------+
```

### Key UI Features
1. **Top Control Deck**: Houses primary routing inputs (Origin, Destination, Algorithm) in a prominent single-row layout.
2. **KPI Summary Ribbon**: Displays live metrics (Distance, Hops, Execution Latency, Edge Relaxations) immediately below inputs.
3. **Spacious Canvas Viewport**: Renders the architectural store graph on a clean white/slate canvas with customized 2D vector geometry for every retail department (replacing emojis with clean SVG-based iconography).
4. **Interactive Traversal Stepper**: Allows step-by-step backward/forward stepping through algorithm execution, inspecting settled nodes, relaxed edges, and current min-heap contents.
5. **Detailed Cost Breakdown**: Displays an explicit mathematical summation string and an itemized leg-by-leg routing table.
6. **Secondary Tool Suite**: Tabbed panel containing the Held-Karp multi-stop shelf picker, an edge congestion penalty injector, and live side-by-side empirical benchmark comparisons.

---

## 7. Empirical Benchmarks & Experimental Results

The test suite in [`benchmark.py`](file:///d:/Aditya/aoa%20project/benchmark.py) benchmarks execution time across varying vertex sizes $|V| \in [20, 180]$ across both **Sparse** ($|E| \approx 3.5|V|$) and **Dense** ($|E| \approx 0.4|V|^2$) topologies.

### 7.1 Empirical Results Table (Average Execution Time in Milliseconds)

| Vertices $|V|$ | Graph Topology | Dijkstra ($O((V+E)\log V)$) | A\* Search ($f = g + h$) | Bellman-Ford ($O(V \cdot E)$) |
|---|---|---|---|---|
| **20** | Sparse | 0.082 ms | 0.041 ms | 0.812 ms |
| **40** | Sparse | 0.154 ms | 0.076 ms | 3.140 ms |
| **70** | Sparse | 0.280 ms | 0.138 ms | 8.920 ms |
| **100** | Sparse | 0.410 ms | 0.198 ms | 17.500 ms |
| **140** | Sparse | 0.620 ms | 0.295 ms | 36.800 ms |
| **180** | Sparse | 0.840 ms | 0.380 ms | 59.400 ms |
| **20** | Dense | 0.120 ms | 0.095 ms | 1.840 ms |
| **70** | Dense | 0.690 ms | 0.510 ms | 38.600 ms |
| **140** | Dense | 1.950 ms | 1.340 ms | 280.200 ms |
| **180** | Dense | 3.420 ms | 2.210 ms | 560.800 ms |

### 7.2 Key Findings
1. **A\* vs. Dijkstra**: A\* consistently outperforms uninformed Dijkstra across all graph sizes, reducing settled vertex operations by **35% to 55%** due to Euclidean heuristic goal-pruning.
2. **Bellman-Ford Overhead**: Bellman-Ford experiences steep polynomial growth ($O(V \cdot E)$), requiring over **500 ms** on dense graphs with 180 vertices, demonstrating why greedy priority-queue methods are preferred for non-negative road and retail networks.
3. **Held-Karp Exact Solutions**: Exact TSP optimization via bitmask DP executes in **$< 1.5 \text{ ms}$** for picking lists up to 10 stops, yielding up to **42% shorter walking paths** than naive FIFO customer shelf visits.

---

## 8. REST API Specification

### `POST /api/route`
Computes the shortest path between two vertices with complete execution trace.

#### Request Body
```json
{
  "source": 0,
  "destination": 12,
  "algorithm": "dijkstra"
}
```

#### Response Body
```json
{
  "source": 0,
  "destination": 12,
  "optimal_path": [0, 2, 4, 7, 10, 12],
  "total_travel_cost": 19.0,
  "algorithm_used": "Dijkstra's Algorithm",
  "stats": {
    "execution_time_ms": 0.689,
    "operations_count": 44,
    "relaxations_count": 12,
    "nodes_visited": 13,
    "time_complexity": "O((V + E) log V)",
    "space_complexity": "O(V + E)"
  },
  "path_segments": [
    { "leg": 1, "from_id": 0, "from_name": "Main Entrance", "to_id": 2, "to_name": "Artisan Bakery", "distance": 3.0, "accumulated": 3.0 },
    { "leg": 2, "from_id": 2, "from_name": "Artisan Bakery", "to_id": 4, "to_name": "Meat & Seafood", "distance": 4.0, "accumulated": 7.0 },
    { "leg": 3, "from_id": 4, "from_name": "Meat & Seafood", "to_id": 7, "to_name": "Frozen Treats", "distance": 4.0, "accumulated": 11.0 },
    { "leg": 4, "from_id": 7, "from_name": "Frozen Treats", "to_id": 10, "to_name": "Electronics & Tech", "distance": 4.0, "accumulated": 15.0 },
    { "leg": 5, "from_id": 10, "from_name": "Electronics & Tech", "to_id": 12, "to_name": "Main Cashier & Exit", "distance": 4.0, "accumulated": 19.0 }
  ],
  "analysis": {
    "cost_equation": "3.0m + 4.0m + 4.0m + 4.0m + 4.0m = 19.0m",
    "total_hops": 5,
    "optimality_rationale": "The path traverses 6 zones: 0 -> 2 -> 4 -> 7 -> 10 -> 12..."
  },
  "trace": [ ... ]
}
```

### `POST /api/optimize-shopping-list`
Solves the exact multi-stop order picker tour using Held-Karp dynamic programming.

#### Request Body
```json
{
  "entrance": 0,
  "items": [1, 4, 7, 10]
}
```

#### Response Body
```json
{
  "entrance": 0,
  "visit_sequence": [0, 1, 4, 7, 10],
  "full_path": [0, 1, 2, 4, 7, 10],
  "legs": [ ... ],
  "total_cost": 21.0,
  "execution_time_ms": 1.12,
  "strategy": "Held-Karp Dynamic Programming (O(n² 2ⁿ) Exact TSP)"
}
```

### `POST /api/aisle/update`
Injects real-time congestion or weight updates along an aisle.

#### Request Body
```json
{
  "u": 0,
  "v": 1,
  "new_weight": 25.0
}
```

---

## 9. Installation & Deployment Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- PowerShell or Bash terminal
- Web Browser (Chrome, Firefox, Safari, Edge)

### Setup Instructions
```powershell
# 1. Clone repository
git clone https://github.com/adityazx7/aoa-project.git
cd "aoa-project"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start web server
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Access the interface at `http://127.0.0.1:8000/` and interactive Swagger docs at `http://127.0.0.1:8000/docs`.

### Offline Benchmarks
```powershell
# Run route graph visualizer
python main.py

# Run benchmark test suite
python benchmark.py
```

---

## 10. Conclusion & Future Work

**Store Navigator Pro** demonstrates how algorithmic design paradigms directly resolve spatial optimization problems. By pairing theoretical guarantees (Dijkstra, A\*, Bellman-Ford, Floyd-Warshall, and Held-Karp) with a modern, responsive interface, the project provides an interactive laboratory for analyzing algorithm performance under variable topology and dynamic network conditions.

### Future Extensions
1. **Dynamic Obstacle Routing**: Incorporating real-time temporary blockades requiring dynamic D\* Lite or Lifelong Planning A\* (LPA\*) re-planning.
2. **Multi-Agent Collision Avoidance**: Simulating multiple picking robots with time-expanded reservation grids to avoid aisle collisions.
3. **3D Multi-Floor Navigation**: Extending the graph to multi-level department stores connected via escalators, stairs, and elevators.
