import pytest
import math
from campus_navigation.models import (
    CampusGraphData, CampusNode, CampusEdge, CampusRoom, CostModel
)
from campus_navigation.algorithms import CampusRouter, RoutingOptions
from campus_navigation.networkx_verifier import NetworkXVerifier

@pytest.fixture
def campus_graph():
    return CampusGraphData.load_from_file("campus-graph.json")

@pytest.fixture
def router(campus_graph):
    return CampusRouter(campus_graph)

@pytest.fixture
def nx_verifier(campus_graph):
    return NetworkXVerifier(campus_graph)

# ==========================================
# 1. Pydantic Schema & Integrity Tests
# ==========================================

def test_graph_integrity_valid(campus_graph):
    assert len(campus_graph.nodes) == 82
    assert len(campus_graph.edges) == 87
    assert len(campus_graph.rooms) == 51
    assert campus_graph.costModel.campus == 0.25
    assert campus_graph.costModel.int_ == 0.1

def test_duplicate_node_id_validation():
    cm = CostModel(campus=0.25, int=0.1, stair=12.0, lift=8.0, door=4.0)
    nodes = [
        CampusNode(id="A", label="Node A", level="c", x=0, y=0, type="p"),
        CampusNode(id="A", label="Duplicate A", level="c", x=10, y=10, type="p")
    ]
    edges = [CampusEdge(a="A", b="A", type="w", cost=1.0, accessible=True, outdoor=True)]
    with pytest.raises(ValueError, match="Duplicate node ID"):
        CampusGraphData(costModel=cm, nodes=nodes, edges=edges)

def test_dangling_edge_validation():
    cm = CostModel(campus=0.25, int=0.1, stair=12.0, lift=8.0, door=4.0)
    nodes = [
        CampusNode(id="A", label="Node A", level="c", x=0, y=0, type="p")
    ]
    edges = [CampusEdge(a="A", b="NON_EXISTENT", type="w", cost=5.0, accessible=True, outdoor=True)]
    with pytest.raises(ValueError, match="Dangling edge endpoint"):
        CampusGraphData(costModel=cm, nodes=nodes, edges=edges)

def test_negative_cost_validation():
    from pydantic import ValidationError
    cm = CostModel(campus=0.25, int=0.1, stair=12.0, lift=8.0, door=4.0)
    nodes = [
        CampusNode(id="A", label="Node A", level="c", x=0, y=0, type="p"),
        CampusNode(id="B", label="Node B", level="c", x=10, y=10, type="p")
    ]
    with pytest.raises((ValueError, ValidationError)):
        edges = [CampusEdge(a="A", b="B", type="w", cost=-2.0, accessible=True, outdoor=True)]
        CampusGraphData(costModel=cm, nodes=nodes, edges=edges)

def test_disconnected_graph_validation():
    cm = CostModel(campus=0.25, int=0.1, stair=12.0, lift=8.0, door=4.0)
    nodes = [
        CampusNode(id="A", label="Node A", level="c", x=0, y=0, type="p"),
        CampusNode(id="B", label="Node B", level="c", x=10, y=10, type="p"),
        CampusNode(id="ISLAND", label="Island", level="c", x=100, y=100, type="p")
    ]
    edges = [CampusEdge(a="A", b="B", type="w", cost=1.0, accessible=True, outdoor=True)]
    with pytest.raises(ValueError, match="Graph is not connected"):
        CampusGraphData(costModel=cm, nodes=nodes, edges=edges)

# ==========================================
# 2. Shortest Path Correctness Tests
# ==========================================

def test_hand_checked_main_gate_to_lab_t3(router):
    # Route from Main gate (GATE) to Lab T3 (T3)
    res = router.dijkstra("GATE", "T3")
    assert res is not None
    assert res.path[0] == "GATE"
    assert res.path[-1] == "T3"
    assert res.total_cost > 0
    # Must enter VIT building through either door, stairs, or library portal
    assert any(portal in res.path for portal in ["VDA", "VDN", "MBD", "LIB", "LB"])

def test_dijkstra_astar_optimality_match(router):
    # Tested on diverse intra-level and cross-level pairs
    pairs = [
        ("GATE", "PARK"),
        ("GATE", "T3"),
        ("T1", "B7"),
        ("MC1", "LIB"),
        ("LIFT0", "AB"),
        ("FB", "CAN")
    ]
    for src, dst in pairs:
        r_dijkstra = router.dijkstra(src, dst)
        r_astar = router.astar(src, dst)
        assert r_dijkstra is not None
        assert r_astar is not None
        assert r_dijkstra.total_cost == pytest.approx(r_astar.total_cost, rel=1e-4)

def test_bidirectional_dijkstra_optimality_match(router):
    pairs = [
        ("GATE", "T3"),
        ("MC0", "EB"),
        ("PARK", "LB")
    ]
    for src, dst in pairs:
        r_dijkstra = router.dijkstra(src, dst)
        r_bidi = router.bidirectional_dijkstra(src, dst)
        assert r_dijkstra is not None
        assert r_bidi is not None
        assert r_dijkstra.total_cost == pytest.approx(r_bidi.total_cost, rel=1e-4)

def test_bfs_fewest_hops(router):
    res_bfs = router.bfs("GATE", "T3")
    res_dijk = router.dijkstra("GATE", "T3")
    assert res_bfs is not None
    assert len(res_bfs.path) <= len(res_dijk.path)

# ==========================================
# 3. Routing Constraints & Options Tests
# ==========================================

def test_accessible_only_uses_lift_not_stairs(router):
    # From basement (LIFT0) to floor 1 (MC1 or LIFT1)
    res_standard = router.dijkstra("LIFT0", "MC1")
    opt_acc = RoutingOptions(accessible_only=True)
    res_acc = router.dijkstra("LIFT0", "MC1", opt_acc)

    assert res_acc is not None
    # No stair edges in the accessible path
    for edge in res_acc.edges:
        assert edge["type"] != "s"
        assert edge["accessible"] is True

    # Must cross levels via the elevator lift
    assert "LIFT0" in res_acc.path
    assert "LIFT1" in res_acc.path

def test_avoid_stairs_penalty(router):
    # Test path that would normally use stairs
    opt_normal = RoutingOptions(avoid_stairs=False)
    opt_avoid = RoutingOptions(avoid_stairs=True, stairs_penalty=4.0)

    # SA0 to S1A is direct stairs (cost 12)
    res_normal = router.dijkstra("SA0", "S1A", opt_normal)
    res_avoid = router.dijkstra("SA0", "S1A", opt_avoid)

    assert res_avoid.total_cost >= res_normal.total_cost

def test_prefer_indoor_penalty(router):
    opt_normal = RoutingOptions(prefer_indoor=False)
    opt_indoor = RoutingOptions(prefer_indoor=True, outdoor_penalty=3.0)

    res_normal = router.dijkstra("GATE", "FB", opt_normal)
    res_indoor = router.dijkstra("GATE", "FB", opt_indoor)

    assert res_indoor.total_cost >= res_normal.total_cost

def test_yen_k_shortest_paths(router):
    routes = router.k_shortest_paths("GATE", "T3", k=3)
    assert len(routes) >= 2
    # Check cost monotonic order
    for i in range(len(routes) - 1):
        assert routes[i].total_cost <= routes[i + 1].total_cost + 1e-4
    # All paths must be distinct
    path_tuples = [tuple(r.path) for r in routes]
    assert len(set(path_tuples)) == len(routes)

def test_multi_stop_tsp(router):
    stops = ["T3", "LIB", "MC1"]
    tsp_res = router.multi_stop_tsp("GATE", stops)

    assert tsp_res["visit_sequence"][0] == "GATE"
    assert set(stops).issubset(set(tsp_res["visit_sequence"]))
    assert len(tsp_res["legs"]) == len(stops)
    assert tsp_res["total_cost"] > 0
    assert len(tsp_res["full_path"]) > len(tsp_res["visit_sequence"])

# ==========================================
# 4. NetworkX Cross-Checking Tests
# ==========================================

def test_cross_check_with_networkx(router, nx_verifier):
    test_cases = [
        ("GATE", "T3", RoutingOptions()),
        ("GATE", "T3", RoutingOptions(avoid_stairs=True)),
        ("MC0", "LB", RoutingOptions(accessible_only=True)),
        ("R1", "NES", RoutingOptions(prefer_indoor=True)),
        ("PARK", "AUD", RoutingOptions())
    ]

    for src, dst, opt in test_cases:
        res_custom = router.dijkstra(src, dst, opt)
        nx_path, nx_cost = nx_verifier.shortest_path(src, dst, opt)

        if nx_path is None:
            assert res_custom is None
        else:
            assert res_custom is not None
            assert res_custom.total_cost == pytest.approx(nx_cost, rel=1e-4)

# ==========================================
# 5. Performance Budget Tests (< 5ms)
# ==========================================

def test_performance_budget_sub_5ms(router):
    import time
    iterations = 20
    t0 = time.perf_counter()
    for _ in range(iterations):
        router.dijkstra("GATE", "T3")
    elapsed_ms = ((time.perf_counter() - t0) / iterations) * 1000

    print(f"\nAverage Dijkstra query time: {elapsed_ms:.3f} ms")
    assert elapsed_ms < 5.0, f"Query took {elapsed_ms:.2f} ms, exceeding 5 ms budget"

# ==========================================
# 6. Floor 1 Blueprint Specific Navigation Tests
# ==========================================

def test_f1_room_a_to_room_b_walkway(router):
    res = router.dijkstra("AB", "BB")
    assert res is not None
    assert res.path[0] == "AB"
    assert res.path[-1] == "BB"
    # Route traverses walkway nodes N1_L -> N2_1 -> N3
    assert "N1_L" in res.path
    assert "N2_1" in res.path
    assert "N3" in res.path
    assert res.total_cost > 0

def test_f1_lab_to_mblock_stairs(router):
    res = router.dijkstra("LAB_COMP", "MC1")
    assert res is not None
    assert res.path[0] == "LAB_COMP"
    assert res.path[-1] == "MC1"
    assert "N2_1" in res.path
    assert "N_R_BEND" in res.path

def test_f1_library_stairs_cross_level_to_campus(router):
    # From Floor 1 Library stairs (LB) to Campus ground Library (LIB)
    res = router.dijkstra("LB", "LIB")
    assert res is not None
    assert res.path == ["LB", "LIB"]
    assert res.total_cost == pytest.approx(12.0)

def test_f1_accessible_route_from_lab_to_basement(router):
    # Wheelchair query from LAB_COMP to basement lab T1 must use LIFT1 -> LIFT0, never stairs
    opt_acc = RoutingOptions(accessible_only=True)
    res = router.dijkstra("LAB_COMP", "T1", opt_acc)
    assert res is not None
    assert "LIFT1" in res.path
    assert "LIFT0" in res.path
    for edge in res.edges:
        assert edge["accessible"] is True
        assert edge["type"] != "s"
