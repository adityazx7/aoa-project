import heapq
import math
import time
from typing import Dict, List, Tuple, Any, Optional

class StoreEngine:
    def __init__(self, vertices: int):
        self.V = vertices
        self.adj: Dict[int, List[Tuple[int, float]]] = {i: [] for i in range(vertices)}
        self.edges: List[Tuple[int, int, float]] = []
        self.matrix: List[List[float]] = [[float('inf')] * vertices for _ in range(vertices)]
        self.node_positions: Dict[int, Tuple[float, float]] = {}
        self.node_metadata: Dict[int, Dict[str, Any]] = {}
        for i in range(vertices):
            self.matrix[i][i] = 0.0

    def set_node_metadata(self, node_id: int, name: str, category: str, icon: str, x: float, y: float):
        self.node_positions[node_id] = (x, y)
        self.node_metadata[node_id] = {
            "name": name,
            "category": category,
            "icon": icon,
            "x": x,
            "y": y
        }

    def add_aisle(self, u: int, v: int, weight: float, bidirectional: bool = True):
        """Add or update an aisle connection with the specified weight."""
        weight = float(weight)
        # Remove existing if updating
        self.adj[u] = [(nbr, w) for nbr, w in self.adj[u] if nbr != v]
        self.adj[u].append((v, weight))
        self.matrix[u][v] = weight

        # Update edges list
        self.edges = [(su, sv, sw) for su, sv, sw in self.edges if not (su == u and sv == v)]
        self.edges.append((u, v, weight))

        if bidirectional:
            self.adj[v] = [(nbr, w) for nbr, w in self.adj[v] if nbr != u]
            self.adj[v].append((u, weight))
            self.matrix[v][u] = weight
            self.edges = [(su, sv, sw) for su, sv, sw in self.edges if not (su == v and sv == u)]
            self.edges.append((v, u, weight))

    def update_aisle(self, u: int, v: int, new_weight: float, bidirectional: bool = True):
        self.add_aisle(u, v, new_weight, bidirectional)

    def heuristic(self, u: int, v: int) -> float:
        """Euclidean distance heuristic for A* using node 2D coordinates."""
        if u in self.node_positions and v in self.node_positions:
            x1, y1 = self.node_positions[u]
            x2, y2 = self.node_positions[v]
            # Scaled Euclidean distance as admissible heuristic
            return math.hypot(x2 - x1, y2 - y1) / 50.0
        return 0.0

    def _clean_dist(self, d: float) -> Optional[float]:
        return None if d == float('inf') else round(d, 2)

    def _clean_dist_list(self, dists: List[float]) -> List[Optional[float]]:
        return [self._clean_dist(d) for d in dists]

    def dijkstra(self, start: int, target: Optional[int] = None) -> Tuple[List[float], List[int], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Dijkstra's Algorithm with Min-Heap Priority Queue.
        Time Complexity: O((V + E) log V)
        Space Complexity: O(V + E)
        """
        t0 = time.perf_counter()
        distances = [float('inf')] * self.V
        predecessors = [-1] * self.V
        visited = [False] * self.V
        distances[start] = 0.0
        pq: List[Tuple[float, int]] = [(0.0, start)]

        trace = []
        operations = 0
        relaxations = 0

        trace.append({
            "step": 0,
            "type": "init",
            "current_node": start,
            "description": f"Initialized source node {start} with distance 0. All other nodes set to ∞.",
            "distances": self._clean_dist_list(distances),
            "visited_nodes": [],
            "frontier": [start]
        })

        step_idx = 1
        while pq:
            curr_dist, u = heapq.heappop(pq)
            operations += 1

            if visited[u]:
                continue
            visited[u] = True

            trace.append({
                "step": step_idx,
                "type": "settle_node",
                "current_node": u,
                "current_dist": round(curr_dist, 2),
                "description": f"Extracted node {u} from min-heap with settled optimal distance {curr_dist:.1f}.",
                "distances": self._clean_dist_list(distances),
                "visited_nodes": [i for i, v in enumerate(visited) if v],
                "frontier": [node for _, node in pq if not visited[node]]
            })
            step_idx += 1

            if target is not None and u == target:
                trace.append({
                    "step": step_idx,
                    "type": "target_reached",
                    "current_node": u,
                    "description": f"Target node {target} settled. Early exit triggered.",
                    "distances": self._clean_dist_list(distances),
                    "visited_nodes": [i for i, v in enumerate(visited) if v],
                    "frontier": []
                })
                break

            for v, weight in self.adj[u]:
                operations += 1
                if not visited[v]:
                    new_dist = curr_dist + weight
                    if new_dist < distances[v]:
                        relaxations += 1
                        old_d = distances[v]
                        distances[v] = new_dist
                        predecessors[v] = u
                        heapq.heappush(pq, (new_dist, v))
                        trace.append({
                            "step": step_idx,
                            "type": "relax_edge",
                            "current_node": u,
                            "neighbor": v,
                            "edge_weight": weight,
                            "old_distance": self._clean_dist(old_d),
                            "new_distance": round(new_dist, 2),
                            "description": f"Relaxed edge ({u} → {v}) with weight {weight}: improved distance from {('∞' if old_d == float('inf') else f'{old_d:.1f}')} to {new_dist:.1f}.",
                            "distances": self._clean_dist_list(distances),
                            "visited_nodes": [i for i, v in enumerate(visited) if v],
                            "frontier": [node for _, node in pq if not visited[node]]
                        })
                        step_idx += 1

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        stats = {
            "execution_time_ms": round(elapsed_ms, 3),
            "operations_count": operations,
            "relaxations_count": relaxations,
            "nodes_visited": sum(1 for v in visited if v),
            "time_complexity": "O((V + E) log V)",
            "space_complexity": "O(V + E)"
        }
        return distances, predecessors, trace, stats

    def astar(self, start: int, target: int) -> Tuple[List[float], List[int], List[Dict[str, Any]], Dict[str, Any]]:
        """
        A* Search Algorithm with Admissible Euclidean Distance Heuristic.
        f(n) = g(n) + h(n)
        Time Complexity: O(E) best case, O((V + E) log V) typical
        Space Complexity: O(V)
        """
        t0 = time.perf_counter()
        g_scores = [float('inf')] * self.V
        f_scores = [float('inf')] * self.V
        predecessors = [-1] * self.V
        closed_set = [False] * self.V

        g_scores[start] = 0.0
        h_start = self.heuristic(start, target)
        f_scores[start] = h_start

        # pq stores: (f_score, g_score, node_id)
        pq: List[Tuple[float, float, int]] = [(f_scores[start], 0.0, start)]

        trace = []
        operations = 0
        relaxations = 0

        trace.append({
            "step": 0,
            "type": "init",
            "current_node": start,
            "description": f"Initialized A* search from node {start} to {target}. Heuristic h({start}) = {h_start:.1f}.",
            "distances": self._clean_dist_list(g_scores),
            "visited_nodes": [],
            "frontier": [start]
        })

        step_idx = 1
        while pq:
            curr_f, curr_g, u = heapq.heappop(pq)
            operations += 1

            if closed_set[u]:
                continue
            closed_set[u] = True

            trace.append({
                "step": step_idx,
                "type": "settle_node",
                "current_node": u,
                "current_dist": round(curr_g, 2),
                "f_score": round(curr_f, 2),
                "h_score": round(self.heuristic(u, target), 2),
                "description": f"Popped node {u} with f={curr_f:.1f} (g={curr_g:.1f}, h={self.heuristic(u, target):.1f}).",
                "distances": self._clean_dist_list(g_scores),
                "visited_nodes": [i for i, v in enumerate(closed_set) if v],
                "frontier": [node for _, _, node in pq if not closed_set[node]]
            })
            step_idx += 1

            if u == target:
                trace.append({
                    "step": step_idx,
                    "type": "target_reached",
                    "current_node": u,
                    "description": f"Destination node {target} reached with optimal g-cost {curr_g:.1f}.",
                    "distances": self._clean_dist_list(g_scores),
                    "visited_nodes": [i for i, v in enumerate(closed_set) if v],
                    "frontier": []
                })
                break

            for v, weight in self.adj[u]:
                operations += 1
                if closed_set[v]:
                    continue

                tentative_g = curr_g + weight
                if tentative_g < g_scores[v]:
                    relaxations += 1
                    old_g = g_scores[v]
                    g_scores[v] = tentative_g
                    predecessors[v] = u
                    h_val = self.heuristic(v, target)
                    f_val = tentative_g + h_val
                    f_scores[v] = f_val
                    heapq.heappush(pq, (f_val, tentative_g, v))

                    trace.append({
                        "step": step_idx,
                        "type": "relax_edge",
                        "current_node": u,
                        "neighbor": v,
                        "edge_weight": weight,
                        "old_distance": self._clean_dist(old_g),
                        "new_distance": round(tentative_g, 2),
                        "f_score": round(f_val, 2),
                        "h_score": round(h_val, 2),
                        "description": f"Evaluated neighbor {v}: g={tentative_g:.1f}, h={h_val:.1f} ⇒ f={f_val:.1f}.",
                        "distances": self._clean_dist_list(g_scores),
                        "visited_nodes": [i for i, v in enumerate(closed_set) if v],
                        "frontier": [node for _, _, node in pq if not closed_set[node]]
                    })
                    step_idx += 1

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        stats = {
            "execution_time_ms": round(elapsed_ms, 3),
            "operations_count": operations,
            "relaxations_count": relaxations,
            "nodes_visited": sum(1 for v in closed_set if v),
            "time_complexity": "O(E) to O((V + E) log V)",
            "space_complexity": "O(V)"
        }
        return g_scores, predecessors, trace, stats

    def bellman_ford(self, start: int) -> Tuple[List[float], List[int], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Bellman-Ford Algorithm with Negative Cycle Detection.
        Time Complexity: O(V * E)
        Space Complexity: O(V)
        """
        t0 = time.perf_counter()
        distances = [float('inf')] * self.V
        predecessors = [-1] * self.V
        distances[start] = 0.0

        trace = []
        operations = 0
        relaxations = 0

        trace.append({
            "step": 0,
            "type": "init",
            "current_node": start,
            "description": f"Initialized Bellman-Ford from node {start}. All other distances set to ∞.",
            "distances": self._clean_dist_list(distances),
            "visited_nodes": [start],
            "frontier": []
        })

        step_idx = 1
        # Relax edges up to V - 1 times
        for iteration in range(1, self.V):
            updated = False
            round_relaxations = 0
            for u, v, weight in self.edges:
                operations += 1
                if distances[u] != float('inf') and distances[u] + weight < distances[v]:
                    old_d = distances[v]
                    distances[v] = distances[u] + weight
                    predecessors[v] = u
                    updated = True
                    relaxations += 1
                    round_relaxations += 1

            trace.append({
                "step": step_idx,
                "type": "iteration_summary",
                "iteration": iteration,
                "relaxations_in_round": round_relaxations,
                "description": f"Completed relaxation round {iteration}/{self.V - 1}. Relaxed {round_relaxations} edge(s).",
                "distances": self._clean_dist_list(distances),
                "visited_nodes": [i for i, d in enumerate(distances) if d != float('inf')],
                "frontier": []
            })
            step_idx += 1

            if not updated:
                trace.append({
                    "step": step_idx,
                    "type": "early_termination",
                    "description": f"Early termination: graph converged at round {iteration} with no further distance improvements.",
                    "distances": self._clean_dist_list(distances),
                    "visited_nodes": [i for i, d in enumerate(distances) if d != float('inf')],
                    "frontier": []
                })
                break

        # Check for negative weight cycles
        negative_cycle = False
        for u, v, weight in self.edges:
            operations += 1
            if distances[u] != float('inf') and distances[u] + weight < distances[v]:
                negative_cycle = True
                trace.append({
                    "step": step_idx,
                    "type": "negative_cycle",
                    "description": f"Negative cycle detected along edge ({u} → {v})!",
                    "distances": self._clean_dist_list(distances),
                    "visited_nodes": [],
                    "frontier": []
                })
                raise ValueError("Graph contains a negative weight cycle!")

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        stats = {
            "execution_time_ms": round(elapsed_ms, 3),
            "operations_count": operations,
            "relaxations_count": relaxations,
            "nodes_visited": sum(1 for d in distances if d != float('inf')),
            "time_complexity": "O(V * E)",
            "space_complexity": "O(V)"
        }
        return distances, predecessors, trace, stats

    def bfs(self, start: int, target: Optional[int] = None) -> Tuple[List[float], List[int], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Breadth-First Search (BFS) for unweighted / hop-count routing.
        Time Complexity: O(V + E)
        Space Complexity: O(V)
        """
        t0 = time.perf_counter()
        distances = [float('inf')] * self.V
        predecessors = [-1] * self.V
        visited = [False] * self.V
        queue = [start]
        visited[start] = True
        distances[start] = 0.0

        trace = []
        operations = 0
        step_idx = 1

        trace.append({
            "step": 0,
            "type": "init",
            "current_node": start,
            "description": f"BFS initialized at node {start}. Queue: [{start}].",
            "distances": self._clean_dist_list(distances),
            "visited_nodes": [start],
            "frontier": [start]
        })

        while queue:
            u = queue.pop(0)
            operations += 1

            trace.append({
                "step": step_idx,
                "type": "settle_node",
                "current_node": u,
                "current_dist": distances[u],
                "description": f"Dequeued node {u} at depth {int(distances[u])} hops.",
                "distances": self._clean_dist_list(distances),
                "visited_nodes": [i for i, v in enumerate(visited) if v],
                "frontier": list(queue)
            })
            step_idx += 1

            if target is not None and u == target:
                break

            for v, _ in self.adj[u]:
                operations += 1
                if not visited[v]:
                    visited[v] = True
                    distances[v] = distances[u] + 1
                    predecessors[v] = u
                    queue.append(v)
                    trace.append({
                        "step": step_idx,
                        "type": "relax_edge",
                        "current_node": u,
                        "neighbor": v,
                        "description": f"Discovered unvisited neighbor {v} at depth {int(distances[v])}.",
                        "distances": self._clean_dist_list(distances),
                        "visited_nodes": [i for i, v in enumerate(visited) if v],
                        "frontier": list(queue)
                    })
                    step_idx += 1

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        stats = {
            "execution_time_ms": round(elapsed_ms, 3),
            "operations_count": operations,
            "relaxations_count": sum(1 for p in predecessors if p != -1),
            "nodes_visited": sum(1 for v in visited if v),
            "time_complexity": "O(V + E)",
            "space_complexity": "O(V)"
        }
        return distances, predecessors, trace, stats

    def floyd_warshall_with_paths(self) -> Tuple[List[List[float]], List[List[int]]]:
        """
        All-Pairs Shortest Path via Floyd-Warshall with complete predecessor tracking.
        Time Complexity: O(V^3)
        Space Complexity: O(V^2)
        """
        dist = [row[:] for row in self.matrix]
        nxt = [[-1 if dist[i][j] == float('inf') or i == j else j for j in range(self.V)] for i in range(self.V)]

        for k in range(self.V):
            for i in range(self.V):
                for j in range(self.V):
                    if dist[i][k] + dist[k][j] < dist[i][j]:
                        dist[i][j] = dist[i][k] + dist[k][j]
                        nxt[i][j] = nxt[i][k]
        return dist, nxt

    def reconstruct_apsp_path(self, nxt: List[List[int]], u: int, v: int) -> List[int]:
        if nxt[u][v] == -1:
            return []
        path = [u]
        curr = u
        visited_guard = set()
        while curr != v:
            visited_guard.add(curr)
            curr = nxt[curr][v]
            if curr in visited_guard: # cycle protection
                break
            path.append(curr)
        return path

    def optimize_shopping_list_dp(self, entrance: int, item_nodes: List[int]) -> Dict[str, Any]:
        """
        Exact Multi-Item Route Planning via Held-Karp Dynamic Programming (TSP with fixed start).
        Computes the optimal order picking sequence and stitches the complete physical walking path.
        Time Complexity: O(n^2 * 2^n) where n = number of stops.
        Space Complexity: O(n * 2^n)
        """
        t0 = time.perf_counter()
        apsp_dist, apsp_next = self.floyd_warshall_with_paths()

        # Unique ordered stops starting with entrance
        filtered_items = [n for n in dict.fromkeys(item_nodes) if n != entrance and 0 <= n < self.V]
        nodes = [entrance] + filtered_items
        n = len(nodes)

        if n <= 1:
            return {
                "entrance": entrance,
                "visit_sequence": [entrance],
                "full_path": [entrance],
                "legs": [],
                "total_cost": 0.0,
                "execution_time_ms": 0.0,
                "strategy": "Held-Karp Dynamic Programming"
            }

        memo: Dict[Tuple[int, int], Tuple[float, List[int]]] = {}

        def visit(mask: int, u_idx: int) -> Tuple[float, List[int]]:
            # All items visited
            if mask == (1 << n) - 1:
                return 0.0, [nodes[u_idx]]

            state = (mask, u_idx)
            if state in memo:
                return memo[state]

            best_cost = float('inf')
            best_sequence: List[int] = []

            for v_idx in range(n):
                if not (mask & (1 << v_idx)):
                    step_cost = apsp_dist[nodes[u_idx]][nodes[v_idx]]
                    if step_cost < float('inf'):
                        sub_cost, sub_sequence = visit(mask | (1 << v_idx), v_idx)
                        total = step_cost + sub_cost
                        if total < best_cost:
                            best_cost = total
                            best_sequence = [nodes[u_idx]] + sub_sequence

            memo[state] = (best_cost, best_sequence)
            return memo[state]

        cost, sequence = visit(1, 0)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Stitch full walkable path through all intermediate aisles
        full_path = []
        legs = []

        for i in range(len(sequence) - 1):
            src = sequence[i]
            dst = sequence[i + 1]
            leg_path = self.reconstruct_apsp_path(apsp_next, src, dst)
            leg_dist = apsp_dist[src][dst]

            src_name = self.node_metadata.get(src, {}).get("name", f"Node {src}")
            dst_name = self.node_metadata.get(dst, {}).get("name", f"Node {dst}")

            legs.append({
                "from_node": src,
                "from_name": src_name,
                "to_node": dst,
                "to_name": dst_name,
                "distance": leg_dist,
                "subpath": leg_path
            })

            if not full_path:
                full_path.extend(leg_path)
            else:
                full_path.extend(leg_path[1:])

        return {
            "entrance": entrance,
            "visit_sequence": sequence,
            "full_path": full_path if full_path else sequence,
            "legs": legs,
            "total_cost": round(cost, 2),
            "execution_time_ms": round(elapsed_ms, 3),
            "strategy": "Held-Karp Dynamic Programming (O(n² 2ⁿ) Exact TSP)",
            "stops_count": len(sequence)
        }