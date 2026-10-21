# Spatial Navigator v2 — Campus Navigation Blueprint (VIT Wadala)

Put this file at `docs/BLUEPRINT.md` in the repo, and the reference photos/maps in `docs/reference/`. The agent should treat both as the spec.

## 0. Sources and limits
- Used: the 12 screenshots/photos in this chat (6 reference images, 6 app screenshots), and the earlier hand sketches.
- NOT read: the YouTube tour (video can't be watched) and the GitHub repo (could not be opened). Anything about the code below is inferred from the running app. The agent must audit the real code first.
- Public facts: VIT campus is in Wadala East, about 19.0216°N, 72.8708°E, roughly 11 acres, with three buildings (VIT, VSIT, Polytechnic) and gardens. The architecture is the "Un-Campus" by Planet 3 Studios.

## 1. Diagnosis from the screenshots
**2D views**
1. A black rectangle sits top-right on every 2D tab (broken minimap or canvas).
2. Labels collide with nodes: "Inn◯ation lab", "St◯rs", "M-block ◯wer hall", "La◯B1". "Basketball court" overflows its box.
3. Edges are straight lines between node centres, so routes cut through rooms and walls (the orange route crosses B block and A block). Real walking runs along corridors and through doors.
4. The map is not fitted to the viewport: large empty margins, small content, no zoom-to-route.
5. Campus tab with a selected route (Parking → VP door) draws no route line at all. Cross-level routes (VIT door → Innovation lab) show only the segment of the current level.
6. The tab bar shows "3D Campus" selected while the canvas still shows the 2D map (state/tab desync). The "Explode Floor Slabs" slider appears on the plain 3D Campus tab, where it makes no sense.
7. Distances are inconsistent ("136.1 m", "Leg cost 4.0m", "~3 min walk"): pixel units and metres appear to be mixed.

**3D views**
- Flat, unlit cyan boxes with no labels, no ground, no shadows; the navy background clashes with the light UI.
- The campus is not auto-framed and no path is drawn in 3D Campus. In the exploded interior the route is visible but unlabeled, and the camera angle is poor.
- The VIT interior is modelled as a plain slab. In reality it is a full-height atrium (see §2).

**Algorithm checks (common causes of "not working as I need")**
- Edges stored one-way, or only one direction added to the adjacency list.
- Cost units mixed (px vs m vs seconds), or stairs/lift/door penalties not in the same unit as walking.
- A* heuristic inadmissible because indoor and campus coordinates are not in one metric frame.
- Stale adjacency cache after Dev Editor edits; "Auto-Apply" firing with only one point selected.
- Cross-level edges missing the reverse direction; "avoid stairs" making some targets unreachable with no message.

## 2. Ground truth from photos and maps
**Interior photos (atrium)**
- One huge covered atrium under a steel-truss roof, with brightly coloured block volumes (yellow slanted, orange, timber-clad, blue/black glass boxes) cantilevered into the void, joined by steel bridges and open staircases.
- A sunken opening with a stair descends to the lower (lab) level (photo 2): this is the real "stairs to basement".
- Faceted glass façade on one side; handrails everywhere; landmarks: red telephone box, red poster board, orange/yellow volumes.
- Implications: the first-floor "walkway" is an open plaza floor with bridges above it. Model plaza as an open polygon (free-walk zone), not a single corridor line. Add upper bridges as separate edges at a higher z.

**Maps (mapcarta, 50 m scale bar ≈ 205 px)**
- The main building is about 95–100 m long. That calibrates the sketch scale: the VIT interior sketch ≈ 0.1 m/px, the campus sketch ≈ 0.18 m/px (not the 0.25 used earlier).
- On the map the playground/garden are south and south-west of the main building, and Ganesh Nagar road runs to the south-east. In the user's sketch the grounds are above the road. The sketch may be flipped or rotated, so georeference using 3–4 control points instead of assuming north-up.
- The lower-left of the satellite image shows a sports ground with a court, and a second long building south of the main one.

## 3. Target architecture
```
data/campus.v2.json        single source of truth (validated)
backend/ (FastAPI)         graph loader, routing engine, benchmark endpoint
  engine/graph.py          typed graph + CSR adjacency
  engine/algos/            dijkstra.py astar.py bidir.py alt.py yen.py bfs.py
  engine/cost.py           time-based cost model + profiles
  tests/                   pytest + hypothesis, cross-check with networkx
frontend/ (Vite+React+TS)  store (Zustand), MapView2D, MapView3D, RoutePanel
docs/BLUEPRINT.md, docs/reference/*
```
Keep the existing server entry (the app runs at 127.0.0.1:8000). If it is plain static JS, migrate gradually and keep it working at each step.

## 4. Data model v2
One metric frame for everything: local ENU metres with origin at a surveyed campus point, plus a similarity transform to lat/lng for the map layer. Indoor nodes live in the same frame (z = floor height).
```json
{
  "meta": {"origin": [19.0216, 72.8708], "rotation_deg": 0, "units": "m"},
  "levels": [{"id":"c","z":0},{"id":"f0","z":-4.5},{"id":"f1","z":0}],
  "zones":  [{"id":"plaza","level":"f1","polygon":[[0,0],[40,0]],"walkable":true}],
  "nodes":  [{"id":"EA","label":"Entrance (A block)","level":"f1","xy":[41.2,3.0],"kind":"entrance","landmark":"opposite A block"}],
  "edges":  [{"a":"EA","b":"W5","kind":"walk","path":[[41.2,3.0],[41.2,9.0]],"width_m":3,"accessible":true,"outdoor":false}],
  "portals":[{"id":"stairs_R","kind":"stairs","between":["SR0","S1R"],"flights":1,"accessible":false},
             {"id":"lift_1","kind":"lift","between":["LIFT0","LIFT1"],"accessible":true}]
}
```
- Edges carry a polyline `path` (corridor/door waypoints), so rendering follows the real walkway, and length comes from the polyline in metres. Edges are undirected by default (`oneway` optional).
- Validation (zod/pydantic): unique ids, no dangling refs, edge length > 0, graph connected per accessibility mode, every portal has both ends, every named place reachable.

## 5. Cost model (seconds, not pixels)
`edge_time = length_m / walk_speed` with walk_speed = 1.3 m/s.
- Stairs: 12 s per flight (up) / 9 s (down). Lift: 20 s wait + 8 s ride. Door: 3 s. Bridge: same as walk.
- User profile multipliers: `avoid_stairs` (×4 or forbidden), `wheelchair` (stairs forbidden, min width 1.0 m), `prefer_indoor` (outdoor ×1.3), `quiet_route`, `crowd[time_of_day]` for canteen/plaza edges (e.g. lunch ×1.5).
- Always report both distance (m) and time (min). Never mix units: the engine only deals in seconds; the UI converts.

## 6. Algorithms and correctness
- Dijkstra with a binary heap (`heapq`), A* with h = Euclidean metres / v_max (+ a minimum vertical penalty when levels differ). Valid and consistent because all coordinates share one metric frame. Bidirectional Dijkstra, BFS (fewest hops), ALT (landmarks) for the AOA comparison, Yen's k-shortest for alternatives, and nearest-X (entrance/stairs/lift/toilets) via a single multi-target Dijkstra.
- Return `{path, edges, total_s, total_m, expanded, visit_order, ms}` for every algorithm. Same inputs must give the same optimal cost across Dijkstra/A*/bidirectional (tie-breaking may change the path, not the cost).
- Multi-stop (A→B→C) with a distance matrix + nearest-neighbour + 2-opt.
- Property tests: random graphs vs networkx; A* never worse than Dijkstra; symmetry (cost(a,b)=cost(b,a)); triangle inequality; unreachable returns a clear error.
- Benchmarks (pytest-benchmark): per-algorithm ms and nodes expanded shown in the UI table. Budget: < 5 ms per query at current graph size.

## 6b. Route stitching (cross-level)
The route is a list of **legs**: `walk(level) → portal(stairs/lift/door) → walk(level) …`. The UI shows one leg at a time ("step through"), auto-switches the level tab, and also draws the whole path as a ghosted overview on every tab (current-level legs solid, other levels dashed).

## 7. 2D UX spec
- Library: SVG + d3-zoom for pan/zoom with `fitToBounds` on load and on route change (padding 10%); or PixiJS/Konva if the node count grows. Fix the minimap: draw a scaled-down SVG of the same scene with a viewport rectangle (or remove it).
- Rooms: rounded rects, fill by type (lab, stairs, canteen, auditorium, outdoor). Labels sit **inside** the room, clamp font size, truncate with a tooltip; never put labels under nodes. Show nodes only for selectable places, entrances and portals; hide junction nodes unless Dev Editor is on.
- Routes follow edge polylines: animated dash along the path, direction chevrons, start/end pins with labels, "you are here" pulse. Level-change markers show "↓ Stairs to Basement" chips.
- Selection: a command-palette style combobox (cmdk + fuse.js) with level badges, recent places, swap button, "nearest entrance / stairs / lift / canteen" buttons, and click-on-map selection.
- Directions panel: turn-by-turn using landmarks ("Go down the sunken stairs beside the red telephone box"), distance + time per leg, total in the header, copy/share route as URL (`?from=EA&to=T3&algo=astar`), print view.
- Algorithm panel: run Dijkstra / A* / BFS / bidirectional side by side; replay "search frontier" with a speed slider; table of cost, expanded, ms, complexity.
- Visual design: one theme system (light/dark via CSS variables), calm palette, 8 px spacing grid, consistent icon set (lucide), skeleton loaders, accessible contrast and keyboard navigation. No dead space: the map card fills the viewport height.

## 8. 3D spec
- three.js with @react-three/fiber + drei (OrbitControls, Html/Billboard labels, Line2 for thick paths, Environment, ContactShadows). Theme-aware background, ground plane, soft directional light + hemisphere light, shadows only on key meshes.
- Campus mode: extruded footprints with real-ish heights, roads, grass for the grounds, parking; labels as billboards; auto-frame the camera to the route; route as an animated ribbon with a moving marker.
- Interior mode: exploded floors with the explode slider **only here**. Model the atrium as a void with the cantilevered coloured volumes as separate boxes, a roof truss hint (simple line grid), the sunken stair void, bridges as thin slabs. Use colours from the photos (yellow, orange, timber, blue glass).
- Level focus: click a level to fade the others to 15% opacity. Click a node/room in 3D to select it. Dispose geometries/materials on unmount; instance repeated labs.
- Camera presets: Overview / Follow route / Top-down. A "Center View" button works in every mode.

## 9. Libraries (check the existing stack before adding)
| Need | Choice |
|---|---|
| Frontend | Vite + React + TypeScript (strict), Zustand, Tailwind + shadcn/ui, lucide-react, framer-motion |
| 2D | d3-zoom + SVG (or PixiJS / react-konva for scale) |
| Search UI | cmdk, fuse.js |
| 3D | three, @react-three/fiber, @react-three/drei |
| Outdoor georeferenced layer (optional) | MapLibre GL JS with OSM footprints (Overpass) and a custom indoor overlay |
| Validation | zod (front), pydantic v2 (back) |
| Backend | FastAPI, uvicorn, numpy, scipy.sparse.csgraph (benchmarks), networkx (cross-check only) |
| Geo | pyproj, shapely (calibration, polygon checks) |
| Tests | pytest, hypothesis, pytest-benchmark, Vitest, Playwright for UI screenshots |

## 10. Acceptance criteria
1. No black box; labels never overlap nodes; map fits the viewport on load.
2. Every route follows polylines through doors/corridors and never crosses a room.
3. Selecting any two named places draws the full route on the right tabs and lists legs with distance and time.
4. Dijkstra, A*, bidirectional return the same optimal cost on 1,000 random pairs; BFS reports hops.
5. Avoid-stairs and wheelchair modes reroute through lifts or report "no accessible route" with the reason.
6. 3D campus has labels, ground, shadows and the route; the explode slider appears only in interior mode.
7. Tab state and canvas never desync; deep links restore the state.
8. Tests pass; a query takes < 5 ms; 60 fps pan/zoom on a laptop.

## 11. Data you still need to provide (ask the agent to leave TODO markers)
- A calibrated floor plan: 3–4 control points measured on the real campus (Google Earth ruler or paced distances), including door positions and corridor widths.
- Which VIT door faces which direction, and how M block connects to VIT at each level.
- Upper floors (stairs up from E/F/B) if you want them in the graph.
- Notes from the YouTube tour: timestamps with "enter → turn left → stairs down" so landmarks can be added to `landmark` fields.

## 12. Phases
1. Audit and fix: reproduce the bugs in §1, add the engine tests, unify units (seconds/metres).
2. Data v2: calibrated frame, polyline edges, portals, validation.
3. 2D UX: fit, labels, routes, panels, minimap.
4. 3D: lighting, labels, atrium, route ribbon, camera.
5. Polish: share links, print, performance, accessibility, README.
