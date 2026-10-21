import math
import time
import heapq
from collections import deque
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field

from .models import CampusGraphData, CampusNode, CampusEdge

@dataclass
class RoutingOptions:
    avoid_stairs: bool = False
    stairs_penalty: float = 4.0
    accessible_only: bool = False
    prefer_indoor: bool = False
    outdoor_penalty: float = 2.5

@dataclass
class RouteResult:
    algorithm: str
    path: List[str]
    edges: List[Dict[str, Any]]
    total_cost: float
    nodes_expanded: int
    time_ms: float
    visited_order: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "path": self.path,
            "edges": self.edges,
            "totalCost": round(self.total_cost, 2),
            "nodesExpanded": self.nodes_expanded,
            "timeMs": round(self.time_ms, 3),
            "visitedOrder": self.visited_order
        }

class CampusRouter:
    def __init__(self, graph_data: CampusGraphData):
        self.graph = graph_data
        self.nodes_map: Dict[str, CampusNode] = {n.id: n for n in graph_data.nodes}
        self.min_scale = min(graph_data.costModel.campus, graph_data.costModel.int_)
        self._build_static_adjacency()

    def _build_static_adjacency(self) -> None:
        """Pre-indexes adjacency for fast lookup."""
        self.adj: Dict[str, List[Tuple[str, CampusEdge]]] = {n.id: [] for n in self.graph.nodes}
        for edge in self.graph.edges:
            self.adj[edge.a].append((edge.b, edge))
            self.adj[edge.b].append((edge.a, edge))

    def get_effective_edge_cost(self, edge: CampusEdge, options: RoutingOptions) -> Optional[float]:
        """Calculates effective edge cost based on routing constraints."""
        if options.accessible_only and not edge.accessible:
            return None

        cost = edge.cost
        if edge.type == "s" and options.avoid_stairs:
            cost *= options.stairs_penalty
        if edge.outdoor and options.prefer_indoor:
            cost *= options.outdoor_penalty

        return cost

    def _reconstruct_path(
        self,
        start_id: str,
        target_id: str,
        parent_map: Dict[str, Tuple[str, CampusEdge, float]]
    ) -> Tuple[List[str], List[Dict[str, Any]], float]:
        path = [target_id]
        edges_out = []
        curr = target_id
        total_cost = 0.0

        while curr != start_id:
            prev, edge_obj, leg_cost = parent_map[curr]
            edges_out.append({
                "a": prev,
                "b": curr,
                "type": edge_obj.type,
                "cost": round(leg_cost, 2),
                "accessible": edge_obj.accessible,
                "outdoor": edge_obj.outdoor
            })
            total_cost += leg_cost
            curr = prev
            path.append(curr)

        path.reverse()
        edges_out.reverse()

        # Compute cumulative accumulated costs for edges
        accum = 0.0
        for e in edges_out:
            accum += e["cost"]
            e["accumulated"] = round(accum, 2)

        return path, edges_out, total_cost

    def dijkstra(
        self,
        source: str,
        target: str,
        options: Optional[RoutingOptions] = None,
        ignored_edges: Optional[Set[Tuple[str, str]]] = None,
        ignored_nodes: Optional[Set[str]] = None
    ) -> Optional[RouteResult]:
        """Dijkstra algorithm using a binary min-heap (heapq)."""
        t0 = time.perf_counter()
        opt = options or RoutingOptions()
        ignored_e = ignored_edges or set()
        ignored_n = ignored_nodes or set()

        if source not in self.nodes_map or target not in self.nodes_map:
            return None
        if source == target:
            return RouteResult(
                algorithm="Dijkstra (Binary Heap)",
                path=[source],
                edges=[],
                total_cost=0.0,
                nodes_expanded=0,
                time_ms=(time.perf_counter() - t0) * 1000,
                visited_order=[source]
            )

        dist: Dict[str, float] = {source: 0.0}
        parents: Dict[str, Tuple[str, CampusEdge, float]] = {}
        visited_order: List[str] = []
        settled: Set[str] = set()

        # Binary min-heap entries: (distance, tie_breaker_count, node_id)
        counter = 0
        pq: List[Tuple[float, int, str]] = [(0.0, counter, source)]

        while pq:
            d_u, _, u = heapq.heappop(pq)

            if u in settled:
                continue
            settled.add(u)
            visited_order.append(u)

            if u == target:
                break

            for v, edge in self.adj[u]:
                if v in settled or v in ignored_n:
                    continue
                if (u, v) in ignored_e or (v, u) in ignored_e:
                    continue

                eff_cost = self.get_effective_edge_cost(edge, opt)
                if eff_cost is None:
                    continue

                new_dist = d_u + eff_cost
                if new_dist < dist.get(v, float("inf")):
                    dist[v] = new_dist
                    parents[v] = (u, edge, eff_cost)
                    counter += 1
                    heapq.heappush(pq, (new_dist, counter, v))

        if target not in parents and source != target:
            return None

        path, edges_out, total_cost = self._reconstruct_path(source, target, parents)
        return RouteResult(
            algorithm="Dijkstra (Binary Heap)",
            path=path,
            edges=edges_out,
            total_cost=total_cost,
            nodes_expanded=len(settled),
            time_ms=(time.perf_counter() - t0) * 1000,
            visited_order=visited_order
        )

    def astar(
        self,
        source: str,
        target: str,
        options: Optional[RoutingOptions] = None
    ) -> Optional[RouteResult]:
        """A* Search with admissible Euclidean heuristic."""
        t0 = time.perf_counter()
        opt = options or RoutingOptions()

        if source not in self.nodes_map or target not in self.nodes_map:
            return None
        if source == target:
            return RouteResult(
                algorithm="A* (Admissible Heuristic)",
                path=[source],
                edges=[],
                total_cost=0.0,
                nodes_expanded=0,
                time_ms=(time.perf_counter() - t0) * 1000,
                visited_order=[source]
            )

        target_node = self.nodes_map[target]

        def heuristic(u_id: str) -> float:
            u_node = self.nodes_map[u_id]
            # Euclidean * min_scale only valid within the same level; cross-level h=0 ensures admissibility
            if u_node.level != target_node.level:
                return 0.0
            return math.hypot(u_node.x - target_node.x, u_node.y - target_node.y) * self.min_scale

        g_score: Dict[str, float] = {source: 0.0}
        parents: Dict[str, Tuple[str, CampusEdge, float]] = {}
        visited_order: List[str] = []
        settled: Set[str] = set()

        counter = 0
        h_start = heuristic(source)
        pq: List[Tuple[float, float, int, str]] = [(h_start, 0.0, counter, source)]

        while pq:
            f_u, g_u, _, u = heapq.heappop(pq)

            if u in settled:
                continue
            settled.add(u)
            visited_order.append(u)

            if u == target:
                break

            for v, edge in self.adj[u]:
                if v in settled:
                    continue

                eff_cost = self.get_effective_edge_cost(edge, opt)
                if eff_cost is None:
                    continue

                tentative_g = g_u + eff_cost
                if tentative_g < g_score.get(v, float("inf")):
                    g_score[v] = tentative_g
                    parents[v] = (u, edge, eff_cost)
                    counter += 1
                    f_v = tentative_g + heuristic(v)
                    heapq.heappush(pq, (f_v, tentative_g, counter, v))

        if target not in parents and source != target:
            return None

        path, edges_out, total_cost = self._reconstruct_path(source, target, parents)
        return RouteResult(
            algorithm="A* (Admissible Heuristic)",
            path=path,
            edges=edges_out,
            total_cost=total_cost,
            nodes_expanded=len(settled),
            time_ms=(time.perf_counter() - t0) * 1000,
            visited_order=visited_order
        )

    def bfs(
        self,
        source: str,
        target: str,
        options: Optional[RoutingOptions] = None
    ) -> Optional[RouteResult]:
        """Breadth-First Search (fewest unweighted hops)."""
        t0 = time.perf_counter()
        opt = options or RoutingOptions()

        if source not in self.nodes_map or target not in self.nodes_map:
            return None
        if source == target:
            return RouteResult(
                algorithm="Breadth-First Search (BFS)",
                path=[source],
                edges=[],
                total_cost=0.0,
                nodes_expanded=0,
                time_ms=(time.perf_counter() - t0) * 1000,
                visited_order=[source]
            )

        queue = deque([source])
        parents: Dict[str, Tuple[str, CampusEdge, float]] = {}
        visited_order: List[str] = [source]
        seen: Set[str] = {source}

        while queue:
            u = queue.popleft()

            if u == target:
                break

            for v, edge in self.adj[u]:
                if v in seen:
                    continue

                eff_cost = self.get_effective_edge_cost(edge, opt)
                if eff_cost is None:
                    continue

                seen.add(v)
                visited_order.append(v)
                parents[v] = (u, edge, eff_cost)
                queue.append(v)

        if target not in parents and source != target:
            return None

        path, edges_out, total_cost = self._reconstruct_path(source, target, parents)
        return RouteResult(
            algorithm="Breadth-First Search (BFS)",
            path=path,
            edges=edges_out,
            total_cost=total_cost,
            nodes_expanded=len(seen),
            time_ms=(time.perf_counter() - t0) * 1000,
            visited_order=visited_order
        )

    def bidirectional_dijkstra(
        self,
        source: str,
        target: str,
        options: Optional[RoutingOptions] = None
    ) -> Optional[RouteResult]:
        """Bidirectional Dijkstra search meeting from both endpoints."""
        t0 = time.perf_counter()
        opt = options or RoutingOptions()

        if source not in self.nodes_map or target not in self.nodes_map:
            return None
        if source == target:
            return RouteResult(
                algorithm="Bidirectional Dijkstra",
                path=[source],
                edges=[],
                total_cost=0.0,
                nodes_expanded=0,
                time_ms=(time.perf_counter() - t0) * 1000,
                visited_order=[source]
            )

        # Forward search state
        dist_f: Dict[str, float] = {source: 0.0}
        parent_f: Dict[str, Tuple[str, CampusEdge, float]] = {}
        settled_f: Set[str] = set()
        pq_f: List[Tuple[float, int, str]] = [(0.0, 0, source)]

        # Backward search state
        dist_b: Dict[str, float] = {target: 0.0}
        parent_b: Dict[str, Tuple[str, CampusEdge, float]] = {}
        settled_b: Set[str] = set()
        pq_b: List[Tuple[float, int, str]] = [(0.0, 0, target)]

        visited_order: List[str] = []
        counter = 0
        best_cost = float("inf")
        meeting_node: Optional[str] = None

        while pq_f and pq_b:
            # Check termination
            if pq_f[0][0] + pq_b[0][0] >= best_cost:
                break

            # Forward step
            if pq_f:
                d_u, _, u = heapq.heappop(pq_f)
                if u not in settled_f:
                    settled_f.add(u)
                    visited_order.append(u)

                    if u in settled_b:
                        cand = dist_f[u] + dist_b[u]
                        if cand < best_cost:
                            best_cost = cand
                            meeting_node = u

                    for v, edge in self.adj[u]:
                        if v in settled_f:
                            continue
                        eff_cost = self.get_effective_edge_cost(edge, opt)
                        if eff_cost is None:
                            continue

                        new_d = d_u + eff_cost
                        if new_d < dist_f.get(v, float("inf")):
                            dist_f[v] = new_d
                            parent_f[v] = (u, edge, eff_cost)
                            counter += 1
                            heapq.heappush(pq_f, (new_d, counter, v))

                            if v in settled_b:
                                cand = new_d + dist_b[v]
                                if cand < best_cost:
                                    best_cost = cand
                                    meeting_node = v

            # Backward step
            if pq_b:
                d_w, _, w = heapq.heappop(pq_b)
                if w not in settled_b:
                    settled_b.add(w)
                    visited_order.append(w)

                    if w in settled_f:
                        cand = dist_f[w] + dist_b[w]
                        if cand < best_cost:
                            best_cost = cand
                            meeting_node = w

                    for z, edge in self.adj[w]:
                        if z in settled_b:
                            continue
                        eff_cost = self.get_effective_edge_cost(edge, opt)
                        if eff_cost is None:
                            continue

                        new_d = d_w + eff_cost
                        if new_d < dist_b.get(z, float("inf")):
                            dist_b[z] = new_d
                            parent_b[z] = (w, edge, eff_cost)
                            counter += 1
                            heapq.heappush(pq_b, (new_d, counter, z))

                            if z in settled_f:
                                cand = dist_f[z] + new_d
                                if cand < best_cost:
                                    best_cost = cand
                                    meeting_node = z

        if meeting_node is None:
            return None

        # Reconstruct path through meeting node
        # 1. Forward half from source to meeting_node
        fwd_path = [meeting_node]
        fwd_edges: List[Dict[str, Any]] = []
        curr = meeting_node
        while curr != source:
            prev, edge_obj, cost_leg = parent_f[curr]
            fwd_edges.append({
                "a": prev,
                "b": curr,
                "type": edge_obj.type,
                "cost": round(cost_leg, 2),
                "accessible": edge_obj.accessible,
                "outdoor": edge_obj.outdoor
            })
            curr = prev
            fwd_path.append(curr)

        fwd_path.reverse()
        fwd_edges.reverse()

        # 2. Backward half from meeting_node to target
        curr = meeting_node
        while curr != target:
            nxt, edge_obj, cost_leg = parent_b[curr]
            fwd_edges.append({
                "a": curr,
                "b": nxt,
                "type": edge_obj.type,
                "cost": round(cost_leg, 2),
                "accessible": edge_obj.accessible,
                "outdoor": edge_obj.outdoor
            })
            curr = nxt
            fwd_path.append(curr)

        accum = 0.0
        for e in fwd_edges:
            accum += e["cost"]
            e["accumulated"] = round(accum, 2)

        return RouteResult(
            algorithm="Bidirectional Dijkstra",
            path=fwd_path,
            edges=fwd_edges,
            total_cost=best_cost,
            nodes_expanded=len(settled_f) + len(settled_b),
            time_ms=(time.perf_counter() - t0) * 1000,
            visited_order=visited_order
        )

    def k_shortest_paths(
        self,
        source: str,
        target: str,
        k: int = 3,
        options: Optional[RoutingOptions] = None
    ) -> List[RouteResult]:
        """Yen's algorithm for K-shortest loopless paths."""
        opt = options or RoutingOptions()
        first_route = self.dijkstra(source, target, opt)
        if not first_route:
            return []

        routes: List[RouteResult] = [first_route]
        # Candidate heap holds tuples: (total_cost, counter, path, edges)
        candidates: List[Tuple[float, int, List[str], List[Dict[str, Any]]]] = []
        cand_paths_set: Set[Tuple[str, ...]] = {tuple(first_route.path)}
        counter = 0

        for i in range(1, k):
            prev_path = routes[i - 1].path

            for spur_idx in range(len(prev_path) - 1):
                spur_node = prev_path[spur_idx]
                root_path = prev_path[:spur_idx + 1]

                # Edges to temporarily remove: edges coinciding with existing routes that share root_path
                removed_edges: Set[Tuple[str, str]] = set()
                for r in routes:
                    if r.path[:spur_idx + 1] == root_path and len(r.path) > spur_idx + 1:
                        removed_edges.add((r.path[spur_idx], r.path[spur_idx + 1]))
                        removed_edges.add((r.path[spur_idx + 1], r.path[spur_idx]))

                # Nodes in root_path (except spur_node) are excluded from search to avoid cycles
                removed_nodes: Set[str] = set(root_path[:-1])

                # Calculate spur path
                spur_route = self.dijkstra(
                    spur_node,
                    target,
                    opt,
                    ignored_edges=removed_edges,
                    ignored_nodes=removed_nodes
                )

                if spur_route:
                    # Construct full candidate path
                    total_p = root_path[:-1] + spur_route.path
                    p_tuple = tuple(total_p)

                    if p_tuple not in cand_paths_set:
                        cand_paths_set.add(p_tuple)

                        # Re-calculate edges and total cost accurately
                        edges_full = []
                        total_c = 0.0
                        valid_cand = True
                        for step_i in range(len(total_p) - 1):
                            na, nb = total_p[step_i], total_p[step_i + 1]
                            # Find connecting edge
                            matched_e = None
                            for v, ed in self.adj[na]:
                                if v == nb:
                                    matched_e = ed
                                    break
                            if matched_e is None:
                                valid_cand = False
                                break
                            eff_c = self.get_effective_edge_cost(matched_e, opt)
                            if eff_c is None:
                                valid_cand = False
                                break
                            total_c += eff_c
                            edges_full.append({
                                "a": na,
                                "b": nb,
                                "type": matched_e.type,
                                "cost": round(eff_c, 2),
                                "accessible": matched_e.accessible,
                                "outdoor": matched_e.outdoor
                            })

                        if valid_cand:
                            counter += 1
                            heapq.heappush(candidates, (total_c, counter, total_p, edges_full))

            if not candidates:
                break

            lowest_cost, _, best_p, best_e = heapq.heappop(candidates)
            accum = 0.0
            for e in best_e:
                accum += e["cost"]
                e["accumulated"] = round(accum, 2)

            routes.append(
                RouteResult(
                    algorithm=f"Yen's K-Shortest (Alternative #{len(routes) + 1})",
                    path=best_p,
                    edges=best_e,
                    total_cost=lowest_cost,
                    nodes_expanded=0,
                    time_ms=0.0,
                    visited_order=[]
                )
            )

        return routes

    def multi_stop_tsp(
        self,
        origin: str,
        stops: List[str],
        options: Optional[RoutingOptions] = None
    ) -> Dict[str, Any]:
        """Multi-stop routing via distance matrix + nearest-neighbour + 2-opt."""
        t0 = time.perf_counter()
        opt = options or RoutingOptions()

        # Unique ordered targets
        unique_stops = [s for s in stops if s != origin and s in self.nodes_map]
        all_points = [origin] + unique_stops

        if len(unique_stops) == 0:
            res = self.dijkstra(origin, origin, opt)
            return {
                "visit_sequence": [origin],
                "full_path": [origin],
                "legs": [],
                "total_cost": 0.0,
                "execution_time_ms": (time.perf_counter() - t0) * 1000
            }

        # 1. Compute distance matrix between all points
        dist_matrix: Dict[Tuple[str, str], Tuple[float, List[str], List[Dict[str, Any]]]] = {}
        for p1 in all_points:
            for p2 in all_points:
                if p1 == p2:
                    dist_matrix[(p1, p2)] = (0.0, [p1], [])
                elif (p2, p1) in dist_matrix:
                    d, p, e = dist_matrix[(p2, p1)]
                    # Reverse path & edges
                    rev_p = list(reversed(p))
                    rev_e = []
                    for ed in reversed(e):
                        rev_e.append({**ed, "a": ed["b"], "b": ed["a"]})
                    dist_matrix[(p1, p2)] = (d, rev_p, rev_e)
                else:
                    route = self.dijkstra(p1, p2, opt)
                    if route:
                        dist_matrix[(p1, p2)] = (route.total_cost, route.path, route.edges)
                    else:
                        dist_matrix[(p1, p2)] = (float("inf"), [], [])

        # 2. Nearest Neighbor tour
        unvisited = set(unique_stops)
        curr = origin
        tour = [origin]

        while unvisited:
            next_stop = min(unvisited, key=lambda n: dist_matrix.get((curr, n), (float("inf"),))[0])
            tour.append(next_stop)
            unvisited.remove(next_stop)
            curr = next_stop

        # 3. 2-opt local search optimization (origin stays fixed at index 0)
        improved = True
        n = len(tour)
        while improved:
            improved = False
            for i in range(1, n - 1):
                for j in range(i + 1, n):
                    # Current segments: (i-1 -> i) and (j -> j+1 if j+1 < n)
                    curr_cost = dist_matrix[(tour[i - 1], tour[i])][0]
                    new_cost = dist_matrix[(tour[i - 1], tour[j])][0]

                    if j + 1 < n:
                        curr_cost += dist_matrix[(tour[j], tour[j + 1])][0]
                        new_cost += dist_matrix[(tour[i], tour[j + 1])][0]

                    if new_cost + 1e-6 < curr_cost:
                        tour[i:j + 1] = reversed(tour[i:j + 1])
                        improved = True

        # 4. Expand full path & legs
        full_path: List[str] = [origin]
        legs_out: List[Dict[str, Any]] = []
        total_cost = 0.0

        for idx in range(len(tour) - 1):
            p_from = tour[idx]
            p_to = tour[idx + 1]
            leg_cost, leg_path, leg_edges = dist_matrix[(p_from, p_to)]

            if leg_cost == float("inf"):
                continue

            total_cost += leg_cost
            legs_out.append({
                "leg_index": idx + 1,
                "from_id": p_from,
                "from_label": self.nodes_map[p_from].label,
                "to_id": p_to,
                "to_label": self.nodes_map[p_to].label,
                "distance": round(leg_cost, 2),
                "path": leg_path,
                "edges": leg_edges
            })

            # Stitch path (skip duplicate connecting node)
            if len(leg_path) > 1:
                full_path.extend(leg_path[1:])

        return {
            "visit_sequence": tour,
            "full_path": full_path,
            "legs": legs_out,
            "total_cost": round(total_cost, 2),
            "stops_count": len(unique_stops),
            "execution_time_ms": round((time.perf_counter() - t0) * 1000, 3)
        }

    def generate_directions(self, edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Human-readable turn-by-turn guidance steps."""
        if not edges:
            return []

        steps = []
        for i, edge in enumerate(edges):
            na = self.nodes_map[edge["a"]]
            nb = self.nodes_map[edge["b"]]
            etype = edge["type"]

            if etype == "s":
                action = "climb"
                icon = "stairs"
                instruction = f"Take stairs from {na.label} to {nb.label} ({edge['cost']:.1f} cost)"
            elif etype == "l":
                action = "lift"
                icon = "lift"
                instruction = f"Take lift from {na.label} to {nb.label}"
            elif etype == "b":
                action = "bridge"
                icon = "bridge"
                instruction = f"Cross elevated bridge from {na.label} to {nb.label}"
            elif etype == "d":
                action = "door"
                icon = "door"
                instruction = f"Pass through doorway connecting {na.label} and {nb.label}"
            else:
                action = "walk"
                icon = "walk"
                instruction = f"Walk from {na.label} to {nb.label} ({edge['cost']:.1f} m)"

            steps.append({
                "step": i + 1,
                "action": action,
                "icon": icon,
                "from_id": na.id,
                "from_label": na.label,
                "to_id": nb.id,
                "to_label": nb.label,
                "edge_type": etype,
                "cost": edge["cost"],
                "instruction": instruction
            })

        return steps
