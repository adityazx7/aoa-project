from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import time
from starlette.concurrency import run_in_threadpool

from engine import StoreEngine
from campus_navigation.models import CampusGraphData, CampusNode, CampusEdge, CampusRoom, CostModel
from campus_navigation.algorithms import CampusRouter, RoutingOptions, RouteResult

app = FastAPI(
    title="Spatial Navigator - Spatial Routing & Graph Engine",
    version="2.3.0",
    description="Analysis of Algorithms (AOA) Campus & Retail Pathfinding Engine (featuring Vidyalankar College System)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Global layout store
current_preset_name = "vidyalankar"
current_store: StoreEngine = StoreEngine(36)

def init_store_preset(preset: str = "vidyalankar") -> StoreEngine:
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
            (0, 1, 4.0, "pathway", 1.0, "Entrance to Produce"),
            (0, 2, 2.0, "pathway", 1.0, "Entrance to Bakery"),
            (1, 2, 1.0, "pathway", 1.0, "Produce to Bakery Aisle"),
            (1, 3, 5.0, "pathway", 1.0, "Produce to Dairy"),
            (2, 3, 8.0, "pathway", 1.0, "Bakery to Dairy Central"),
            (2, 4, 10.0, "pathway", 1.0, "Bakery to Beverages"),
            (3, 5, 6.0, "pathway", 1.0, "Dairy to Checkout"),
            (4, 5, 2.0, "pathway", 1.0, "Beverages to Checkout")
        ]
        for u, v, w, et, mult, lbl in edges:
            st.add_aisle(u, v, w, bidirectional=True, edge_type=et, multiplier=mult, label=lbl)
        current_store = st
        return st

    elif preset == "mega":
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
            (0, 1, 4.0, "pathway", 1.0, "Entrance to Produce"),
            (0, 2, 3.0, "pathway", 1.0, "Entrance to Bakery"),
            (1, 2, 5.0, "pathway", 1.0, "Produce to Bakery Aisle"),
            (1, 3, 4.0, "pathway", 1.0, "Produce to Dairy"),
            (2, 4, 4.0, "pathway", 1.0, "Bakery to Meat"),
            (3, 4, 6.0, "pathway", 1.0, "Dairy to Meat"),
            (3, 5, 4.0, "pathway", 1.0, "Dairy to Beverages"),
            (3, 6, 5.0, "pathway", 1.0, "Dairy to Snacks"),
            (4, 6, 5.0, "pathway", 1.0, "Meat to Snacks"),
            (4, 7, 4.0, "pathway", 1.0, "Meat to Frozen"),
            (5, 6, 3.0, "pathway", 1.0, "Beverages to Snacks"),
            (5, 8, 4.0, "pathway", 1.0, "Beverages to Household"),
            (6, 7, 3.0, "pathway", 1.0, "Snacks to Frozen"),
            (6, 9, 4.0, "pathway", 1.0, "Snacks to Pharmacy"),
            (7, 10, 4.0, "pathway", 1.0, "Frozen to Tech"),
            (8, 9, 3.0, "pathway", 1.0, "Household to Pharmacy"),
            (8, 11, 4.0, "pathway", 1.0, "Household to Express Checkout"),
            (9, 10, 3.0, "pathway", 1.0, "Pharmacy to Tech"),
            (9, 11, 3.0, "pathway", 1.0, "Pharmacy to Express Checkout"),
            (9, 12, 3.0, "pathway", 1.0, "Pharmacy to Exit"),
            (10, 12, 4.0, "pathway", 1.0, "Tech to Exit"),
            (11, 12, 2.0, "pathway", 1.0, "Express Checkout to Exit")
        ]
        for u, v, w, et, mult, lbl in edges:
            st.add_aisle(u, v, w, bidirectional=True, edge_type=et, multiplier=mult, label=lbl)
        current_store = st
        return st

    # Featured Blueprint Preset: "vidyalankar" (36 Nodes, 3 Tiers, Multi-level stairs & bridges)
    st = StoreEngine(36)
    nodes = [
        # Panel 1: Campus Grounds & Main Avenue (Top)
        (0, "Football Ground", "Outdoor Sports", "trophy", 140, 80),
        (1, "Y-Block (GND)", "Academic Block", "building", 320, 60),
        (2, "DEN Block", "Academic Block", "building", 460, 60),
        (3, "CLD Gate (N1)", "Campus Gate", "door-open", 620, 80),
        (4, "Main Ground", "Outdoor Campus", "map-pin", 820, 80),
        (5, "Parking & Courts", "Sports & Parking", "car", 1240, 80),
        (6, "West Avenue", "Campus Avenue", "compass", 120, 170),
        (7, "M-Block North", "Avenue Hub", "compass", 320, 170),
        (8, "Central Ave (N2)", "Main Avenue Hub", "compass", 620, 170),
        (9, "East Ave (N5)", "Avenue Hub", "compass", 920, 170),
        (10, "East Ave End", "Avenue Hub", "compass", 1180, 170),
        (11, "VP Block", "Academic Block", "building", 920, 250),

        # Panel 2: M-Block Ground Floor & Lab Corridor (Middle)
        (12, "M-Block Entry", "M-Block Entry", "door-open", 320, 250),
        (13, "Innovation Lab", "M-Block Labs", "laptop", 200, 390),
        (14, "Canteen Basement", "Amenities", "coffee", 120, 500),
        (15, "West Stairs", "Vertical Stairs", "stairs", 280, 500),
        (16, "Corridor N1", "Lab Corridor", "navigation", 440, 500),
        (17, "Computer Labs", "Laboratories", "monitor", 440, 390),
        (18, "Central Corridor", "Lab Corridor", "navigation", 680, 500),
        (19, "Electronics Labs", "Laboratories", "cpu", 680, 390),
        (20, "East Corridor", "Lab Corridor", "navigation", 920, 500),
        (21, "Research Labs", "Laboratories", "microscope", 920, 390),
        (22, "East Stairs", "Vertical Stairs", "stairs", 1200, 500),

        # Panel 3: VIT Academic Block & Skybridges (Bottom)
        (23, "VIT Entry (N3)", "VIT Campus Core", "door-open", 540, 580),
        (24, "Annex Stairs", "Vertical Stairs", "stairs", 120, 710),
        (25, "West Hub (N3)", "VIT Walkways", "navigation", 280, 740),
        (26, "E-Block", "Academic Block", "book-open", 400, 660),
        (27, "Bridge N1", "Elevated Bridge", "bridge", 540, 660),
        (28, "F-Block", "Academic Block", "book-open", 680, 660),
        (29, "Central Bridge N2", "Elevated Bridge", "bridge", 780, 740),
        (30, "VIT Library", "Academic Core", "library", 980, 660),
        (31, "East Bridge N2", "Elevated Bridge", "bridge", 1140, 740),
        (32, "A-Block", "Academic Block", "building", 1140, 830),
        (33, "B-Block", "Academic Block", "building", 980, 830),
        (34, "D-Block", "Academic Block", "building", 400, 830),
        (35, "Nescafe & Canteen", "Amenities", "coffee", 680, 830)
    ]
    for nid, name, cat, icon, x, y in nodes:
        st.set_node_metadata(nid, name, cat, icon, x, y)

    edges = [
        # Top Tier: Outdoor Campus & Roadways
        (6, 7, 30.0, "pathway", 1.0, "West Avenue (30m)"),
        (7, 8, 45.0, "pathway", 1.0, "Main Avenue West (45m)"),
        (7, 12, 35.0, "pathway", 1.0, "M-Block North Approach (35m)"),
        (8, 9, 35.0, "pathway", 1.0, "Main Avenue East (35m)"),
        (9, 10, 40.0, "pathway", 1.0, "East Avenue Pathway (40m)"),
        (10, 5, 20.0, "pathway", 1.0, "Parking Approach (20m)"),
        (9, 11, 15.0, "pathway", 1.0, "VP Block Entrance (15m)"),
        (8, 23, 15.0, "pathway", 1.0, "VIT Main Entrance Walkway (15m)"),
        (8, 3, 22.5, "pathway", 1.5, "Avenue to Y-Block Gate (15m, c=1.5)"),
        (3, 2, 15.0, "pathway", 1.0, "CLD to DEN Pathway (15m)"),
        (2, 1, 45.0, "pathway", 1.0, "DEN to GND Pathway (45m)"),
        (1, 0, 30.0, "pathway", 1.0, "GND to Football Ground (30m)"),
        (2, 4, 25.0, "pathway", 1.0, "DEN to Main Ground (25m)"),
        (12, 7, 52.5, "stairs", 1.5, "M-Block N6 Ramp/Stairs (35m, c=1.5)"),

        # Middle Tier: M-Block Labs & Corridors
        (12, 13, 25.0, "pathway", 1.0, "M-Block Entry to Innovation Lab"),
        (13, 14, 20.0, "pathway", 1.0, "Innovation Lab to Canteen Basement"),
        (13, 15, 22.5, "stairs", 1.5, "Innovation Lab to 1st Floor Stairs (15m, c=1.5)"),
        (14, 15, 18.0, "stairs", 1.5, "Canteen to Upper Floor Stairs (12m, c=1.5)"),
        (15, 16, 35.0, "pathway", 1.0, "Stairs to Corridor Junction N1 (35m)"),
        (16, 17, 15.0, "pathway", 1.0, "Hallway to Computer Labs (15m)"),
        (16, 18, 30.0, "pathway", 1.0, "Corridor N1 to Central N2 (30m)"),
        (18, 19, 45.0, "pathway", 1.0, "Central Hallway to Electronics Labs (45m)"),
        (18, 20, 45.0, "pathway", 1.0, "Corridor N2 to East Wing (45m)"),
        (20, 21, 45.0, "pathway", 1.0, "East Hallway to Research Labs (45m)"),
        (20, 22, 90.0, "stairs", 2.0, "Corridor to East Vertical Stairs (45m, c=2.0)"),

        # Inter-Floor Vertical Connectors (M-Block to VIT Upper Floor)
        (15, 24, 50.0, "stairs", 2.0, "West Stairs to VIT Canteen Annex (25m, c=2.0)"),
        (22, 31, 60.0, "stairs", 2.0, "East Stairs to Bridge N2 (30m, c=2.0)"), # blue arrow in blueprint

        # Bottom Tier: VIT Academic Block View
        (23, 27, 25.0, "pathway", 1.0, "VIT Entrance to Bridge N1 (25m)"),
        (24, 25, 45.0, "stairs", 1.5, "Stairs to Canteen Annex to N3 (30m, c=1.5)"),
        (25, 26, 30.0, "pathway", 1.0, "Junction N3 to E-Block (30m)"),
        (26, 27, 20.0, "bridge", 1.0, "Bridge N1: E-Block to F-Block (20m)"),
        (27, 28, 25.0, "bridge", 1.0, "Bridge N1: Connector to F-Block (25m)"),
        (27, 29, 45.0, "pathway", 1.0, "Bridge N1 to Central Bridge N2 (45m)"),
        (29, 30, 30.0, "bridge", 1.0, "Bridge N2: Central Skybridge to Library (30m)"),
        (30, 31, 25.0, "bridge", 1.0, "East Bridge N2: Library to East Wing (25m)"),
        (31, 32, 20.0, "pathway", 1.0, "East Bridge to A-Block (20m)"),
        (30, 33, 30.0, "stairs", 2.0, "Stairs from Library down to B-Block (15m, c=2.0)"),
        (25, 34, 35.0, "pathway", 1.0, "Junction N3 to D-Block (35m)"),
        (34, 35, 25.0, "bridge", 1.0, "Bridge: D-Block to Nescafe & Canteen (25m)"),
        (35, 33, 20.0, "pathway", 1.0, "Nescafe to B-Block Walkway (20m)"),
        (33, 32, 25.0, "pathway", 1.0, "B-Block to A-Block Walkway (25m)")
    ]
    for u, v, w, et, mult, lbl in edges:
        st.add_aisle(u, v, w, bidirectional=True, edge_type=et, multiplier=mult, label=lbl)

    current_store = st
    return st

# Initialize store on startup with the featured Vidyalankar campus system
init_store_preset("vidyalankar")

# Request Models
class RouteRequest(BaseModel):
    source: int = Field(..., ge=0, description="Start node ID")
    destination: int = Field(..., ge=0, description="Target node ID")
    algorithm: str = Field("dijkstra", description="'dijkstra', 'astar', 'bellman-ford', or 'bfs'")

class DynamicWeightUpdate(BaseModel):
    u: int = Field(..., ge=0)
    v: int = Field(..., ge=0)
    new_weight: float = Field(..., ge=0.1, description="Congestion or adjusted weight")

class ShoppingListRequest(BaseModel):
    entrance: int = Field(0, ge=0)
    items: List[int] = Field(..., min_length=1, description="List of node IDs to visit")

class PresetRequest(BaseModel):
    preset: str = Field("vidyalankar", description="'vidyalankar', 'mega', or 'classic'")

class BenchmarkRequest(BaseModel):
    source: int = Field(0, ge=0)
    destination: int = Field(30, ge=0)

@app.get("/api/graph", status_code=status.HTTP_200_OK)
def get_graph():
    """Returns nodes, edges, and rich metadata for current layout."""
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
            attr = current_store.edge_attributes.get((u, v), {})
            edge_list.append({
                "u": u,
                "v": v,
                "weight": w,
                "congested": w >= 40.0,
                "edge_type": attr.get("type", "pathway"),
                "multiplier": attr.get("multiplier", 1.0),
                "base_distance": attr.get("base_distance", w),
                "label": attr.get("label", f"Aisle {u}-{v}")
            })

    return {
        "preset": current_preset_name,
        "total_nodes": current_store.V,
        "nodes": node_list,
        "edges": edge_list
    }

@app.post("/api/route", status_code=status.HTTP_200_OK)
def compute_route(payload: RouteRequest):
    """Computes shortest route using chosen algorithm and returns step trace, natural language guidance, and deep analysis."""
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
        step_by_step_guidance = []
        total_accumulated = 0.0
        total_base_meters = 0.0
        stairs_count = 0
        bridges_count = 0

        src_name = current_store.node_metadata.get(payload.source, {}).get("name", f"Node {payload.source}")
        dst_name = current_store.node_metadata.get(payload.destination, {}).get("name", f"Node {payload.destination}")

        step_by_step_guidance.append({
            "step": 1,
            "action": "start",
            "icon": "flag",
            "instruction": f"Start at {src_name}."
        })

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            w = next((w for sv, w in current_store.adj[u] if sv == v), 1.0)
            attr = current_store.edge_attributes.get((u, v), {})
            edge_type = attr.get("type", "pathway")
            mult = attr.get("multiplier", 1.0)
            base_d = attr.get("base_distance", w)
            lbl = attr.get("label", "")

            total_accumulated += w
            total_base_meters += base_d

            u_name = current_store.node_metadata.get(u, {}).get("name", f"Node {u}")
            v_name = current_store.node_metadata.get(v, {}).get("name", f"Node {v}")

            if edge_type == "stairs":
                stairs_count += 1
                instruction = f"Take stairs from {u_name} to {v_name} (climb {base_d:.1f}m, vertical effort penalty {mult:.1f}x -> weighted cost: {w:.1f}m)."
                action_type = "climb"
                icon_type = "stairs"
            elif edge_type == "bridge":
                bridges_count += 1
                instruction = f"Cross elevated skybridge from {u_name} to {v_name} ({base_d:.1f}m bridge connectivity)."
                action_type = "bridge"
                icon_type = "bridge"
            else:
                instruction = f"Walk along pathway from {u_name} to {v_name} (distance: {base_d:.1f}m)."
                action_type = "walk"
                icon_type = "navigation"

            step_by_step_guidance.append({
                "step": i + 2,
                "action": action_type,
                "icon": icon_type,
                "from_name": u_name,
                "to_name": v_name,
                "edge_type": edge_type,
                "distance": round(base_d, 1),
                "weighted_cost": round(w, 1),
                "instruction": instruction
            })

            path_segments.append({
                "leg": i + 1,
                "from_id": u,
                "from_name": u_name,
                "to_id": v,
                "to_name": v_name,
                "edge_type": edge_type,
                "multiplier": mult,
                "distance": round(w, 2),
                "base_distance": round(base_d, 2),
                "accumulated": round(total_accumulated, 2),
                "label": lbl
            })

        step_by_step_guidance.append({
            "step": len(path) + 1,
            "action": "arrive",
            "icon": "map-pin",
            "instruction": f"Arrive at destination: {dst_name}."
        })

        # Generate "Go from here to there, then from there to..." natural language chain text
        chain_hops = [current_store.node_metadata.get(p, {}).get("name", f"Node {p}") for p in path]
        if len(chain_hops) == 1:
            natural_language_chain = f"Already at destination: {dst_name}."
        elif len(chain_hops) == 2:
            natural_language_chain = f"Go directly from {chain_hops[0]} to {chain_hops[1]}."
        else:
            chain_parts = [f"Go from {chain_hops[0]} to {chain_hops[1]}"]
            for hop in chain_hops[2:]:
                chain_parts.append(f"then go to {hop}")
            natural_language_chain = ", ".join(chain_parts) + "."

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
            "total_base_meters": round(total_base_meters, 2),
            "stairs_count": stairs_count,
            "bridges_count": bridges_count,
            "cost_equation": f"{cost_formula} = {cost_val:.1f}m",
            "time_complexity": stats["time_complexity"],
            "space_complexity": stats["space_complexity"],
            "operations_count": stats["operations_count"],
            "relaxations_count": stats["relaxations_count"],
            "nodes_visited_count": stats["nodes_visited"],
            "natural_language_chain": natural_language_chain,
            "step_by_step_guidance": step_by_step_guidance,
            "optimality_rationale": (
                f"The algorithm evaluated paths across {len(path)} waypoints ({' → '.join(str(p) for p in path)}). "
                f"Path balances vertical stairs climbing penalties (count: {stairs_count}) with elevated bridges (count: {bridges_count}) "
                f"to achieve the mathematical minimum travel cost ({cost_val:.1f}m)."
            )
        }

        explanation = (
            f"### Algorithmic Execution Summary\n"
            f"- **Algorithm**: {algo_name} ({paradigms})\n"
            f"- **Route**: {src_name} → {dst_name} across **{len(path) - 1} hops** (**{total_base_meters:.1f}m physical meters**, weighted cost **{cost_val:.1f}m**).\n"
            f"- **Vertical Transitions**: **{stairs_count} staircases** climbed | **{bridges_count} elevated skybridges** crossed.\n"
            f"- **Execution Metrics**: Completed in **{stats['execution_time_ms']} ms** with **{stats['operations_count']} operations** and **{stats['relaxations_count']} edge relaxations**.\n\n"
            f"**Turn-by-Turn Guidance**: {natural_language_chain}"
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
        f"### Multi-Destination Route Optimization\n"
        f"- **Algorithm Strategy**: Held-Karp Dynamic Programming (Exact TSP formulation)\n"
        f"- **Waypoints Visited**: {len(result['visit_sequence'])} destinations ({' → '.join(visit_names)})\n"
        f"- **Total Distance / Weighted Cost**: **{result['total_cost']:.1f} meters** across **{len(result['full_path']) - 1} steps**\n"
        f"- **Computational Complexity**: $O(n^2 2^n)$ solved in **{result['execution_time_ms']} ms** via bitmask state memoization.\n\n"
        f"**Efficiency Impact**: Compared to walking stops in arbitrary order, dynamic programming guarantees the mathematical minimum walking distance."
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
        "message": f"Connection ({payload.u} ↔ {payload.v}) weight successfully updated to {payload.new_weight}m."
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

# =====================================================================
# CAMPUS INDOOR / OUTDOOR NAVIGATION ENGINE (VIT BLUEPRINT)
# =====================================================================

campus_graph_instance = CampusGraphData.load_from_file("campus-graph.json")
campus_router_instance = CampusRouter(campus_graph_instance)

class CampusRouteRequest(BaseModel):
    source: str = Field(..., description="Start node ID")
    destination: str = Field(..., description="Target node ID")
    algorithm: str = Field("dijkstra", description="'dijkstra', 'astar', 'bfs', or 'bidirectional'")
    avoid_stairs: bool = Field(False)
    stairs_penalty: float = Field(4.0, ge=1.0)
    accessible_only: bool = Field(False)
    prefer_indoor: bool = Field(False)
    outdoor_penalty: float = Field(2.5, ge=1.0)
    k_alternatives: int = Field(1, ge=1, le=5)

class CampusMultiStopRequest(BaseModel):
    origin: str = Field(..., description="Start node ID")
    stops: List[str] = Field(..., min_length=1, description="List of stop node IDs")
    avoid_stairs: bool = Field(False)
    stairs_penalty: float = Field(4.0, ge=1.0)
    accessible_only: bool = Field(False)
    prefer_indoor: bool = Field(False)
    outdoor_penalty: float = Field(2.5, ge=1.0)

@app.get("/api/campus/graph", status_code=status.HTTP_200_OK)
async def get_campus_graph():
    """Returns validated nodes, edges with precomputed costs, rooms, and cost model."""
    return campus_graph_instance.model_dump(by_alias=True)

@app.post("/api/campus/route", status_code=status.HTTP_200_OK)
async def compute_campus_route(payload: CampusRouteRequest):
    """Computes optimal campus route in background thread with comparison benchmarks and alternatives."""
    if payload.source not in campus_router_instance.nodes_map:
        raise HTTPException(status_code=400, detail=f"Source node '{payload.source}' not found.")
    if payload.destination not in campus_router_instance.nodes_map:
        raise HTTPException(status_code=400, detail=f"Destination node '{payload.destination}' not found.")

    opt = RoutingOptions(
        avoid_stairs=payload.avoid_stairs,
        stairs_penalty=payload.stairs_penalty,
        accessible_only=payload.accessible_only,
        prefer_indoor=payload.prefer_indoor,
        outdoor_penalty=payload.outdoor_penalty
    )

    algo = payload.algorithm.lower().replace("-", "").replace("_", "")

    def _run_search():
        if algo in ("astar", "a*"):
            primary = campus_router_instance.astar(payload.source, payload.destination, opt)
        elif algo == "alt":
            primary = campus_router_instance.alt(payload.source, payload.destination, opt)
        elif algo == "bfs":
            primary = campus_router_instance.bfs(payload.source, payload.destination, opt)
        elif algo in ("bidirectional", "bidi", "bidirectionaldijkstra"):
            primary = campus_router_instance.bidirectional_dijkstra(payload.source, payload.destination, opt)
        else:
            primary = campus_router_instance.dijkstra(payload.source, payload.destination, opt)

        # Comparative benchmark across algorithms
        r_dijk = campus_router_instance.dijkstra(payload.source, payload.destination, opt)
        r_astar = campus_router_instance.astar(payload.source, payload.destination, opt)
        r_alt = campus_router_instance.alt(payload.source, payload.destination, opt)
        r_bidi = campus_router_instance.bidirectional_dijkstra(payload.source, payload.destination, opt)
        r_bfs = campus_router_instance.bfs(payload.source, payload.destination, opt)

        comparison = []
        for name, r, compl in [
            ("Dijkstra (Binary Heap)", r_dijk, "O((V + E) log V)"),
            ("A* (Admissible Euclidean)", r_astar, "O(E) to O((V + E) log V)"),
            ("ALT (Landmarks + Triangle Ineq)", r_alt, "O((V + E) log V)"),
            ("Bidirectional Dijkstra", r_bidi, "2 x O((V + E) log V)"),
            ("Breadth-First Search (BFS)", r_bfs, "O(V + E)")
        ]:
            if r:
                comparison.append({
                    "name": name,
                    "cost": round(r.total_s, 2),
                    "total_s": round(r.total_s, 2),
                    "total_m": round(r.total_m, 1),
                    "nodesExpanded": r.expanded,
                    "timeMs": round(r.ms, 3),
                    "complexity": compl,
                    "hops": len(r.path) - 1
                })

        alts = []
        if payload.k_alternatives > 1:
            alts = campus_router_instance.k_shortest_paths(
                payload.source, payload.destination, k=payload.k_alternatives, profile=opt
            )

        return primary, comparison, alts

    primary_res, comparison_data, alternatives_res = await run_in_threadpool(_run_search)

    if not primary_res:
        raise HTTPException(
            status_code=404,
            detail="No route exists between the selected locations under current constraints."
        )

    # Use structured cross-level legs for directions
    directions = [
        {"action": leg.type, "text": leg.instructions, "distance": f"{leg.distance_m}m", "time": f"{round(leg.time_s)}s"}
        for leg in primary_res.legs
    ]

    return {
        "primary": primary_res.to_dict(),
        "legs": [leg.to_dict() for leg in primary_res.legs],
        "directions": directions,
        "comparison": comparison_data,
        "alternatives": [a.to_dict() for a in alternatives_res],
        "total_s": round(primary_res.total_s, 1),
        "total_m": round(primary_res.total_m, 1),
        "estimatedSeconds": round(primary_res.total_s),
        "sourceLabel": campus_router_instance.nodes_map[payload.source].label,
        "destinationLabel": campus_router_instance.nodes_map[payload.destination].label
    }

@app.post("/api/campus/multi-stop", status_code=status.HTTP_200_OK)
async def compute_campus_multi_stop(payload: CampusMultiStopRequest):
    """Computes exact/2-opt multi-stop itinerary across campus."""
    if payload.origin not in campus_router_instance.nodes_map:
        raise HTTPException(status_code=400, detail=f"Origin node '{payload.origin}' not found.")

    opt = RoutingOptions(
        avoid_stairs=payload.avoid_stairs,
        stairs_penalty=payload.stairs_penalty,
        accessible_only=payload.accessible_only,
        prefer_indoor=payload.prefer_indoor,
        outdoor_penalty=payload.outdoor_penalty
    )

    result = await run_in_threadpool(
        campus_router_instance.multi_stop_tsp, payload.origin, payload.stops, opt
    )
    return result

@app.get("/api/campus/shortcuts", status_code=status.HTTP_200_OK)
async def get_campus_shortcuts(node_id: str):
    """Returns nearest entrance, stairs, and lift from selected node."""
    if node_id not in campus_router_instance.nodes_map:
        raise HTTPException(status_code=400, detail="Node not found.")

    def _find():
        res_e = campus_router_instance.nearest_x(node_id, "e")
        res_s = campus_router_instance.nearest_x(node_id, "s")
        res_l = campus_router_instance.nearest_x(node_id, "l")

        def _fmt(r):
            if not r or not r.path or len(r.path) < 2:
                return None
            target = r.path[-1]
            return {
                "id": target,
                "label": campus_router_instance.nodes_map[target].label,
                "cost": round(r.total_s, 1),
                "distance_m": round(r.total_m, 1),
                "time_s": round(r.total_s, 1)
            }

        return {
            "nearest_entrance": _fmt(res_e),
            "nearest_stairs": _fmt(res_s),
            "nearest_lift": _fmt(res_l)
        }

    return await run_in_threadpool(_find)

@app.post("/api/campus/graph/save", status_code=status.HTTP_200_OK)
async def save_campus_graph(payload: CampusGraphData):
    """Saves updated campus graph and refreshes router (used by Dev Graph Editor)."""
    global campus_graph_instance, campus_router_instance
    try:
        payload.save_to_file("campus-graph.json")
        campus_graph_instance = payload
        campus_router_instance = CampusRouter(campus_graph_instance)
        return {"status": "success", "message": "Campus graph saved and re-indexed."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")
