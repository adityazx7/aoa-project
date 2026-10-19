from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import time
from engine import StoreEngine

app = FastAPI(
    title="Store Navigator Pro - Spatial Routing & Graph Engine",
    version="2.1.0",
    description="Analysis of Algorithms (AOA) Indoor Retail Pathfinding & Routing Intelligence API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global layout store
current_preset_name = "mega"
current_store: StoreEngine = StoreEngine(13)

def init_store_preset(preset: str = "mega") -> StoreEngine:
    global current_store, current_preset_name
    current_preset_name = preset

    if preset == "classic":
        st = StoreEngine(6)
        nodes = [
            (0, "Main Entrance", "Entry", "door-open", 120, 240),
            (1, "Fresh Produce", "Grocery", "apple", 320, 140),
            (2, "Artisan Bakery", "Bakery", "croissant", 300, 360),
            (3, "Dairy & Chilled", "Chilled", "milk", 540, 140),
            (4, "Beverages & Drinks", "Drinks", "cup-soda", 520, 360),
            (5, "Checkout & Exit", "Exit", "shopping-bag", 740, 250)
        ]
        for nid, name, cat, icon, x, y in nodes:
            st.set_node_metadata(nid, name, cat, icon, x, y)

        edges = [
            (0, 1, 4), (0, 2, 2), (1, 2, 1), (1, 3, 5),
            (2, 3, 8), (2, 4, 10), (3, 5, 6), (4, 5, 2)
        ]
        for u, v, w in edges:
            st.add_aisle(u, v, w)
        current_store = st
        return st

    # Default: "mega" layout (13 realistic retail zones)
    st = StoreEngine(13)
    nodes = [
        (0, "Main Entrance", "Entry", "door-open", 90, 330),
        (1, "Fresh Produce", "Grocery", "apple", 240, 150),
        (2, "Artisan Bakery", "Bakery", "croissant", 240, 510),
        (3, "Dairy & Eggs", "Chilled", "milk", 440, 150),
        (4, "Meat & Seafood", "Fresh", "beef", 440, 510),
        (5, "Beverages & Drinks", "Drinks", "cup-soda", 640, 150),
        (6, "Snacks & Pantry", "Grocery", "cookie", 640, 330),
        (7, "Frozen Treats", "Frozen", "ice-cream", 640, 510),
        (8, "Household & Cleaners", "Home", "sparkles", 840, 150),
        (9, "Pharmacy & Health", "Health", "pill", 840, 330),
        (10, "Electronics & Tech", "Tech", "laptop", 840, 510),
        (11, "Express Self-Checkout", "Checkout", "credit-card", 1020, 220),
        (12, "Main Cashier & Exit", "Exit", "shopping-bag", 1020, 440)
    ]
    for nid, name, cat, icon, x, y in nodes:
        st.set_node_metadata(nid, name, cat, icon, x, y)

    edges = [
        (0, 1, 4), (0, 2, 3),
        (1, 2, 5), (1, 3, 4),
        (2, 4, 4),
        (3, 4, 6), (3, 5, 4), (3, 6, 5),
        (4, 6, 5), (4, 7, 4),
        (5, 6, 3), (5, 8, 4),
        (6, 7, 3), (6, 9, 4),
        (7, 10, 4),
        (8, 9, 3), (8, 11, 4),
        (9, 10, 3), (9, 11, 3), (9, 12, 3),
        (10, 12, 4),
        (11, 12, 2)
    ]
    for u, v, w in edges:
        st.add_aisle(u, v, w)

    current_store = st
    return st

# Initialize store on startup
init_store_preset("mega")

# Request Models
class RouteRequest(BaseModel):
    source: int = Field(..., ge=0, description="Start node ID")
    destination: int = Field(..., ge=0, description="Target node ID")
    algorithm: str = Field("dijkstra", description="'dijkstra', 'astar', 'bellman-ford', or 'bfs'")

class DynamicWeightUpdate(BaseModel):
    u: int = Field(..., ge=0)
    v: int = Field(..., ge=0)
    new_weight: float = Field(..., ge=0.1, description="Congestion or adjusted aisle weight")

class ShoppingListRequest(BaseModel):
    entrance: int = Field(0, ge=0)
    items: List[int] = Field(..., min_length=1, description="List of shelf node IDs")

class PresetRequest(BaseModel):
    preset: str = Field("mega", description="'mega' or 'classic'")

class BenchmarkRequest(BaseModel):
    source: int = Field(0, ge=0)
    destination: int = Field(12, ge=0)

@app.get("/api/graph", status_code=status.HTTP_200_OK)
def get_graph():
    """Returns nodes, edges, and metadata for current layout."""
    node_list = []
    for nid in range(current_store.V):
        meta = current_store.node_metadata.get(nid, {
            "name": f"Node {nid}", "category": "General", "icon": "map-pin", "x": 100, "y": 100
        })
        node_list.append({
            "id": nid,
            **meta
        })

    edge_list = []
    seen = set()
    for u, v, w in current_store.edges:
        edge_key = tuple(sorted((u, v)))
        if edge_key not in seen:
            seen.add(edge_key)
            edge_list.append({
                "u": u,
                "v": v,
                "weight": w,
                "congested": w >= 12
            })

    return {
        "preset": current_preset_name,
        "total_nodes": current_store.V,
        "nodes": node_list,
        "edges": edge_list
    }

@app.post("/api/route", status_code=status.HTTP_200_OK)
def compute_route(payload: RouteRequest):
    """Computes shortest route using chosen algorithm and returns step trace & deep analysis."""
    if payload.source >= current_store.V or payload.destination >= current_store.V:
        raise HTTPException(status_code=400, detail="Invalid node index for current layout.")

    algo = payload.algorithm.lower().replace("_", "-")

    try:
        if algo in ("astar", "a-star", "a*"):
            dists, preds, trace, stats = current_store.astar(payload.source, payload.destination)
            algo_name = "A* Search Algorithm"
            paradigms = "Best-First Search + Admissible Euclidean Heuristic"
        elif algo == "bellman-ford":
            dists, preds, trace, stats = current_store.bellman_ford(payload.source)
            algo_name = "Bellman-Ford Algorithm"
            paradigms = "Dynamic Programming (Iterative Edge Relaxation)"
        elif algo == "bfs":
            dists, preds, trace, stats = current_store.bfs(payload.source, payload.destination)
            algo_name = "Breadth-First Search (BFS)"
            paradigms = "Queue-Based Unweighted Traversal (Min Hops)"
        else:
            dists, preds, trace, stats = current_store.dijkstra(payload.source, payload.destination)
            algo_name = "Dijkstra's Algorithm"
            paradigms = "Greedy Single-Source Shortest Path with Min-Heap"

        if dists[payload.destination] == float('inf'):
            raise HTTPException(status_code=404, detail="Destination unreachable from source.")

        # Reconstruct path
        path = []
        curr = payload.destination
        while curr != -1:
            path.append(curr)
            curr = preds[curr]
        path.reverse()

        # Detailed path segments & cost accumulation
        path_segments = []
        total_accumulated = 0.0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            w = next((w for sv, w in current_store.adj[u] if sv == v), 1.0)
            total_accumulated += w
            path_segments.append({
                "leg": i + 1,
                "from_id": u,
                "from_name": current_store.node_metadata.get(u, {}).get("name", f"Node {u}"),
                "to_id": v,
                "to_name": current_store.node_metadata.get(v, {}).get("name", f"Node {v}"),
                "distance": round(w, 2),
                "accumulated": round(total_accumulated, 2)
            })

        src_name = current_store.node_metadata.get(payload.source, {}).get("name", f"Node {payload.source}")
        dst_name = current_store.node_metadata.get(payload.destination, {}).get("name", f"Node {payload.destination}")

        # Deep analysis metrics
        cost_val = dists[payload.destination]
        cost_formula = " + ".join([f"{seg['distance']:.1f}m" for seg in path_segments])
        if not cost_formula:
            cost_formula = "0.0m"

        analysis = {
            "source_label": src_name,
            "target_label": dst_name,
            "total_hops": len(path) - 1,
            "total_distance": round(cost_val, 2),
            "cost_equation": f"{cost_formula} = {cost_val:.1f}m",
            "time_complexity": stats["time_complexity"],
            "space_complexity": stats["space_complexity"],
            "operations_count": stats["operations_count"],
            "relaxations_count": stats["relaxations_count"],
            "nodes_visited_count": stats["nodes_visited"],
            "optimality_rationale": (
                f"The path traverses {len(path)} zones: {' → '.join(str(p) for p in path)}. "
                f"At each junction, edges with greater weights or congestion penalties were rejected in favor of the minimum cumulative distance ({cost_val:.1f}m)."
            )
        }

        explanation = (
            f"### Algorithmic Execution Summary\n"
            f"- **Algorithm**: {algo_name} ({paradigms})\n"
            f"- **Route**: {src_name} → {dst_name} across **{len(path) - 1} aisle hops**.\n"
            f"- **Total Distance / Cost**: **{cost_val:.1f} meters** (`{cost_formula}`)\n"
            f"- **Execution Metrics**: Completed in **{stats['execution_time_ms']} ms** with **{stats['operations_count']} operations** and **{stats['relaxations_count']} edge relaxations**.\n\n"
            f"**Optimality Guarantee**: {analysis['optimality_rationale']}"
        )

        return {
            "source": payload.source,
            "destination": payload.destination,
            "optimal_path": path,
            "path": path,
            "total_travel_cost": cost_val,
            "total_cost": cost_val,
            "algorithm_used": algo_name,
            "stats": stats,
            "path_segments": path_segments,
            "analysis": analysis,
            "trace": trace,
            "explanation": explanation
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/optimize-shopping-list", status_code=status.HTTP_200_OK)
def optimize_shopping_list(payload: ShoppingListRequest):
    """Held-Karp Exact TSP Order Picking route planner."""
    result = current_store.optimize_shopping_list_dp(payload.entrance, payload.items)

    visit_names = [current_store.node_metadata.get(s, {}).get('name', f'Node {s}') for s in result['visit_sequence']]
    explanation = (
        f"### Multi-Stop Order Picking Analysis\n"
        f"- **Algorithm Strategy**: Held-Karp Dynamic Programming (Exact TSP formulation)\n"
        f"- **Stops Visited**: {len(result['visit_sequence'])} destinations ({' → '.join(visit_names)})\n"
        f"- **Total Distance**: **{result['total_cost']:.1f} meters** across **{len(result['full_path']) - 1} aisle steps**\n"
        f"- **Computational Complexity**: $O(n^2 2^n)$ solved in **{result['execution_time_ms']} ms** via bitmask state memoization.\n\n"
        f"**Efficiency Impact**: Compared to walking shelves in arbitrary order, dynamic programming guarantees the mathematical minimum walking distance, reducing warehouse/shopper retrieval fatigue."
    )

    return {
        **result,
        "optimized_itinerary": result["visit_sequence"],
        "route": result["full_path"],
        "explanation": explanation
    }

@app.post("/api/aisle/update", status_code=status.HTTP_200_OK)
def update_aisle(payload: DynamicWeightUpdate):
    if payload.u >= current_store.V or payload.v >= current_store.V:
        raise HTTPException(status_code=400, detail="Invalid node coordinates.")

    current_store.update_aisle(payload.u, payload.v, payload.new_weight)
    return {
        "status": "success",
        "u": payload.u,
        "v": payload.v,
        "new_weight": payload.new_weight,
        "message": f"Aisle ({payload.u} ↔ {payload.v}) weight successfully updated to {payload.new_weight}m."
    }

@app.post("/api/graph/preset", status_code=status.HTTP_200_OK)
def set_graph_preset(payload: PresetRequest):
    init_store_preset(payload.preset)
    return get_graph()

@app.post("/api/graph/reset", status_code=status.HTTP_200_OK)
def reset_graph():
    init_store_preset(current_preset_name)
    return {"message": "Graph reset to default baseline topology."}

@app.post("/api/benchmark/live", status_code=status.HTTP_200_OK)
def benchmark_algorithms(payload: BenchmarkRequest):
    """Runs Dijkstra, A*, Bellman-Ford, and BFS on current layout to compare live metrics."""
    s = payload.source
    d = payload.destination
    if s >= current_store.V or d >= current_store.V:
        raise HTTPException(status_code=400, detail="Node index out of bounds.")

    results = []

    # Dijkstra
    dists_d, preds_d, _, stats_d = current_store.dijkstra(s, d)
    results.append({
        "algorithm": "Dijkstra's Algorithm",
        "time_ms": stats_d["execution_time_ms"],
        "operations": stats_d["operations_count"],
        "relaxations": stats_d["relaxations_count"],
        "cost": dists_d[d] if dists_d[d] != float('inf') else None,
        "time_complexity": "O((V + E) log V)",
        "space_complexity": "O(V + E)",
        "optimal": True
    })

    # A*
    dists_a, preds_a, _, stats_a = current_store.astar(s, d)
    results.append({
        "algorithm": "A* Search Algorithm",
        "time_ms": stats_a["execution_time_ms"],
        "operations": stats_a["operations_count"],
        "relaxations": stats_a["relaxations_count"],
        "cost": dists_a[d] if dists_a[d] != float('inf') else None,
        "time_complexity": "O(E) to O((V+E)logV)",
        "space_complexity": "O(V)",
        "optimal": True
    })

    # Bellman-Ford
    dists_b, preds_b, _, stats_b = current_store.bellman_ford(s)
    results.append({
        "algorithm": "Bellman-Ford",
        "time_ms": stats_b["execution_time_ms"],
        "operations": stats_b["operations_count"],
        "relaxations": stats_b["relaxations_count"],
        "cost": dists_b[d] if dists_b[d] != float('inf') else None,
        "time_complexity": "O(V · E)",
        "space_complexity": "O(V)",
        "optimal": True
    })

    # BFS
    dists_bfs, preds_bfs, _, stats_bfs = current_store.bfs(s, d)
    results.append({
        "algorithm": "Breadth-First Search (BFS)",
        "time_ms": stats_bfs["execution_time_ms"],
        "operations": stats_bfs["operations_count"],
        "relaxations": stats_bfs["relaxations_count"],
        "cost": dists_bfs[d] if dists_bfs[d] != float('inf') else None,
        "time_complexity": "O(V + E)",
        "space_complexity": "O(V)",
        "optimal": False
    })

    return {
        "source": s,
        "destination": d,
        "benchmark_data": results
    }

@app.get("/api/algorithms/info", status_code=status.HTTP_200_OK)
def get_algorithms_info():
    """Educational metadata and theoretical reference for all routing algorithms."""
    return [
        {
            "id": "dijkstra",
            "name": "Dijkstra's Algorithm",
            "inventor": "Edsger W. Dijkstra (1956)",
            "paradigm": "Greedy Approach with Min-Priority Queue",
            "time_complexity": "O((|V| + |E|) \\log |V|)",
            "space_complexity": "O(|V| + |E|)",
            "description": "Computes single-source shortest paths in graphs with non-negative edge weights.",
            "pros": ["Provably optimal for non-negative weights", "Fast with binary heap"],
            "cons": ["Cannot handle negative edge weights"]
        },
        {
            "id": "astar",
            "name": "A* Search Algorithm",
            "inventor": "Peter Hart, Nils Nilsson, Bertram Raphael (1968)",
            "paradigm": "Best-First Search + Admissible Heuristic",
            "time_complexity": "O(|E|) best case, O((|V| + |E|) \\log |V|) worst case",
            "space_complexity": "O(|V|)",
            "description": "Guided pathfinding evaluating f(n) = g(n) + h(n).",
            "pros": ["Goal-directed exploration saves operations", "Provably optimal when heuristic is admissible"],
            "cons": ["Requires spatial coordinate heuristic"]
        },
        {
            "id": "bellman-ford",
            "name": "Bellman-Ford Algorithm",
            "inventor": "Richard Bellman & Lester Ford Jr. (1958)",
            "paradigm": "Dynamic Programming (Edge Relaxation)",
            "time_complexity": "O(|V| \\cdot |E|)",
            "space_complexity": "O(|V|)",
            "description": "Iteratively relaxes all edges |V|-1 times with cycle detection.",
            "pros": ["Handles negative edge weights", "Detects negative cycles reliably"],
            "cons": ["Slower than Dijkstra on positive weights"]
        },
        {
            "id": "held-karp",
            "name": "Held-Karp Dynamic Programming (TSP)",
            "inventor": "Michael Held & Richard M. Karp (1962)",
            "paradigm": "Dynamic Programming with Bitmask State",
            "time_complexity": "O(n^2 2^n)",
            "space_complexity": "O(n 2^n)",
            "description": "Finds exact optimal itinerary visiting multiple stops.",
            "pros": ["Guarantees absolute global minimum total walking distance"],
            "cons": ["Exponential time complexity"]
        }
    ]

@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")
