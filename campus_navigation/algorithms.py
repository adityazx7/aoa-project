import math
import time
import heapq
from collections import deque
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field

from .models import CampusGraphData, CampusNode, CampusEdge
from .cost import CostConfig, RoutingProfile, WALK_SPEED_MPS, compute_edge_metrics

@dataclass
class Leg:
    type: str                  # "walk", "stairs", "lift", "door", "bridge"
    level: str                 # "c", "f1", "f0"
    path: List[str]            # Node IDs
    distance_m: float          # Leg physical distance
    time_s: float              # Leg walking time in seconds
    instructions: str          # Turn-by-turn guidance description
    landmark: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "level": self.level,
            "path": self.path,
            "distance_m": round(self.distance_m, 1),
            "time_s": round(self.time_s, 1),
            "instructions": self.instructions,
            "landmark": self.landmark
        }

@dataclass
class RouteResult:
    algorithm: str
    path: List[str]
    edges: List[Dict[str, Any]]
    legs: List[Leg]
    total_s: float
    total_m: float
    expanded: int
    visit_order: List[str]
    ms: float

    # Backward compatibility properties
    @property
    def total_cost(self) -> float:
        return self.total_s

    @property
    def nodes_expanded(self) -> int:
        return self.expanded

    @property
    def time_ms(self) -> float:
        return self.ms

    @property
    def visited_order(self) -> List[str]:
        return self.visit_order

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "path": self.path,
            "edges": self.edges,
            "legs": [leg.to_dict() for leg in self.legs],
            "total_s": round(self.total_s, 2),
            "total_m": round(self.total_m, 1),
            "totalCost": round(self.total_s, 2),
            "nodesExpanded": self.expanded,
            "timeMs": round(self.ms, 3),
            "visit_order": self.visit_order,
            "visitedOrder": self.visit_order
        }

# Backward compatibility alias
RoutingOptions = RoutingProfile

class CampusRouter:
    def __init__(self, graph_data: CampusGraphData, cost_config: CostConfig = CostConfig()):
        self.graph = graph_data
        self.cost_config = cost_config
        self.nodes_map: Dict[str, CampusNode] = {n.id: n for n in graph_data.nodes}
        self.landmarks: List[str] = []
        self.landmark_distances: Dict[str, Dict[str, float]] = {}  # landmark -> {node_id: dist_s}
        self._build_static_adjacency()
        self._init_landmarks()

    def _build_static_adjacency(self) -> None:
        """Pre-indexes undirected adjacency with both directions stored."""
        self.adj: Dict[str, List[Tuple[str, CampusEdge, float, float]]] = {n.id: [] for n in self.graph.nodes}
        for edge in self.graph.edges:
            na = self.nodes_map.get(edge.a)
            nb = self.nodes_map.get(edge.b)
            if not na or not nb:
                continue

            dist_m = getattr(edge, "distance_m", None)
            if dist_m is None or dist_m <= 0:
                scale = 0.18 if (na.level == "c" and nb.level == "c") else 0.1
                pix_dist = math.hypot(na.x - nb.x, na.y - nb.y)
                dist_m = max(pix_dist * scale, 1.0)
                edge.distance_m = dist_m

            if getattr(edge, "time_s", None) is not None and edge.time_s > 0:
                base_t = edge.time_s
            elif getattr(edge, "cost", None) is not None and edge.cost > 0:
                base_t = edge.cost
            else:
                base_t = compute_edge_metrics(edge.type, dist_m, edge.outdoor, self.cost_config)["time_s"]

            # Undirected graph: identical base metrics in both directions
            self.adj[edge.a].append((edge.b, edge, base_t, dist_m))
            self.adj[edge.b].append((edge.a, edge, base_t, dist_m))

    def get_effective_edge_cost(self, edge: CampusEdge, options: Optional[RoutingProfile] = None) -> Optional[float]:
        """Provides effective edge weight in seconds for external verifiers."""
        profile = options or RoutingProfile()
        na = self.nodes_map.get(edge.a)
        nb = self.nodes_map.get(edge.b)
        dist_m = getattr(edge, "distance_m", None)
        if dist_m is None or dist_m <= 0:
            scale = 0.18 if (na and nb and na.level == "c" and nb.level == "c") else 0.1
            pix_dist = math.hypot(na.x - nb.x, na.y - nb.y) if (na and nb) else 10.0
            dist_m = max(pix_dist * scale, 1.0)

        if getattr(edge, "time_s", None) is not None and edge.time_s > 0:
            base_t = edge.time_s
        elif getattr(edge, "cost", None) is not None and edge.cost > 0:
            base_t = edge.cost
        else:
            base_t = compute_edge_metrics(edge.type, dist_m, edge.outdoor, self.cost_config)["time_s"]

        return self._get_effective_time(edge, base_t, profile)

    def _init_landmarks(self) -> None:
        """Picks structural landmarks and precomputes baseline shortest path trees."""
        candidates = ["GATE", "VDA", "IL", "AUD", "LIB", "PARK", "R2", "T3", "B1"]
        self.landmarks = [c for c in candidates if c in self.nodes_map][:6]
        if not self.landmarks and self.nodes_map:
            self.landmarks = list(self.nodes_map.keys())[:min(4, len(self.nodes_map))]

        default_profile = RoutingProfile()
        self.landmark_distances = {}
        for lm in self.landmarks:
            dist_map = {}
            pq = [(0.0, lm)]
            dist_map[lm] = 0.0
            while pq:
                d, u = heapq.heappop(pq)
                if d > dist_map[u]:
                    continue
                for v, edge, t_s, _ in self.adj[u]:
                    eff_t = self._get_effective_time(edge, t_s, default_profile)
                    if eff_t is None:
                        continue
                    if d + eff_t < dist_map.get(v, float("inf")):
                        dist_map[v] = d + eff_t
                        heapq.heappush(pq, (d + eff_t, v))
            self.landmark_distances[lm] = dist_map

    def _get_effective_time(self, edge: CampusEdge, base_time_s: float, profile: RoutingProfile) -> Optional[float]:
        """Calculates effective traversal time (s) under active routing profile."""
        if (profile.wheelchair or profile.accessible_only) and not edge.accessible:
            return None

        t = base_time_s
        if edge.type == "s" and profile.avoid_stairs:
            mult = profile.stairs_penalty if getattr(profile, "stairs_penalty", None) is not None else self.cost_config.stairs_avoid_mult
            t *= mult
        if edge.outdoor and profile.prefer_indoor:
            mult = profile.outdoor_penalty if getattr(profile, "outdoor_penalty", None) is not None else self.cost_config.outdoor_penalty_mult
            t *= mult

        return t

    def _heuristic_euclidean(self, curr_id: str, target_id: str) -> float:
        """
        Admissible Euclidean lower bound in SECONDS.
        Per spec: Euclidean distance * minimum scale, only valid within a level;
        use h=0 for cross-level estimates so it stays optimal.
        """
        na = self.nodes_map[curr_id]
        nb = self.nodes_map[target_id]

        if na.level != nb.level:
            return 0.0

        min_scale = min(
            getattr(self.graph.costModel, "campus", 0.25),
            getattr(self.graph.costModel, "int_", 0.1)
        )
        dx = na.x - nb.x
        dy = na.y - nb.y
        dist_px = math.hypot(dx, dy)
        return dist_px * min_scale

    def _heuristic_alt(self, curr_id: str, target_id: str) -> float:
        """
        Admissible Landmark (ALT) lower bound using Triangle Inequality:
        h(u) = max_L |dist(L, target) - dist(L, u)|.
        """
        best_h = 0.0
        for lm in self.landmarks:
            d_map = self.landmark_distances.get(lm, {})
            if curr_id in d_map and target_id in d_map:
                diff = abs(d_map[curr_id] - d_map[target_id])
                if diff > best_h:
                    best_h = diff
        euc_h = self._heuristic_euclidean(curr_id, target_id)
        return max(best_h, euc_h)

    def _reconstruct(
        self,
        start_id: str,
        target_id: str,
        parent_map: Dict[str, Tuple[str, CampusEdge, float, float]]
    ) -> Tuple[List[str], List[Dict[str, Any]], float, float]:
        path = [target_id]
        edges_out = []
        curr = target_id
        tot_s = 0.0
        tot_m = 0.0

        while curr != start_id:
            prev, edge_obj, t_s, d_m = parent_map[curr]
            edges_out.append({
                "a": prev,
                "b": curr,
                "type": edge_obj.type,
                "time_s": round(t_s, 2),
                "distance_m": round(d_m, 1),
                "cost": round(t_s, 2),
                "accessible": edge_obj.accessible,
                "outdoor": edge_obj.outdoor
            })
            tot_s += t_s
            tot_m += d_m
            curr = prev
            path.append(curr)

        path.reverse()
        edges_out.reverse()

        accum_s = 0.0
        accum_m = 0.0
        for e in edges_out:
            accum_s += e["time_s"]
            accum_m += e["distance_m"]
            e["accumulated_s"] = round(accum_s, 2)
            e["accumulated_m"] = round(accum_m, 1)
            e["accumulated"] = round(accum_s, 2)

        return path, edges_out, tot_s, tot_m

    def generate_legs(self, path: List[str], edges: List[Dict[str, Any]]) -> List[Leg]:
        """
        Stitches the route into structured cross-level legs:
        walk(level) -> portal(stairs/lift/door) -> walk(level)...
        """
        if not path or len(path) < 2:
            return []

        legs: List[Leg] = []
        curr_type = edges[0]["type"]
        curr_level = self.nodes_map[path[0]].level
        curr_path = [path[0]]
        curr_dist = 0.0
        curr_time = 0.0

        def _leg_type_category(etype: str) -> str:
            if etype in ("s", "l", "d"):
                return etype
            return "walk"

        curr_cat = _leg_type_category(curr_type)

        for idx, e in enumerate(edges):
            u = e["a"]
            v = e["b"]
            nv = self.nodes_map[v]
            e_cat = _leg_type_category(e["type"])

            if e_cat != curr_cat or nv.level != curr_level:
                desc = self._describe_leg(curr_cat, curr_level, curr_path, curr_dist, curr_time)
                lm = getattr(self.nodes_map[curr_path[0]], "landmark", None)
                legs.append(Leg(
                    type=curr_cat,
                    level=curr_level,
                    path=curr_path,
                    distance_m=curr_dist,
                    time_s=curr_time,
                    instructions=desc,
                    landmark=lm
                ))
                curr_cat = e_cat
                curr_level = nv.level
                curr_path = [u, v]
                curr_dist = e["distance_m"]
                curr_time = e["time_s"]
            else:
                curr_path.append(v)
                curr_dist += e["distance_m"]
                curr_time += e["time_s"]

        if curr_path:
            desc = self._describe_leg(curr_cat, curr_level, curr_path, curr_dist, curr_time)
            lm = getattr(self.nodes_map[curr_path[-1]], "landmark", None)
            legs.append(Leg(
                type=curr_cat,
                level=curr_level,
                path=curr_path,
                distance_m=curr_dist,
                time_s=curr_time,
                instructions=desc,
                landmark=lm
            ))

        return legs

    def _describe_leg(self, cat: str, level: str, path: List[str], dist_m: float, time_s: float) -> str:
        start_lbl = self.nodes_map[path[0]].label
        end_lbl = self.nodes_map[path[-1]].label
        lv_name = {"c": "Campus Outdoors", "f1": "Floor 1 Walkway", "f0": "Basement Labs"}.get(level, level)

        if cat == "s":
            direction = "down" if "0" in path[-1] else "up"
            return f"Take stairs {direction} from {start_lbl} to {end_lbl} (~{round(time_s)}s)"
        elif cat == "l":
            return f"Take elevator from {start_lbl} to {end_lbl} (~{round(time_s)}s)"
        elif cat == "d":
            return f"Pass doorway connecting {start_lbl} and {end_lbl}"
        else:
            return f"Walk {round(dist_m)}m on {lv_name} from {start_lbl} to {end_lbl}"

    # -------------------------------------------------------------
    # 1. HEAP DIJKSTRA
    # -------------------------------------------------------------
    def dijkstra(self, source: str, destination: str, profile: RoutingProfile = RoutingProfile()) -> Optional[RouteResult]:
        t0 = time.perf_counter()
        if source not in self.nodes_map or destination not in self.nodes_map:
            return None

        dist_map: Dict[str, float] = {source: 0.0}
        parent_map: Dict[str, Tuple[str, CampusEdge, float, float]] = {}
        visited_order: List[str] = []
        pq: List[Tuple[float, str]] = [(0.0, source)]
        settled: Set[str] = set()

        while pq:
            d, u = heapq.heappop(pq)
            if u in settled:
                continue
            settled.add(u)
            visited_order.append(u)

            if u == destination:
                break

            for v, edge, t_s, d_m in self.adj[u]:
                if v in settled:
                    continue
                eff_t = self._get_effective_time(edge, t_s, profile)
                if eff_t is None:
                    continue
                alt_d = d + eff_t
                if alt_d < dist_map.get(v, float("inf")):
                    dist_map[v] = alt_d
                    parent_map[v] = (u, edge, eff_t, d_m)
                    heapq.heappush(pq, (alt_d, v))

        if destination not in parent_map and source != destination:
            return None

        ms = (time.perf_counter() - t0) * 1000.0
        if source == destination:
            return RouteResult("dijkstra", [source], [], [], 0.0, 0.0, len(settled), [source], ms)

        path, edges, tot_s, tot_m = self._reconstruct(source, destination, parent_map)
        legs = self.generate_legs(path, edges)
        return RouteResult("dijkstra", path, edges, legs, tot_s, tot_m, len(settled), visited_order, ms)

    # -------------------------------------------------------------
    # 2. A* SEARCH (EUCLIDEAN HEURISTIC)
    # -------------------------------------------------------------
    def astar(self, source: str, destination: str, profile: RoutingProfile = RoutingProfile()) -> Optional[RouteResult]:
        t0 = time.perf_counter()
        if source not in self.nodes_map or destination not in self.nodes_map:
            return None

        g_score: Dict[str, float] = {source: 0.0}
        parent_map: Dict[str, Tuple[str, CampusEdge, float, float]] = {}
        visited_order: List[str] = []
        settled: Set[str] = set()

        h_init = self._heuristic_euclidean(source, destination)
        pq: List[Tuple[float, float, str]] = [(h_init, 0.0, source)]

        while pq:
            f, g, u = heapq.heappop(pq)
            if g > g_score.get(u, float("inf")):
                continue
            settled.add(u)
            visited_order.append(u)

            if u == destination:
                break

            for v, edge, t_s, d_m in self.adj[u]:
                eff_t = self._get_effective_time(edge, t_s, profile)
                if eff_t is None:
                    continue
                tentative_g = g + eff_t
                if tentative_g < g_score.get(v, float("inf")):
                    g_score[v] = tentative_g
                    parent_map[v] = (u, edge, eff_t, d_m)
                    h_v = self._heuristic_euclidean(v, destination)
                    heapq.heappush(pq, (tentative_g + h_v, tentative_g, v))

        if destination not in parent_map and source != destination:
            return None

        ms = (time.perf_counter() - t0) * 1000.0
        if source == destination:
            return RouteResult("astar", [source], [], [], 0.0, 0.0, len(settled), [source], ms)

        path, edges, tot_s, tot_m = self._reconstruct(source, destination, parent_map)
        legs = self.generate_legs(path, edges)
        return RouteResult("astar", path, edges, legs, tot_s, tot_m, len(settled), visited_order, ms)

    # -------------------------------------------------------------
    # 3. ALT (A* WITH LANDMARKS & TRIANGLE INEQUALITY)
    # -------------------------------------------------------------
    def alt(self, source: str, destination: str, profile: RoutingProfile = RoutingProfile()) -> Optional[RouteResult]:
        t0 = time.perf_counter()
        if source not in self.nodes_map or destination not in self.nodes_map:
            return None

        g_score: Dict[str, float] = {source: 0.0}
        parent_map: Dict[str, Tuple[str, CampusEdge, float, float]] = {}
        visited_order: List[str] = []
        settled: Set[str] = set()

        h_init = self._heuristic_alt(source, destination)
        pq: List[Tuple[float, float, str]] = [(h_init, 0.0, source)]

        while pq:
            f, g, u = heapq.heappop(pq)
            if g > g_score.get(u, float("inf")):
                continue
            settled.add(u)
            visited_order.append(u)

            if u == destination:
                break

            for v, edge, t_s, d_m in self.adj[u]:
                eff_t = self._get_effective_time(edge, t_s, profile)
                if eff_t is None:
                    continue
                tentative_g = g + eff_t
                if tentative_g < g_score.get(v, float("inf")):
                    g_score[v] = tentative_g
                    parent_map[v] = (u, edge, eff_t, d_m)
                    h_v = self._heuristic_alt(v, destination)
                    heapq.heappush(pq, (tentative_g + h_v, tentative_g, v))

        if destination not in parent_map and source != destination:
            return None

        ms = (time.perf_counter() - t0) * 1000.0
        if source == destination:
            return RouteResult("alt", [source], [], [], 0.0, 0.0, len(settled), [source], ms)

        path, edges, tot_s, tot_m = self._reconstruct(source, destination, parent_map)
        legs = self.generate_legs(path, edges)
        return RouteResult("alt", path, edges, legs, tot_s, tot_m, len(settled), visited_order, ms)

    # -------------------------------------------------------------
    # 4. BIDIRECTIONAL DIJKSTRA
    # -------------------------------------------------------------
    def bidirectional_dijkstra(self, source: str, destination: str, profile: RoutingProfile = RoutingProfile()) -> Optional[RouteResult]:
        t0 = time.perf_counter()
        if source not in self.nodes_map or destination not in self.nodes_map:
            return None

        if source == destination:
            ms = (time.perf_counter() - t0) * 1000.0
            return RouteResult("bidirectional", [source], [], [], 0.0, 0.0, 1, [source], ms)

        dist_fwd: Dict[str, float] = {source: 0.0}
        dist_bwd: Dict[str, float] = {destination: 0.0}
        parent_fwd: Dict[str, Tuple[str, CampusEdge, float, float]] = {}
        parent_bwd: Dict[str, Tuple[str, CampusEdge, float, float]] = {}

        pq_fwd = [(0.0, source)]
        pq_bwd = [(0.0, destination)]
        settled_fwd: Set[str] = set()
        settled_bwd: Set[str] = set()
        visited_order: List[str] = []

        best_cost = float("inf")
        meeting_node: Optional[str] = None

        while pq_fwd and pq_bwd:
            if pq_fwd[0][0] + pq_bwd[0][0] >= best_cost:
                break

            # Forward step
            df, u = heapq.heappop(pq_fwd)
            if u not in settled_fwd:
                settled_fwd.add(u)
                visited_order.append(u)
                if u in settled_bwd:
                    cost = dist_fwd[u] + dist_bwd[u]
                    if cost < best_cost:
                        best_cost = cost
                        meeting_node = u

                for v, edge, t_s, d_m in self.adj[u]:
                    eff_t = self._get_effective_time(edge, t_s, profile)
                    if eff_t is None:
                        continue
                    new_d = df + eff_t
                    if new_d < dist_fwd.get(v, float("inf")):
                        dist_fwd[v] = new_d
                        parent_fwd[v] = (u, edge, eff_t, d_m)
                        heapq.heappush(pq_fwd, (new_d, v))
                        if v in settled_bwd:
                            c = new_d + dist_bwd[v]
                            if c < best_cost:
                                best_cost = c
                                meeting_node = v

            # Backward step
            db, w = heapq.heappop(pq_bwd)
            if w not in settled_bwd:
                settled_bwd.add(w)
                visited_order.append(w)
                if w in settled_fwd:
                    cost = dist_fwd[w] + dist_bwd[w]
                    if cost < best_cost:
                        best_cost = cost
                        meeting_node = w

                for z, edge, t_s, d_m in self.adj[w]:
                    eff_t = self._get_effective_time(edge, t_s, profile)
                    if eff_t is None:
                        continue
                    new_d = db + eff_t
                    if new_d < dist_bwd.get(z, float("inf")):
                        dist_bwd[z] = new_d
                        parent_bwd[z] = (w, edge, eff_t, d_m)
                        heapq.heappush(pq_bwd, (new_d, z))
                        if z in settled_fwd:
                            c = new_d + dist_fwd[z]
                            if c < best_cost:
                                best_cost = c
                                meeting_node = z

        if meeting_node is None or best_cost == float("inf"):
            return None

        # Reconstruct path through meeting node
        curr = meeting_node
        fwd_edges: List[Dict[str, Any]] = []
        fwd_nodes = [meeting_node]
        tot_m = 0.0

        while curr != source:
            prev, edge_obj, t_s, d_m = parent_fwd[curr]
            fwd_edges.append({
                "a": prev, "b": curr, "type": edge_obj.type,
                "time_s": round(t_s, 2), "distance_m": round(d_m, 1),
                "cost": round(t_s, 2), "accessible": edge_obj.accessible, "outdoor": edge_obj.outdoor
            })
            tot_m += d_m
            curr = prev
            fwd_nodes.append(curr)

        fwd_nodes.reverse()
        fwd_edges.reverse()

        curr = meeting_node
        bwd_edges: List[Dict[str, Any]] = []
        bwd_nodes = []

        while curr != destination:
            nxt, edge_obj, t_s, d_m = parent_bwd[curr]
            bwd_edges.append({
                "a": curr, "b": nxt, "type": edge_obj.type,
                "time_s": round(t_s, 2), "distance_m": round(d_m, 1),
                "cost": round(t_s, 2), "accessible": edge_obj.accessible, "outdoor": edge_obj.outdoor
            })
            tot_m += d_m
            curr = nxt
            bwd_nodes.append(curr)

        full_path = fwd_nodes + bwd_nodes
        full_edges = fwd_edges + bwd_edges

        accum_s = 0.0
        accum_m = 0.0
        for e in full_edges:
            accum_s += e["time_s"]
            accum_m += e["distance_m"]
            e["accumulated_s"] = round(accum_s, 2)
            e["accumulated_m"] = round(accum_m, 1)
            e["accumulated"] = round(accum_s, 2)

        ms = (time.perf_counter() - t0) * 1000.0
        legs = self.generate_legs(full_path, full_edges)
        return RouteResult(
            "bidirectional", full_path, full_edges, legs,
            best_cost, tot_m, len(settled_fwd) + len(settled_bwd), visited_order, ms
        )

    # -------------------------------------------------------------
    # 5. BREADTH-FIRST SEARCH (FEWEST HOPS)
    # -------------------------------------------------------------
    def bfs(self, source: str, destination: str, profile: RoutingProfile = RoutingProfile()) -> Optional[RouteResult]:
        t0 = time.perf_counter()
        if source not in self.nodes_map or destination not in self.nodes_map:
            return None

        queue = deque([source])
        parent_map: Dict[str, Tuple[str, CampusEdge, float, float]] = {}
        visited: Set[str] = {source}
        visit_order: List[str] = []

        while queue:
            u = queue.popleft()
            visit_order.append(u)
            if u == destination:
                break

            for v, edge, t_s, d_m in self.adj[u]:
                if v not in visited:
                    eff_t = self._get_effective_time(edge, t_s, profile)
                    if eff_t is None:
                        continue
                    visited.add(v)
                    parent_map[v] = (u, edge, eff_t, d_m)
                    queue.append(v)

        if destination not in parent_map and source != destination:
            return None

        ms = (time.perf_counter() - t0) * 1000.0
        if source == destination:
            return RouteResult("bfs", [source], [], [], 0.0, 0.0, 1, [source], ms)

        path, edges, tot_s, tot_m = self._reconstruct(source, destination, parent_map)
        legs = self.generate_legs(path, edges)
        return RouteResult("bfs", path, edges, legs, tot_s, tot_m, len(visited), visit_order, ms)

    # -------------------------------------------------------------
    # 6. YEN'S K-SHORTEST PATHS
    # -------------------------------------------------------------
    def k_shortest_paths(
        self,
        source: str,
        destination: str,
        k: int = 3,
        profile: RoutingProfile = RoutingProfile()
    ) -> List[RouteResult]:
        initial = self.dijkstra(source, destination, profile)
        if not initial or not initial.path:
            return []

        A: List[RouteResult] = [initial]
        B: List[Tuple[float, List[str]]] = []
        B_set: Set[Tuple[str, ...]] = set()

        for i in range(1, k):
            prev_path = A[-1].path
            for spur_idx in range(len(prev_path) - 1):
                spur_node = prev_path[spur_idx]
                root_path = prev_path[:spur_idx + 1]

                excluded_edges: Set[Tuple[str, str]] = set()
                for existing in A:
                    if len(existing.path) > spur_idx and existing.path[:spur_idx + 1] == root_path:
                        excluded_edges.add((existing.path[spur_idx], existing.path[spur_idx + 1]))
                        excluded_edges.add((existing.path[spur_idx + 1], existing.path[spur_idx]))

                spur_res = self._dijkstra_with_exclusions(
                    spur_node, destination, profile, excluded_edges, set(root_path[:-1])
                )
                if spur_res and spur_res.path:
                    total_candidate_path = root_path[:-1] + spur_res.path
                    t_cand = tuple(total_candidate_path)
                    if t_cand not in B_set:
                        B_set.add(t_cand)
                        cost_s = self._calculate_path_time(total_candidate_path, profile)
                        if cost_s is not None:
                            heapq.heappush(B, (cost_s, total_candidate_path))

            if not B:
                break

            lowest_cost, next_path = heapq.heappop(B)
            res = self._build_result_from_path(next_path, f"yen_alt_{i}", profile)
            if res:
                A.append(res)

        return A

    def _dijkstra_with_exclusions(
        self,
        source: str,
        destination: str,
        profile: RoutingProfile,
        excluded_edges: Set[Tuple[str, str]],
        excluded_nodes: Set[str]
    ) -> Optional[RouteResult]:
        dist_map: Dict[str, float] = {source: 0.0}
        parent_map: Dict[str, Tuple[str, CampusEdge, float, float]] = {}
        pq = [(0.0, source)]
        settled: Set[str] = set()

        while pq:
            d, u = heapq.heappop(pq)
            if u in settled:
                continue
            settled.add(u)
            if u == destination:
                break

            for v, edge, t_s, d_m in self.adj[u]:
                if v in settled or v in excluded_nodes:
                    continue
                if (u, v) in excluded_edges or (v, u) in excluded_edges:
                    continue
                eff_t = self._get_effective_time(edge, t_s, profile)
                if eff_t is None:
                    continue
                alt_d = d + eff_t
                if alt_d < dist_map.get(v, float("inf")):
                    dist_map[v] = alt_d
                    parent_map[v] = (u, edge, eff_t, d_m)
                    heapq.heappush(pq, (alt_d, v))

        if destination not in parent_map and source != destination:
            return None

        path, edges, tot_s, tot_m = self._reconstruct(source, destination, parent_map)
        legs = self.generate_legs(path, edges)
        return RouteResult("dijkstra_spur", path, edges, legs, tot_s, tot_m, len(settled), [], 0.0)

    def _calculate_path_time(self, path: List[str], profile: RoutingProfile) -> Optional[float]:
        tot = 0.0
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            found = False
            for nb, edge, t_s, _ in self.adj[u]:
                if nb == v:
                    eff_t = self._get_effective_time(edge, t_s, profile)
                    if eff_t is None:
                        return None
                    tot += eff_t
                    found = True
                    break
            if not found:
                return None
        return tot

    def _build_result_from_path(self, path: List[str], label: str, profile: RoutingProfile) -> Optional[RouteResult]:
        edges = []
        tot_s = 0.0
        tot_m = 0.0
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            found = False
            for nb, edge, t_s, d_m in self.adj[u]:
                if nb == v:
                    eff_t = self._get_effective_time(edge, t_s, profile)
                    if eff_t is None:
                        return None
                    edges.append({
                        "a": u, "b": v, "type": edge.type,
                        "time_s": round(eff_t, 2), "distance_m": round(d_m, 1),
                        "cost": round(eff_t, 2), "accessible": edge.accessible, "outdoor": edge.outdoor
                    })
                    tot_s += eff_t
                    tot_m += d_m
                    found = True
                    break
            if not found:
                return None

        legs = self.generate_legs(path, edges)
        return RouteResult(label, path, edges, legs, tot_s, tot_m, len(path), [], 0.0)

    # -------------------------------------------------------------
    # 7. NEAREST-X (MULTI-TARGET SINGLE DIJKSTRA)
    # -------------------------------------------------------------
    def nearest_x(self, source: str, target_kind: str, profile: RoutingProfile = RoutingProfile()) -> Optional[RouteResult]:
        """Finds closest node matching target_kind ('e'=entrance, 's'=stairs, 'l'=lift) using one SSSP."""
        if source not in self.nodes_map:
            return None

        dist_map: Dict[str, float] = {source: 0.0}
        parent_map: Dict[str, Tuple[str, CampusEdge, float, float]] = {}
        pq = [(0.0, source)]
        settled: Set[str] = set()

        found_target: Optional[str] = None

        while pq:
            d, u = heapq.heappop(pq)
            if u in settled:
                continue
            settled.add(u)

            if u != source and self.nodes_map[u].type == target_kind:
                found_target = u
                break

            for v, edge, t_s, d_m in self.adj[u]:
                if v in settled:
                    continue
                eff_t = self._get_effective_time(edge, t_s, profile)
                if eff_t is None:
                    continue
                alt_d = d + eff_t
                if alt_d < dist_map.get(v, float("inf")):
                    dist_map[v] = alt_d
                    parent_map[v] = (u, edge, eff_t, d_m)
                    heapq.heappush(pq, (alt_d, v))

        if not found_target:
            return None

        path, edges, tot_s, tot_m = self._reconstruct(source, found_target, parent_map)
        legs = self.generate_legs(path, edges)
        return RouteResult(f"nearest_{target_kind}", path, edges, legs, tot_s, tot_m, len(settled), [], 0.0)

    # -------------------------------------------------------------
    # 8. MULTI-STOP ROUTING (DISTANCE MATRIX + 2-OPT TSP)
    # -------------------------------------------------------------
    def multi_stop_tsp(
        self,
        origin: str,
        stops: List[str],
        profile: RoutingProfile = RoutingProfile()
    ) -> Dict[str, Any]:
        all_points = [origin] + [s for s in stops if s != origin]
        n = len(all_points)
        if n <= 1:
            return {"ordered_stops": all_points, "complete_path": all_points, "total_s": 0.0, "total_m": 0.0, "legs": []}

        # 1. Pairwise distance matrix
        cost_matrix: Dict[Tuple[str, str], float] = {}
        path_matrix: Dict[Tuple[str, str], List[str]] = {}

        for p in all_points:
            for q in all_points:
                if p == q:
                    cost_matrix[(p, q)] = 0.0
                    path_matrix[(p, q)] = [p]
                else:
                    r = self.dijkstra(p, q, profile)
                    if r and r.path:
                        cost_matrix[(p, q)] = r.total_s
                        path_matrix[(p, q)] = r.path
                    else:
                        cost_matrix[(p, q)] = float("inf")
                        path_matrix[(p, q)] = []

        # 2. Nearest-Neighbor Tour
        unvisited = set(all_points[1:])
        curr = origin
        tour = [origin]
        while unvisited:
            next_p = min(unvisited, key=lambda candidate: cost_matrix.get((curr, candidate), float("inf")))
            tour.append(next_p)
            unvisited.remove(next_p)
            curr = next_p

        # 3. 2-Opt Local Search
        def _tour_cost(t_list: List[str]) -> float:
            c = 0.0
            for i in range(len(t_list) - 1):
                c += cost_matrix.get((t_list[i], t_list[i + 1]), float("inf"))
            return c

        improved = True
        best_tour = list(tour)
        best_cost = _tour_cost(best_tour)

        while improved:
            improved = False
            for i in range(1, len(best_tour) - 1):
                for j in range(i + 1, len(best_tour)):
                    new_tour = best_tour[:i] + best_tour[i:j + 1][::-1] + best_tour[j + 1:]
                    new_cost = _tour_cost(new_tour)
                    if new_cost < best_cost - 1e-4:
                        best_tour = new_tour
                        best_cost = new_cost
                        improved = True
                        break
                if improved:
                    break

        # 4. Stitch intermediate paths
        stitched_path: List[str] = []
        all_edges: List[Dict[str, Any]] = []
        pairwise_legs: List[Dict[str, Any]] = []
        tot_m = 0.0
        tot_s = 0.0

        for i in range(len(best_tour) - 1):
            p1 = best_tour[i]
            p2 = best_tour[i + 1]
            seg_res = self.dijkstra(p1, p2, profile)
            if seg_res and seg_res.path:
                if stitched_path:
                    stitched_path.extend(seg_res.path[1:])
                else:
                    stitched_path.extend(seg_res.path)
                all_edges.extend(seg_res.edges)
                tot_s += seg_res.total_s
                tot_m += seg_res.total_m
                pairwise_legs.append(seg_res.to_dict())

        detailed_legs = self.generate_legs(stitched_path, all_edges)
        return {
            "visit_sequence": best_tour,
            "ordered_stops": best_tour,
            "full_path": stitched_path,
            "complete_path": stitched_path,
            "total_s": round(tot_s, 2),
            "total_m": round(tot_m, 1),
            "total_cost": round(tot_s, 2),
            "legs": pairwise_legs,
            "detailed_legs": [leg.to_dict() for leg in detailed_legs],
            "sub_legs": [leg.to_dict() for leg in detailed_legs]
        }
