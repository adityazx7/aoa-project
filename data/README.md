# Campus Navigation Graph Data Format (v2)

`data/campus.v2.json` is the single source of truth for indoor and outdoor routing, 2D blueprint rendering, and 3D architectural visualization in **Spatial Navigator**.

---

## 1. Coordinate Frames & Metric System

All internal engine routing distances and times are strictly unified:
- **Physical Coordinates (`xy`, `path`)**: Metres in a local ENU (East-North-Up) metric frame.
- **Elevation (`z`)**: Metres relative to campus ground ($z = 0.0$ for campus ground and Floor 1 walkway; $z = -4.5$ for basement labs).
- **Pixel Coordinates (`x`, `y`)**: SVG canvas coordinates calibrated at:
  - Campus Outdoors (`level: 'c'`): $\approx 0.18\text{ m/px}$
  - Interior Floors (`level: 'f1'`, `'f0'`): $\approx 0.10\text{ m/px}$
- **Routing Costs**: Traversal durations strictly in **seconds** (`total_s`).
- **Physical Distances**: Real world distances in **metres** (`total_m`).

---

## 2. Schema Specification

Validated at load time using Pydantic v2 (`CampusGraphData` in `campus_navigation/models.py`).

```json
{
  "meta": {
    "origin": [19.0216, 72.8708],
    "rotation_deg": 0.0,
    "units": "m",
    "crs": "local_enu",
    "todo": true
  },
  "costModel": {
    "campus": 0.25,
    "int": 0.1,
    "stair": 12.0,
    "lift": 8.0,
    "door": 4.0
  },
  "levels": [
    {"id": "c", "name": "Campus Grounds", "z": 0.0},
    {"id": "f0", "name": "Basement Labs", "z": -4.5},
    {"id": "f1", "name": "Floor 1 Walkway / Atrium", "z": 0.0}
  ],
  "zones": [
    {
      "id": "atrium_plaza",
      "name": "Central Covered Atrium Plaza",
      "level": "f1",
      "polygon": [[40.0, 20.0], [105.0, 20.0], [105.0, 60.0], [40.0, 60.0]],
      "walkable": true,
      "todo": true
    }
  ],
  "nodes": [
    {
      "id": "GATE",
      "label": "Main Campus Security Gate",
      "level": "c",
      "x": 1585.0,
      "y": 430.0,
      "z": 0.0,
      "xy": [285.3, 77.4],
      "type": "e",
      "kind": "entrance",
      "landmark": "Main Campus Security Gate",
      "todo": true
    }
  ],
  "edges": [
    {
      "a": "GATE",
      "b": "R1",
      "type": "w",
      "kind": "walk",
      "cost": 20.08,
      "distance_m": 26.1,
      "time_s": 20.08,
      "width_m": 3.0,
      "accessible": true,
      "outdoor": true,
      "path": [[285.3, 77.4], [259.2, 77.4]],
      "todo": true
    }
  ],
  "portals": [
    {
      "id": "stairs_sa",
      "kind": "stairs",
      "between": ["SA0", "S1A"],
      "flights": 1,
      "accessible": false,
      "todo": false
    },
    {
      "id": "lift_atrium",
      "kind": "lift",
      "between": ["LIFT0", "LIFT1"],
      "flights": 1,
      "accessible": true,
      "todo": false
    }
  ],
  "rooms": [
    {
      "level": "f1",
      "label": "Auditorium",
      "x": 1050.0,
      "y": 140.0,
      "width": 160.0,
      "height": 180.0,
      "kind": "room"
    }
  ]
}
```

---

## 3. Data Integrity & Validation Guarantees

The loader automatically enforces the following invariants:
1. **Unique Node IDs**: No duplicate identifiers permitted.
2. **Endpoint Validity**: Every edge and portal endpoint must reference an existing node.
3. **Non-negative Costs**: Travel times and distances must be $\ge 0$.
4. **Global Graph Connectivity**: The graph must form a single connected component across floors via stairs and elevators.
5. **Accessibility Integrity**: Stairs are marked `accessible: false` (excluded when wheelchair routing is active); elevators are marked `accessible: true`.

---

## 4. Pending Survey Data (TODO Markers)

Per Blueprint §11, the following real-world calibration measurements can be refined by surveying:
- `meta.origin`: High-precision GNSS benchmark coordinates for campus origin point.
- `meta.rotation_deg`: True astronomical north orientation relative to surveyed CAD coordinate frame.
- `portals`: Additional upper-floor transitions (stairs ascending from E-Block, F-Block, and B-Block wings).
- `nodes.landmark`: YouTube tour timestamp notes for specific visual landmarks ("enter -> turn left -> stairs down beside red telephone box").
- `edges.width_m`: Exact measured corridor pinch-points and doorway clear widths.
