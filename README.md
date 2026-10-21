# Spatial Navigator - Campus & Retail Spatial Routing Engine

> **Analysis of Algorithms (AOA) Enterprise Project**: Indoor/Outdoor Multi-Floor Campus & Retail Spatial Graph Navigation, Multi-Algorithm Pathfinding, 2D Vector SVG + 3D WebGL (Three.js) Rendering, Empirical Parity Benchmarking, and Multi-Stop Routing.

---

## 🌟 Architecture & Features

### 1. Campus Indoor/Outdoor Blueprint Engine (`campus_navigation/`)
- **Single Source of Truth**: `campus-graph.json` contains the validated graph extracted from the Vidyalankar Institute of Technology (VIT) blueprint (81 nodes, 95 edges, 54 architectural rooms across campus grounds and multi-story indoor levels).
- **Strict Pydantic Schema Validation (`models.py`)**:
  - No duplicate node IDs.
  - No dangling edge endpoints (`u` or `v` missing).
  - No negative edge costs ($w \ge 0$).
  - Full graph connectivity verification via BFS traversal at load time.
- **Configurable Cost Model**:
  - Walk distance scale: Campus Outdoor $= 0.25$, Building Interior $= 0.1$.
  - Vertical transition penalties: Stairs $= 12.0$, Elevators/Lifts $= 8.0$, Threshold Doors $= 4.0$.
  - Edge attributes: `accessible` (boolean; `false` for stairs, `true` for ramps/elevators), `outdoor` (boolean).
- **Pure Algorithm Suite (`algorithms.py`)**:
  - **Dijkstra's Algorithm**: Min-heap priority queue ($O((V + E) \log V)$), early stopping on target.
  - **A\* Search**: Euclidean distance $\times \min(\text{campus scale}, \text{interior scale})$ heuristic; uses $h=0$ cross-level to guarantee admissibility and exact optimality.
  - **Bidirectional Dijkstra**: Dual-frontier simultaneous search from source and destination.
  - **Breadth-First Search (BFS)**: Unweighted fewest-hop pathfinding.
  - **Yen's Algorithm ($k$-Shortest Paths)**: Generates loopless alternative detour paths.
  - **Multi-Stop TSP**: Distance matrix computation + Nearest-Neighbor + 2-Opt local search refinement.
  - **Turn-by-Turn Guidance**: Natural language step generation ("Take stairs down to basement", "Cross bridge D -> Canteen", "Enter VIT building").
- **NetworkX Cross-Verification (`networkx_verifier.py`)**: Built-in parity checker comparing our pure heap implementations against Python's standard `networkx.dijkstra_path` and `networkx.astar_path`.

---

### 2. Interactive 2D & 3D Frontend (`index.html`, `static/`)
- **Unified Spatial Navigator**: Clean header preset switcher allowing seamless switching between **Campus Blueprint (2D / 3D)**, **VIT Campus (Retail/Graph)**, **Mega Mart**, and **Classic Store**.
- **Interactive 2D Blueprint (`static/campus_navigator.js`)**:
  - Pan/zoom via **D3-zoom** (60 fps rendering budget).
  - Architectural level switching: Campus Grounds (`c`), Floor 1 Walkway (`f1`), Basement Labs (`f0`).
  - Searchable origin and destination comboboxes with fuzzy search powered by **Fuse.js**.
  - Quick shortcuts: "Nearest Entrance", "Nearest Stairs", "Nearest Lift".
  - Path draw animation (`stroke-dashoffset`) and interactive search frontier step-by-step playback with scrub slider and speed control.
  - Live side-by-side benchmark comparison table (Cost, Nodes Expanded, Execution Time, Complexity).
  - Global overview minimap with real-time viewport drag/pan rectangle.
- **Interactive 3D Viewport (Three.js + OrbitControls)**:
  - **3D Campus Mode**: Extruded architectural buildings and landscape.
  - **3D Exploded Interior Mode**: Separated floor slabs with interactive elevation slider ($0\text{m} - 30\text{m}$) and transparent rooms.
  - Animated walker sphere moving continuously along the 3D Catmull-Rom tube path.
  - Camera auto-focus on computed route bounding box.
  - Raycaster click support on 3D node spheres.
- **Dev Graph Editor**:
  - Visual node repositioning via D3 drag.
  - Node creation and connection editing.
  - One-click JSON export and live server persistence with Pydantic validation via `POST /api/campus/graph/save`.
- **Accessibility & Themes**: Light and dark mode styling with full contrast support and ARIA labels.

---

## 📐 Data Format Specification (`campus-graph.json`)

```json
{
  "costModel": {
    "scaleCampus": 0.25,
    "scaleInterior": 0.1,
    "stairsPenalty": 12.0,
    "liftPenalty": 8.0,
    "doorPenalty": 4.0
  },
  "nodes": [
    {
      "id": "GATE",
      "label": "Main Gate",
      "level": "c",
      "x": 80,
      "y": 700,
      "type": "e"
    }
  ],
  "edges": [
    {
      "a": "GATE",
      "b": "R1",
      "type": "w",
      "cost": 27.5,
      "accessible": true,
      "outdoor": true
    }
  ],
  "rooms": [
    {
      "id": "r_vit_c",
      "label": "VIT",
      "level": "c",
      "x": 580,
      "y": 300,
      "width": 570,
      "height": 280,
      "kind": "bld"
    }
  ]
}
```

### Node Types
- `e`: Campus / Building Entrance
- `p`: Point of interest / Room / Lab
- `s`: Staircase
- `l`: Elevator / Lift
- `j`: Junction / Corridor intersection waypoint

### Edge Types
- `w`: Walking path / Corridor / Sidewalk
- `b`: Elevated connector bridge
- `s`: Staircase transition
- `l`: Elevator / Lift transition
- `d`: Building access door

---

## 🛠️ How to Add a New Building or Floor

1. **Add Rooms to `campus-graph.json`**:
   Define bounding boxes for new rooms under the `rooms` list, specifying `level` (e.g. `"f2"` for 2nd floor), `kind` (`"room"`, `"lab"`, `"stair"`, `"bridge"`, `"bld"`), `x`, `y`, `width`, and `height`.
2. **Add Nodes**:
   Add POIs and junctions with corresponding `level` and coordinate coordinates $(x, y)$.
3. **Add Edges**:
   Connect nodes using `a` and `b`. Precomputed `cost` can be computed automatically or left for the Pydantic loader to derive from Euclidean distance and the active `costModel`. Set `accessible: false` for stair edges.
4. **Vertical Connections**:
   Create two nodes with the same staircase/lift name on different levels (e.g. `STAIRS_F1` on `level: "f1"` and `STAIRS_F2` on `level: "f2"`), and link them with an edge of type `"s"` (or `"l"` for lifts).
5. **Alternatively, use the Dev Graph Editor**:
   Switch to the **Dev Graph Editor** tab in the UI, add/drag nodes, export the updated JSON, or click **"Validate & Save to Server"** to update in place.

---

## 🚀 Quick Start

### 1. Install Requirements
```powershell
pip install -r requirements.txt
```

### 2. Run Test Suite
```powershell
python -m pytest tests/
```
*Current test suite: 23 passing unit tests verifying graph validation, routing correctness, accessibility filters, K-shortest paths, TSP, and sub-5ms query performance.*

### 3. Start the Server
```powershell
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```
- **Web App**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📡 REST API Reference

### Campus Blueprint Endpoints
- `GET /api/campus/graph`: Returns validated campus graph topology, rooms, and cost model.
- `POST /api/campus/route`: Solves multi-criteria path query in a background thread. Returns primary path, turn directions, live multi-algorithm comparison, and Yen's alternative routes.
- `POST /api/campus/multi-stop`: Solves campus TSP itinerary using distance matrix and 2-opt search.
- `GET /api/campus/shortcuts?node_id=XYZ`: Returns the closest entrance, staircase, and lift from any given node.
- `POST /api/campus/graph/save`: Validates and saves updated topology from Dev Graph Editor.

### Existing Retail & AOA Endpoints
- `GET /api/graph`: Returns retail topology nodes and aisles.
- `POST /api/route`: Computes shortest path with choice of `dijkstra`, `astar`, `bellman-ford`, or `bfs`.
- `POST /api/optimize-shopping-list`: Computes exact Held-Karp order picking sequence.
- `POST /api/aisle/update`: Updates dynamic aisle edge weights.
- `POST /api/graph/preset`: Switches between `vidyalankar`, `mega`, and `classic` layouts.
- `POST /api/graph/reset`: Resets graph topology.
