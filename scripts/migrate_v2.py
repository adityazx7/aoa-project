import json
import os
import math
from campus_navigation.models import CampusGraphData, CampusNode, CampusEdge, CampusRoom, CostModel
from campus_navigation.cost import CostConfig, compute_edge_metrics

def generate_v2():
    with open("campus-graph.json", "r", encoding="utf-8") as f:
        v1 = json.load(f)

    # Architectural landmarks for VIT campus
    landmarks_map = {
        "GATE": "Main Campus Security Gate",
        "VDA": "VIT Main Building Entrance (A-Block Wing)",
        "VDN": "VIT Building Secondary Entrance (Nescafe Wing)",
        "VPD": "VP College Connecting Door",
        "MBD": "M-Block Building Connection",
        "LIB": "Central Campus Library",
        "AUD": "Main Auditorium Foyer",
        "CAN": "Campus Canteen / Cafeteria",
        "PARK": "Student & Staff Parking Zone",
        "BBALL": "Outdoor Basketball Court",
        "FB": "Football & Sports Ground",
        "LIFT0": "Basement Lab Level Elevator",
        "LIFT1": "Ground Atrium Central Glass Elevator",
        "SA0": "Sunken Stairway to Computer Labs (West)",
        "S1A": "Main Atrium Stairwell (West)",
        "SB0": "Sunken Stairway to Basement Labs (Center)",
        "S1B": "Atrium Center Staircase",
        "SC0": "Stairwell C (Basement Lab Wing)",
        "S1C": "Atrium North Bridge Stairwell",
        "IL": "Innovation & Incubation Lab",
        "T1": "T-Block Classroom 101",
        "T3": "T-Block Seminar Hall",
        "B1": "Bio-Tech Lab 1",
        "B7": "Advanced Robotics & AI Lab",
        "MC1": "Main Walkway Atrium Center",
        "MC0": "Basement Central Hallway"
    }

    # Meta
    meta = {
        "origin": [19.0216, 72.8708],
        "rotation_deg": 0.0,
        "units": "m",
        "crs": "local_enu",
        "todo": True
    }

    levels = [
        {"id": "c", "name": "Campus Grounds", "z": 0.0},
        {"id": "f0", "name": "Basement Labs", "z": -4.5},
        {"id": "f1", "name": "Floor 1 Walkway / Atrium", "z": 0.0}
    ]

    zones = [
        {
            "id": "atrium_plaza",
            "name": "Central Covered Atrium Plaza",
            "level": "f1",
            "polygon": [[40.0, 20.0], [105.0, 20.0], [105.0, 60.0], [40.0, 60.0]],
            "walkable": True,
            "todo": True
        },
        {
            "id": "sunken_atrium_void",
            "name": "Sunken Stair Void to Lab Level",
            "level": "f1",
            "polygon": [[65.0, 28.0], [75.0, 28.0], [75.0, 38.0], [65.0, 38.0]],
            "walkable": False,
            "todo": True
        },
        {
            "id": "campus_parking",
            "name": "Vehicle Parking Area",
            "level": "c",
            "polygon": [[135.0, 25.0], [155.0, 25.0], [155.0, 40.0], [135.0, 40.0]],
            "walkable": True,
            "todo": True
        },
        {
            "id": "sports_ground",
            "name": "College Sports & Activity Field",
            "level": "c",
            "polygon": [[10.0, 10.0], [70.0, 10.0], [70.0, 35.0], [10.0, 35.0]],
            "walkable": True,
            "todo": True
        }
    ]

    # Portals
    portals = [
        {"id": "stairs_sa", "kind": "stairs", "between": ["SA0", "S1A"], "flights": 1, "accessible": False, "todo": False},
        {"id": "stairs_sb", "kind": "stairs", "between": ["SB0", "S1B"], "flights": 1, "accessible": False, "todo": False},
        {"id": "stairs_sc", "kind": "stairs", "between": ["SC0", "S1C"], "flights": 1, "accessible": False, "todo": False},
        {"id": "stairs_sd", "kind": "stairs", "between": ["SD0", "S1D"], "flights": 1, "accessible": False, "todo": False},
        {"id": "stairs_se", "kind": "stairs", "between": ["SE0", "S1E"], "flights": 1, "accessible": False, "todo": False},
        {"id": "lift_atrium", "kind": "lift", "between": ["LIFT0", "LIFT1"], "flights": 1, "accessible": True, "todo": False}
    ]

    v2_nodes = []
    nodes_lookup = {}
    for n in v1["nodes"]:
        lv = n["level"]
        scale = 0.18 if lv == "c" else 0.1
        z = 0.0 if lv in ("c", "f1") else -4.5
        x_m = round(n["x"] * scale, 2)
        y_m = round(n["y"] * scale, 2)

        kind_map = {
            "e": "entrance",
            "s": "stairs",
            "l": "lift",
            "j": "corridor",
            "p": "poi"
        }
        kind = kind_map.get(n.get("type", "p"), "poi")
        lm = landmarks_map.get(n["id"])

        node_obj = {
            "id": n["id"],
            "label": n["label"],
            "level": lv,
            "x": float(n["x"]),
            "y": float(n["y"]),
            "z": z,
            "xy": [x_m, y_m],
            "type": n.get("type", "p"),
            "kind": kind,
            "landmark": lm,
            "todo": True
        }
        v2_nodes.append(node_obj)
        nodes_lookup[n["id"]] = node_obj

    cost_cfg = CostConfig()
    v2_edges = []
    for e in v1["edges"]:
        na = nodes_lookup[e["a"]]
        nb = nodes_lookup[e["b"]]

        # Polyline corridor waypoints: [start_m, end_m] in metric coordinates
        path_coords = [na["xy"], nb["xy"]]
        dx = nb["xy"][0] - na["xy"][0]
        dy = nb["xy"][1] - na["xy"][1]
        dist_m = round(math.hypot(dx, dy), 2)
        if dist_m < 1.0:
            dist_m = 1.5

        etype = e.get("type", "w")
        is_outdoor = (na["level"] == "c" and nb["level"] == "c")

        # Metric times
        metrics = compute_edge_metrics(etype, dist_m, is_outdoor, cost_cfg)
        time_s = round(metrics["time_s"], 2)

        edge_kind = {
            "w": "walk",
            "b": "bridge",
            "s": "stairs",
            "l": "lift",
            "d": "door"
        }.get(etype, "walk")

        width_m = 1.8 if etype == "s" else (1.2 if etype == "d" else 3.0)

        v2_edges.append({
            "a": e["a"],
            "b": e["b"],
            "type": etype,
            "kind": edge_kind,
            "cost": time_s,
            "distance_m": dist_m,
            "time_s": time_s,
            "width_m": width_m,
            "accessible": (etype != "s"),
            "outdoor": is_outdoor,
            "path": path_coords,
            "todo": True
        })

    v2_rooms = []
    for r in v1.get("rooms", []):
        v2_rooms.append({
            "level": r["level"],
            "label": r.get("label", ""),
            "x": float(r["x"]),
            "y": float(r["y"]),
            "width": float(r["width"]),
            "height": float(r["height"]),
            "kind": r.get("kind", "room")
        })

    v2_graph = {
        "meta": meta,
        "costModel": {
            "campus": 0.25,
            "int": 0.1,
            "stair": 12.0,
            "lift": 8.0,
            "door": 4.0
        },
        "levels": levels,
        "zones": zones,
        "portals": portals,
        "nodes": v2_nodes,
        "edges": v2_edges,
        "rooms": v2_rooms
    }

    # Validate using Pydantic model
    validated = CampusGraphData(**v2_graph)
    os.makedirs("data", exist_ok=True)
    with open("data/campus.v2.json", "w", encoding="utf-8") as out_f:
        json.dump(v2_graph, out_f, indent=2)

    print(f"Successfully generated data/campus.v2.json:")
    print(f"- Nodes: {len(validated.nodes)}")
    print(f"- Edges: {len(validated.edges)}")
    print(f"- Rooms: {len(validated.rooms)}")
    print(f"- Portals: {len(validated.portals)}")
    print(f"- Zones: {len(validated.zones)}")

if __name__ == "__main__":
    generate_v2()
