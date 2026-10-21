import random
import math
import networkx as nx
import pytest
from hypothesis import given, strategies as st, settings

from campus_navigation.models import CampusGraphData, CampusNode, CampusEdge, CostModel
from campus_navigation.algorithms import CampusRouter, RoutingProfile
from campus_navigation.cost import CostConfig

def build_random_connected_graph(num_nodes=15, edge_prob=0.35, seed=42):
    random.seed(seed)
    nodes = []
    levels = ["c", "f1", "f0"]
    for i in range(num_nodes):
        nid = f"N{i}"
        lv = levels[i % len(levels)]
        x = float(random.randint(100, 1000))
        y = float(random.randint(100, 600))
        ntype = "s" if i in (3, 7) else ("l" if i == 5 else ("e" if i == 0 else "p"))
        nodes.append(CampusNode(id=nid, label=f"Node {nid}", level=lv, x=x, y=y, type=ntype))

    nodes_map = {n.id: n for n in nodes}
    # Ensure connectedness via random spanning tree + additional random edges
    edges = []
    shuffled = list(range(num_nodes))
    random.shuffle(shuffled)
    
    edge_set = set()
    for i in range(1, num_nodes):
        u = f"N{shuffled[i-1]}"
        v = f"N{shuffled[i]}"
        edge_set.add((min(u, v), max(u, v)))
        is_cross = nodes_map[u].level != nodes_map[v].level
        if is_cross:
            # Vertical shafts (stairs/lifts) share horizontal column coordinates
            nodes_map[v].x = nodes_map[u].x + random.uniform(-5.0, 5.0)
            nodes_map[v].y = nodes_map[u].y + random.uniform(-5.0, 5.0)
            etype = "s" if random.random() < 0.7 else "l"
            cost = 12.0 if etype == "s" else 8.0
        else:
            etype = "w"
            dist_px = math.hypot(nodes_map[u].x - nodes_map[v].x, nodes_map[u].y - nodes_map[v].y)
            cost = max(2.0, dist_px * 0.1)
        edges.append(CampusEdge(a=u, b=v, type=etype, cost=cost, accessible=(etype != "s"), outdoor=False))

    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            u = f"N{i}"
            v = f"N{j}"
            if (min(u, v), max(u, v)) not in edge_set and random.random() < edge_prob:
                is_cross = nodes_map[u].level != nodes_map[v].level
                if is_cross:
                    # Only connect cross-level if already close in (x, y) column
                    dist_col = math.hypot(nodes_map[u].x - nodes_map[v].x, nodes_map[u].y - nodes_map[v].y)
                    if dist_col > 30.0:
                        continue
                    edge_set.add((min(u, v), max(u, v)))
                    etype = "s" if random.random() < 0.7 else "l"
                    cost = 12.0 if etype == "s" else 8.0
                else:
                    edge_set.add((min(u, v), max(u, v)))
                    etype = "w"
                    dist_px = math.hypot(nodes_map[u].x - nodes_map[v].x, nodes_map[u].y - nodes_map[v].y)
                    cost = max(2.0, dist_px * 0.1)
                edges.append(CampusEdge(a=u, b=v, type=etype, cost=cost, accessible=(etype != "s"), outdoor=False))

    graph_data = CampusGraphData(
        costModel=CostModel(campus=0.25, int=0.1, stair=12.0, lift=8.0, door=4.0),
        nodes=nodes,
        edges=edges
    )
    return graph_data

def test_optimal_algorithms_exact_cost_agreement():
    """All optimal algorithms (Dijkstra, A*, ALT, Bidirectional) must agree on exact cost."""
    graph_data = build_random_connected_graph(num_nodes=20, edge_prob=0.3, seed=123)
    router = CampusRouter(graph_data)
    node_ids = [n.id for n in graph_data.nodes]

    # Test across 50 random node pairs
    random.seed(999)
    for _ in range(50):
        src = random.choice(node_ids)
        dst = random.choice(node_ids)

        r_dijk = router.dijkstra(src, dst)
        r_astar = router.astar(src, dst)
        r_alt = router.alt(src, dst)
        r_bidi = router.bidirectional_dijkstra(src, dst)

        assert r_dijk is not None
        assert r_astar is not None
        assert r_alt is not None
        assert r_bidi is not None

        c_dijk = r_dijk.total_s
        c_astar = r_astar.total_s
        c_alt = r_alt.total_s
        c_bidi = r_bidi.total_s

        assert abs(c_dijk - c_astar) < 1e-4, f"Dijkstra vs A* mismatch: {c_dijk} vs {c_astar}"
        assert abs(c_dijk - c_alt) < 1e-4, f"Dijkstra vs ALT mismatch: {c_dijk} vs {c_alt}"
        assert abs(c_dijk - c_bidi) < 1e-4, f"Dijkstra vs Bidirectional mismatch: {c_dijk} vs {c_bidi}"

def test_cross_check_with_networkx():
    """Verify Dijkstra and BFS against NetworkX reference implementations."""
    graph_data = build_random_connected_graph(num_nodes=22, edge_prob=0.35, seed=456)
    router = CampusRouter(graph_data)

    # Build networkx graph
    G = nx.Graph()
    for n in graph_data.nodes:
        G.add_node(n.id)
    for u, neighbors in router.adj.items():
        for v, edge, t_s, _ in neighbors:
            if not G.has_edge(u, v):
                G.add_edge(u, v, weight=t_s)

    node_ids = [n.id for n in graph_data.nodes]
    random.seed(777)
    for _ in range(30):
        src = random.choice(node_ids)
        dst = random.choice(node_ids)

        # 1. Dijkstra cost matches NetworkX
        nx_len = nx.dijkstra_path_length(G, src, dst, weight="weight")
        my_res = router.dijkstra(src, dst)
        assert abs(my_res.total_s - nx_len) < 1e-4, f"NetworkX parity failure: {my_res.total_s} vs {nx_len}"

        # 2. BFS hops matches NetworkX shortest_path_length unweighted
        nx_hops = nx.shortest_path_length(G, src, dst)
        my_bfs = router.bfs(src, dst)
        my_hops = len(my_bfs.path) - 1
        assert my_hops == nx_hops, f"BFS hop mismatch: {my_hops} vs {nx_hops}"

def test_metric_symmetry_and_triangle_inequality():
    """Verify symmetry and triangle inequality: d(u, v) <= d(u, w) + d(w, v)."""
    graph_data = build_random_connected_graph(num_nodes=18, edge_prob=0.3, seed=789)
    router = CampusRouter(graph_data)
    node_ids = [n.id for n in graph_data.nodes]

    random.seed(888)
    for _ in range(30):
        u, v, w = random.sample(node_ids, 3)

        d_uv = router.dijkstra(u, v).total_s
        d_vu = router.dijkstra(v, u).total_s
        assert abs(d_uv - d_vu) < 1e-4, f"Symmetry violated: d({u},{v})={d_uv} != d({v},{u})={d_vu}"

        d_uw = router.dijkstra(u, w).total_s
        d_wv = router.dijkstra(w, v).total_s
        assert d_uv <= d_uw + d_wv + 1e-4, f"Triangle inequality violated: {d_uv} > {d_uw} + {d_wv}"

def test_wheelchair_accessibility_strict_exclusion():
    """Wheelchair mode must strictly forbid stairs and reroute or return None."""
    graph_data = build_random_connected_graph(num_nodes=20, edge_prob=0.35, seed=101)
    router = CampusRouter(graph_data)
    profile = RoutingProfile(wheelchair=True)

    node_ids = [n.id for n in graph_data.nodes]
    for _ in range(20):
        src = random.choice(node_ids)
        dst = random.choice(node_ids)
        res = router.dijkstra(src, dst, profile)
        if res:
            for edge in res.edges:
                assert edge["type"] != "s", f"Wheelchair route traversed stairs edge {edge['a']}-{edge['b']}"

def test_yen_k_shortest_monotonic_costs():
    """Yen's algorithm must return distinct loopless paths with non-decreasing costs."""
    graph_data = build_random_connected_graph(num_nodes=18, edge_prob=0.4, seed=202)
    router = CampusRouter(graph_data)
    node_ids = [n.id for n in graph_data.nodes]

    src, dst = random.sample(node_ids, 2)
    alts = router.k_shortest_paths(src, dst, k=3)
    assert len(alts) >= 1
    costs = [r.total_s for r in alts]
    for i in range(len(costs) - 1):
        assert costs[i] <= costs[i + 1] + 1e-4, f"Yen paths not sorted: {costs}"

def test_nearest_x_target_search():
    """Nearest-X returns the closest target node of the given category."""
    graph_data = build_random_connected_graph(num_nodes=20, edge_prob=0.35, seed=303)
    router = CampusRouter(graph_data)

    res = router.nearest_x("N0", "s")
    if res:
        assert res.path[0] == "N0"
        target = res.path[-1]
        assert router.nodes_map[target].type == "s"

@settings(max_examples=25, deadline=None)
@given(
    seed=st.integers(min_value=1, max_value=10000),
    num_nodes=st.integers(min_value=8, max_value=25)
)
def test_hypothesis_random_graph_parity(seed, num_nodes):
    """Hypothesis property test: On arbitrary random connected graphs, Dijkstra and A* must match exact cost."""
    graph_data = build_random_connected_graph(num_nodes=num_nodes, edge_prob=0.35, seed=seed)
    router = CampusRouter(graph_data)
    node_ids = [n.id for n in graph_data.nodes]

    src = node_ids[0]
    dst = node_ids[-1]

    r1 = router.dijkstra(src, dst)
    r2 = router.astar(src, dst)
    r3 = router.bidirectional_dijkstra(src, dst)

    assert r1 is not None and r2 is not None and r3 is not None
    assert abs(r1.total_s - r2.total_s) < 1e-4
    assert abs(r1.total_s - r3.total_s) < 1e-4
