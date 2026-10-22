import json
import os
import math
from campus_navigation.models import CampusGraphData, CampusNode, CampusEdge, CampusRoom, CostModel

def update_f1_floor_plan():
    with open("data/campus.v2.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Preserve campus ('c') and basement ('f0') nodes
    c_nodes = [n for n in data["nodes"] if n["level"] == "c"]
    f0_nodes = [n for n in data["nodes"] if n["level"] == "f0"]

    # 2. Define the ACCURATE new Floor 1 ('f1') nodes based on user's diagram
    # Walkway spine runs along y = 420
    # West Entry (EA) at bottom left, East Entry (EN) at bottom right
    f1_nodes = [
        # --- Endpoints & Rooms ---
        {
            "id": "AB",
            "label": "Room A",
            "level": "f1",
            "x": 140.0, "y": 320.0, "z": 0.0, "xy": [14.0, 32.0],
            "type": "p", "kind": "entrance", "landmark": "Classroom A Wing", "todo": False
        },
        {
            "id": "EA",
            "label": "West Entry (Opp. A Block)",
            "level": "f1",
            "x": 140.0, "y": 700.0, "z": 0.0, "xy": [14.0, 70.0],
            "type": "e", "kind": "entrance", "landmark": "West Campus Entry Door", "todo": False
        },
        {
            "id": "ENTRY_L",
            "label": "West Entry Portal",
            "level": "f1",
            "x": 140.0, "y": 710.0, "z": 0.0, "xy": [14.0, 71.0],
            "type": "e", "kind": "entrance", "landmark": "West Campus Entry Doorway", "todo": False
        },
        {
            "id": "LAB_COMP",
            "label": "LaB computer",
            "level": "f1",
            "x": 300.0, "y": 520.0, "z": 0.0, "xy": [30.0, 52.0],
            "type": "p", "kind": "entrance", "landmark": "Computer Department Labs", "todo": False
        },
        {
            "id": "S1A",
            "label": "Faculty (Stairs to Labs)",
            "level": "f1",
            "x": 420.0, "y": 320.0, "z": 0.0, "xy": [42.0, 32.0],
            "type": "s", "kind": "stairs", "landmark": "Faculty West Stairwell (Down to SA0)", "todo": False
        },
        {
            "id": "FAC_W",
            "label": "Faculty (West)",
            "level": "f1",
            "x": 420.0, "y": 240.0, "z": 0.0, "xy": [42.0, 24.0],
            "type": "p", "kind": "entrance", "landmark": "West Faculty Workstations", "todo": False
        },
        {
            "id": "BB",
            "label": "Room B",
            "level": "f1",
            "x": 540.0, "y": 320.0, "z": 0.0, "xy": [54.0, 32.0],
            "type": "p", "kind": "entrance", "landmark": "Classroom B Wing", "todo": False
        },
        {
            "id": "LB",
            "label": "library stairs",
            "level": "f1",
            "x": 470.0, "y": 520.0, "z": 0.0, "xy": [47.0, 52.0],
            "type": "s", "kind": "stairs", "landmark": "Library Staircase (Down to Campus Library)", "todo": False
        },
        {
            "id": "FAC_MID",
            "label": "Faculty Staff Room (Center)",
            "level": "f1",
            "x": 640.0, "y": 520.0, "z": 0.0, "xy": [64.0, 52.0],
            "type": "p", "kind": "entrance", "landmark": "Central Faculty Workstations", "todo": False
        },
        {
            "id": "CAN",
            "label": "Canteen (1st Floor)",
            "level": "f1",
            "x": 745.0, "y": 320.0, "z": 0.0, "xy": [74.5, 32.0],
            "type": "p", "kind": "entrance", "landmark": "1F Walkway Canteen Threshold", "todo": False
        },
        {
            "id": "CANT",
            "label": "Canteen Counter",
            "level": "f1",
            "x": 750.0, "y": 280.0, "z": 0.0, "xy": [75.0, 28.0],
            "type": "p", "kind": "poi", "landmark": "Canteen Food Order Counter", "todo": False
        },
        {
            "id": "EB",
            "label": "Classroom (Center-South)",
            "level": "f1",
            "x": 815.0, "y": 520.0, "z": 0.0, "xy": [81.5, 52.0],
            "type": "p", "kind": "entrance", "landmark": "Center South Classroom Wing (E Block)", "todo": False
        },
        {
            "id": "FAC_TOP_R",
            "label": "Faculty (North-East)",
            "level": "f1",
            "x": 920.0, "y": 320.0, "z": 0.0, "xy": [92.0, 32.0],
            "type": "p", "kind": "entrance", "landmark": "North-East Faculty Cabins", "todo": False
        },
        {
            "id": "EN",
            "label": "East Entry (Opp. Canteen/Nescafe)",
            "level": "f1",
            "x": 910.0, "y": 700.0, "z": 0.0, "xy": [91.0, 70.0],
            "type": "e", "kind": "entrance", "landmark": "East Campus Entry Door", "todo": False
        },
        {
            "id": "ENTRY_R",
            "label": "East Entry Portal",
            "level": "f1",
            "x": 910.0, "y": 710.0, "z": 0.0, "xy": [91.0, 71.0],
            "type": "e", "kind": "entrance", "landmark": "East Campus Entry Doorway", "todo": False
        },
        {
            "id": "WASHROOM",
            "label": "Washroom",
            "level": "f1",
            "x": 1030.0, "y": 180.0, "z": 0.0, "xy": [103.0, 18.0],
            "type": "p", "kind": "poi", "landmark": "1F Restrooms", "todo": False
        },
        {
            "id": "CLASS_TR",
            "label": "Classroom (Top-Right)",
            "level": "f1",
            "x": 1100.0, "y": 200.0, "z": 0.0, "xy": [110.0, 20.0],
            "type": "p", "kind": "entrance", "landmark": "Top Right Classroom", "todo": False
        },
        {
            "id": "MC1",
            "label": "into m block (Stairs)",
            "level": "f1",
            "x": 1100.0, "y": 330.0, "z": 0.0, "xy": [110.0, 33.0],
            "type": "s", "kind": "stairs", "landmark": "Covered Bridge Stairway to M Block", "todo": False
        },
        {
            "id": "STAIRS_CANTEEN",
            "label": "down to canteen (Stairs)",
            "level": "f1",
            "x": 1100.0, "y": 450.0, "z": 0.0, "xy": [110.0, 45.0],
            "type": "s", "kind": "stairs", "landmark": "Stairs Down to Ground Canteen", "todo": False
        },
        {
            "id": "STATIONS",
            "label": "Stations",
            "level": "f1",
            "x": 1030.0, "y": 490.0, "z": 0.0, "xy": [103.0, 49.0],
            "type": "p", "kind": "poi", "landmark": "Student Workstation Counter", "todo": False
        },
        {
            "id": "NES",
            "label": "Nescafe / Stations Kiosk",
            "level": "f1",
            "x": 1030.0, "y": 520.0, "z": 0.0, "xy": [103.0, 52.0],
            "type": "p", "kind": "poi", "landmark": "Refreshments & Snacks Kiosk", "todo": False
        },
        {
            "id": "FAC_BOT_R",
            "label": "Faculty (South-East)",
            "level": "f1",
            "x": 980.0, "y": 580.0, "z": 0.0, "xy": [98.0, 58.0],
            "type": "p", "kind": "entrance", "landmark": "South-East Faculty Staff Room", "todo": False
        },
        {
            "id": "CLASS_BR1",
            "label": "Classroom (East Wing 1)",
            "level": "f1",
            "x": 1150.0, "y": 580.0, "z": 0.0, "xy": [115.0, 58.0],
            "type": "p", "kind": "entrance", "landmark": "East Wing Classroom 1", "todo": False
        },
        {
            "id": "CLASS_BR2",
            "label": "Classroom (East Wing 2)",
            "level": "f1",
            "x": 1150.0, "y": 665.0, "z": 0.0, "xy": [115.0, 66.5],
            "type": "p", "kind": "entrance", "landmark": "East Wing Classroom 2", "todo": False
        },
        {
            "id": "LIFT1",
            "label": "Central Elevator (1F)",
            "level": "f1",
            "x": 380.0, "y": 420.0, "z": 0.0, "xy": [38.0, 42.0],
            "type": "l", "kind": "lift", "landmark": "Atrium Central Glass Elevator", "todo": False
        },

        # --- Walkway Circular Junctions (Labeled in Diagram) ---
        {
            "id": "N1_L",
            "label": "Walkway N1 (West)",
            "level": "f1",
            "x": 140.0, "y": 420.0, "z": 0.0, "xy": [14.0, 42.0],
            "type": "j", "kind": "corridor", "landmark": "West Corridor Junction N1", "todo": False
        },
        {
            "id": "N2_1",
            "label": "Walkway N2 (Lab)",
            "level": "f1",
            "x": 300.0, "y": 420.0, "z": 0.0, "xy": [30.0, 42.0],
            "type": "j", "kind": "corridor", "landmark": "Computer Lab Junction N2", "todo": False
        },
        {
            "id": "N3",
            "label": "Walkway N3 (Central Hub)",
            "level": "f1",
            "x": 470.0, "y": 420.0, "z": 0.0, "xy": [47.0, 42.0],
            "type": "j", "kind": "corridor", "landmark": "Central Atrium 5-Way Hub N3", "todo": False
        },
        {
            "id": "N2_2",
            "label": "Walkway N2 (Center)",
            "level": "f1",
            "x": 640.0, "y": 420.0, "z": 0.0, "xy": [64.0, 42.0],
            "type": "j", "kind": "corridor", "landmark": "Faculty Walkway Junction N2", "todo": False
        },
        {
            "id": "N4",
            "label": "Walkway N4 (Class)",
            "level": "f1",
            "x": 815.0, "y": 420.0, "z": 0.0, "xy": [81.5, 42.0],
            "type": "j", "kind": "corridor", "landmark": "Classroom Walkway Junction N4", "todo": False
        },
        {
            "id": "N2_3",
            "label": "Walkway N2 (East)",
            "level": "f1",
            "x": 920.0, "y": 420.0, "z": 0.0, "xy": [92.0, 42.0],
            "type": "j", "kind": "corridor", "landmark": "East Walkway Junction N2", "todo": False
        },
        {
            "id": "N_R_BEND",
            "label": "Right Walkway Junction",
            "level": "f1",
            "x": 1030.0, "y": 420.0, "z": 0.0, "xy": [103.0, 42.0],
            "type": "j", "kind": "corridor", "landmark": "East Corridor Transition Area", "todo": False
        },
        {
            "id": "N_R_NORTH",
            "label": "North-East Corridor Bend",
            "level": "f1",
            "x": 1030.0, "y": 200.0, "z": 0.0, "xy": [103.0, 20.0],
            "type": "j", "kind": "corridor", "landmark": "Restroom & Classroom Corridor", "todo": False
        }
    ]

    all_nodes = c_nodes + f0_nodes + f1_nodes

    # 3. Define the ACCURATE new Floor 1 ('f1') Edges with exact labeled distances
    f1_edges = [
        # Room A <-> N1 (diagram: c=1.5)
        {"a": "AB", "b": "N1_L", "type": "w", "kind": "walk", "distance_m": 15.0, "time_s": 11.5, "accessible": True, "outdoor": False},
        # West Entry <-> N1 (diagram: 15m)
        {"a": "EA", "b": "N1_L", "type": "w", "kind": "walk", "distance_m": 15.0, "time_s": 11.5, "accessible": True, "outdoor": False},
        # West Entry Portal <-> West Entry
        {"a": "ENTRY_L", "b": "EA", "type": "w", "kind": "walk", "distance_m": 1.0, "time_s": 0.8, "accessible": True, "outdoor": False},
        # Faculty West Office <-> Faculty Stairs
        {"a": "FAC_W", "b": "S1A", "type": "w", "kind": "walk", "distance_m": 10.0, "time_s": 7.7, "accessible": True, "outdoor": False},
        # N1 <-> N2 (diagram: 30m)
        {"a": "N1_L", "b": "N2_1", "type": "w", "kind": "walk", "distance_m": 30.0, "time_s": 23.1, "accessible": True, "outdoor": False},
        # N2 <-> LaB computer (diagram: 35m)
        {"a": "N2_1", "b": "LAB_COMP", "type": "w", "kind": "walk", "distance_m": 35.0, "time_s": 26.9, "accessible": True, "outdoor": False},
        # N2 <-> Central Elevator LIFT1
        {"a": "N2_1", "b": "LIFT1", "type": "w", "kind": "walk", "distance_m": 8.0, "time_s": 6.2, "accessible": True, "outdoor": False},
        # Central Elevator LIFT1 <-> N3
        {"a": "LIFT1", "b": "N3", "type": "w", "kind": "walk", "distance_m": 9.0, "time_s": 6.9, "accessible": True, "outdoor": False},
        # N3 <-> Faculty stairs S1A (diagram: 20m)
        {"a": "N3", "b": "S1A", "type": "w", "kind": "walk", "distance_m": 20.0, "time_s": 15.4, "accessible": True, "outdoor": False},
        # N3 <-> Room B (diagram: 15m)
        {"a": "N3", "b": "BB", "type": "w", "kind": "walk", "distance_m": 15.0, "time_s": 11.5, "accessible": True, "outdoor": False},
        # N3 <-> Library stairs LB (diagram: c=1m / 15m)
        {"a": "N3", "b": "LB", "type": "w", "kind": "walk", "distance_m": 15.0, "time_s": 11.5, "accessible": True, "outdoor": False},
        # N3 <-> N2 (diagram: c=1.5 / ~25m)
        {"a": "N3", "b": "N2_2", "type": "w", "kind": "walk", "distance_m": 25.0, "time_s": 19.2, "accessible": True, "outdoor": False},
        # N2 <-> Faculty center (diagram: 35m)
        {"a": "N2_2", "b": "FAC_MID", "type": "w", "kind": "walk", "distance_m": 35.0, "time_s": 26.9, "accessible": True, "outdoor": False},
        # N2 <-> Canteen entrance
        {"a": "N2_2", "b": "CAN", "type": "w", "kind": "walk", "distance_m": 15.0, "time_s": 11.5, "accessible": True, "outdoor": False},
        # Canteen entrance <-> Canteen Counter
        {"a": "CAN", "b": "CANT", "type": "w", "kind": "walk", "distance_m": 4.0, "time_s": 3.0, "accessible": True, "outdoor": False},
        # N2 <-> N4 (diagram: 35m)
        {"a": "N2_2", "b": "N4", "type": "w", "kind": "walk", "distance_m": 35.0, "time_s": 26.9, "accessible": True, "outdoor": False},
        # N4 <-> Class center EB (diagram: 15m)
        {"a": "N4", "b": "EB", "type": "w", "kind": "walk", "distance_m": 15.0, "time_s": 11.5, "accessible": True, "outdoor": False},
        # N4 <-> N2 (east)
        {"a": "N4", "b": "N2_3", "type": "w", "kind": "walk", "distance_m": 18.0, "time_s": 13.8, "accessible": True, "outdoor": False},
        # N2 <-> Faculty north-east (diagram: 15m)
        {"a": "N2_3", "b": "FAC_TOP_R", "type": "w", "kind": "walk", "distance_m": 15.0, "time_s": 11.5, "accessible": True, "outdoor": False},
        # N2 <-> Faculty south-east (diagram: 15m south line)
        {"a": "N2_3", "b": "FAC_BOT_R", "type": "w", "kind": "walk", "distance_m": 18.0, "time_s": 13.8, "accessible": True, "outdoor": False},
        # N2 <-> East Entry EN (diagram: right entry)
        {"a": "N2_3", "b": "EN", "type": "w", "kind": "walk", "distance_m": 25.0, "time_s": 19.2, "accessible": True, "outdoor": False},
        # East Entry Portal <-> East Entry
        {"a": "ENTRY_R", "b": "EN", "type": "w", "kind": "walk", "distance_m": 1.0, "time_s": 0.8, "accessible": True, "outdoor": False},
        # N2 <-> Right bend (diagram: 20m)
        {"a": "N2_3", "b": "N_R_BEND", "type": "w", "kind": "walk", "distance_m": 20.0, "time_s": 15.4, "accessible": True, "outdoor": False},
        # Right bend <-> North bend
        {"a": "N_R_BEND", "b": "N_R_NORTH", "type": "w", "kind": "walk", "distance_m": 18.0, "time_s": 13.8, "accessible": True, "outdoor": False},
        # North bend <-> Washroom
        {"a": "N_R_NORTH", "b": "WASHROOM", "type": "d", "kind": "door", "distance_m": 8.0, "time_s": 6.2, "accessible": True, "outdoor": False},
        # North bend <-> Classroom (Top-Right)
        {"a": "N_R_NORTH", "b": "CLASS_TR", "type": "d", "kind": "door", "distance_m": 10.0, "time_s": 7.7, "accessible": True, "outdoor": False},
        # Right bend <-> M-Block Stairs (diagram: into m block)
        {"a": "N_R_BEND", "b": "MC1", "type": "w", "kind": "walk", "distance_m": 12.0, "time_s": 9.2, "accessible": True, "outdoor": False},
        # Right bend <-> Canteen Stairs (diagram: down to canteen)
        {"a": "N_R_BEND", "b": "STAIRS_CANTEEN", "type": "w", "kind": "walk", "distance_m": 12.0, "time_s": 9.2, "accessible": True, "outdoor": False},
        # Right bend <-> Stations
        {"a": "N_R_BEND", "b": "STATIONS", "type": "w", "kind": "walk", "distance_m": 10.0, "time_s": 7.7, "accessible": True, "outdoor": False},
        # Stations <-> Nescafe Kiosk
        {"a": "STATIONS", "b": "NES", "type": "w", "kind": "walk", "distance_m": 3.0, "time_s": 2.3, "accessible": True, "outdoor": False},
        # Right bend <-> Faculty south-east
        {"a": "N_R_BEND", "b": "FAC_BOT_R", "type": "w", "kind": "walk", "distance_m": 12.0, "time_s": 9.2, "accessible": True, "outdoor": False},
        # Right bend <-> Classroom BR1
        {"a": "N_R_BEND", "b": "CLASS_BR1", "type": "d", "kind": "door", "distance_m": 16.0, "time_s": 12.3, "accessible": True, "outdoor": False},
        # Classroom BR1 <-> Classroom BR2
        {"a": "CLASS_BR1", "b": "CLASS_BR2", "type": "w", "kind": "walk", "distance_m": 10.0, "time_s": 7.7, "accessible": True, "outdoor": False},

        # --- Cross-Level Transition Portals ---
        # 1. Library Stairs <-> Library (LB on f1 <-> LIB on campus ground c)
        {"a": "LB", "b": "LIB", "type": "s", "kind": "stairs", "distance_m": 12.0, "time_s": 12.0, "accessible": False, "outdoor": False},
        # 2. Stairs A <-> SA0 (Basement Computer Labs)
        {"a": "S1A", "b": "SA0", "type": "s", "kind": "stairs", "distance_m": 12.0, "time_s": 12.0, "accessible": False, "outdoor": False},
        # 3. Lift 1F <-> Lift Basement
        {"a": "LIFT1", "b": "LIFT0", "type": "l", "kind": "lift", "distance_m": 4.5, "time_s": 8.0, "accessible": True, "outdoor": False},
        # 4. Into M Block stairs <-> M Block door (campus)
        {"a": "MC1", "b": "MBD", "type": "s", "kind": "stairs", "distance_m": 12.0, "time_s": 12.0, "accessible": False, "outdoor": True},
        # 5. Down to canteen stairs <-> Ground canteen / Basement (MC0)
        {"a": "STAIRS_CANTEEN", "b": "MC0", "type": "s", "kind": "stairs", "distance_m": 10.0, "time_s": 12.0, "accessible": False, "outdoor": False},
        # 6. West Entry <-> VDA (Campus door)
        {"a": "EA", "b": "VDA", "type": "d", "kind": "door", "distance_m": 5.0, "time_s": 4.0, "accessible": True, "outdoor": True},
        # 7. East Entry <-> VDN (Campus door)
        {"a": "EN", "b": "VDN", "type": "d", "kind": "door", "distance_m": 5.0, "time_s": 4.0, "accessible": True, "outdoor": True}
    ]

    # Preserve campus ('c') and basement ('f0') internal edges
    c_f0_edges = [
        e for e in data["edges"]
        if not (any(n["id"] in (e["a"], e["b"]) for n in data["nodes"] if n["level"] == "f1"))
    ]

    # Precompute edge costs and polylines for new f1 edges
    node_coords = {n["id"]: n for n in all_nodes}
    for e in f1_edges:
        e["cost"] = e["time_s"]
        e["width_m"] = 1.8 if e["type"] == "s" else (1.2 if e["type"] == "d" else 3.0)
        na = node_coords[e["a"]]
        nb = node_coords[e["b"]]
        e["path"] = [na["xy"], nb["xy"]]
        e["todo"] = False

    all_edges = c_f0_edges + f1_edges

    # 4. Rooms: Keep campus and basement rooms, replace f1 rooms
    c_f0_rooms = [r for r in data["rooms"] if r["level"] != "f1"]
    new_f1_rooms = [
        # Top Row Rooms
        {"level": "f1", "label": "Room A", "x": 80.0, "y": 100.0, "width": 240.0, "height": 220.0, "kind": "class"},
        {"level": "f1", "label": "Faculty", "x": 340.0, "y": 100.0, "width": 160.0, "height": 220.0, "kind": "faculty"},
        {"level": "f1", "label": "Room B", "x": 520.0, "y": 100.0, "width": 100.0, "height": 220.0, "kind": "class"},
        {"level": "f1", "label": "Canteen", "x": 640.0, "y": 100.0, "width": 210.0, "height": 220.0, "kind": "canteen"},
        {"level": "f1", "label": "Faculty", "x": 870.0, "y": 100.0, "width": 110.0, "height": 220.0, "kind": "faculty"},
        {"level": "f1", "label": "Washroom", "x": 1000.0, "y": 100.0, "width": 80.0, "height": 100.0, "kind": "washroom"},
        {"level": "f1", "label": "Classroom", "x": 1100.0, "y": 100.0, "width": 150.0, "height": 150.0, "kind": "class"},
        # Right Stairs Block
        {"level": "f1", "label": "Stairs: M-Block & Canteen", "x": 1090.0, "y": 260.0, "width": 160.0, "height": 240.0, "kind": "stair"},
        # Bottom Row Rooms
        {"level": "f1", "label": "Computer Lab", "x": 190.0, "y": 520.0, "width": 210.0, "height": 190.0, "kind": "lab"},
        {"level": "f1", "label": "Library Stairs", "x": 420.0, "y": 520.0, "width": 110.0, "height": 190.0, "kind": "stair"},
        {"level": "f1", "label": "Faculty", "x": 550.0, "y": 520.0, "width": 180.0, "height": 190.0, "kind": "faculty"},
        {"level": "f1", "label": "Classroom", "x": 750.0, "y": 520.0, "width": 130.0, "height": 190.0, "kind": "class"},
        {"level": "f1", "label": "Stations", "x": 980.0, "y": 480.0, "width": 100.0, "height": 55.0, "kind": "room"},
        {"level": "f1", "label": "Faculty", "x": 980.0, "y": 550.0, "width": 150.0, "height": 160.0, "kind": "faculty"},
        {"level": "f1", "label": "Classroom", "x": 1150.0, "y": 550.0, "width": 100.0, "height": 75.0, "kind": "class"},
        {"level": "f1", "label": "Classroom", "x": 1150.0, "y": 635.0, "width": 100.0, "height": 75.0, "kind": "class"},
    ]
    all_rooms = c_f0_rooms + new_f1_rooms

    # 5. Portals list
    portals = [
        {"id": "stairs_sa", "kind": "stairs", "between": ["SA0", "S1A"], "flights": 1, "accessible": False, "todo": False},
        {"id": "stairs_lib", "kind": "stairs", "between": ["LB", "LIB"], "flights": 1, "accessible": False, "todo": False},
        {"id": "stairs_mblock", "kind": "stairs", "between": ["MC1", "MBD"], "flights": 1, "accessible": False, "todo": False},
        {"id": "stairs_canteen", "kind": "stairs", "between": ["STAIRS_CANTEEN", "MC0"], "flights": 1, "accessible": False, "todo": False},
        {"id": "lift_atrium", "kind": "lift", "between": ["LIFT0", "LIFT1"], "flights": 1, "accessible": True, "todo": False}
    ]

    updated_graph = {
        "meta": data.get("meta", {}),
        "costModel": data.get("costModel", {
            "campus": 0.25,
            "int": 0.1,
            "stair": 12.0,
            "lift": 8.0,
            "door": 4.0
        }),
        "levels": data.get("levels", []),
        "zones": data.get("zones", []),
        "portals": portals,
        "nodes": all_nodes,
        "edges": all_edges,
        "rooms": all_rooms
    }

    # Validate with Pydantic model
    validated = CampusGraphData(**updated_graph)

    with open("data/campus.v2.json", "w", encoding="utf-8") as out_f:
        json.dump(updated_graph, out_f, indent=2)

    with open("campus-graph.json", "w", encoding="utf-8") as out_f:
        json.dump(updated_graph, out_f, indent=2)

    print("Successfully updated Floor 1 plan:")
    print(f"- Total Nodes: {len(validated.nodes)} ({len(f1_nodes)} on Floor 1)")
    print(f"- Total Edges: {len(validated.edges)} ({len(f1_edges)} on/to Floor 1)")
    print(f"- Total Rooms: {len(validated.rooms)} ({len(new_f1_rooms)} on Floor 1)")

if __name__ == "__main__":
    update_f1_floor_plan()
