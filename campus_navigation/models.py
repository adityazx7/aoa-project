import json
import math
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field, ConfigDict, model_validator

class CostModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    campus: float = Field(0.25, ge=0.0, description="Scale for campus outdoor walk (cost per px)")
    int_: float = Field(0.1, alias="int", ge=0.0, description="Scale for indoor walk (cost per px)")
    stair: float = Field(12.0, ge=0.0, description="Base transition cost for stairs")
    lift: float = Field(8.0, ge=0.0, description="Base transition cost for lifts")
    door: float = Field(4.0, ge=0.0, description="Base transition cost for doors")

class CampusNode(BaseModel):
    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Display label for location")
    level: str = Field(..., description="Level identifier ('c'=campus, 'f1'=floor 1, 'f0'=basement)")
    x: float = Field(..., description="X coordinate in px")
    y: float = Field(..., description="Y coordinate in px")
    type: str = Field("p", description="Node category: 'e'=entrance, 's'=stairs, 'l'=lift, 'j'=junction, 'p'=point of interest")

class CampusEdge(BaseModel):
    a: str = Field(..., description="Source node ID")
    b: str = Field(..., description="Target node ID")
    type: str = Field("w", description="Edge type: 'w'=walk, 'b'=bridge, 's'=stairs, 'l'=lift, 'd'=door")
    cost: float = Field(..., ge=0.0, description="Precomputed travel cost")
    accessible: bool = Field(True, description="Wheelchair / accessibility friendly (false for stairs)")
    outdoor: bool = Field(False, description="Whether this edge is situated outdoors")

class CampusRoom(BaseModel):
    level: str = Field(..., description="Floor/level ('c', 'f0', 'f1')")
    label: str = Field("", description="Room or area title")
    x: float
    y: float
    width: float
    height: float
    kind: str = Field("room", description="Kind: 'room', 'lab', 'bld', 'field', 'park', 'road', 'stair', 'bridge', 'floor'")

class CampusGraphData(BaseModel):
    costModel: CostModel
    nodes: List[CampusNode]
    edges: List[CampusEdge]
    rooms: List[CampusRoom] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_graph_integrity(self) -> "CampusGraphData":
        # 1. No duplicate node IDs
        node_ids: Set[str] = set()
        for node in self.nodes:
            if node.id in node_ids:
                raise ValueError(f"Duplicate node ID detected: '{node.id}'")
            node_ids.add(node.id)

        # 2. No dangling edge endpoints
        for idx, edge in enumerate(self.edges):
            if edge.a not in node_ids:
                raise ValueError(f"Dangling edge endpoint at index {idx}: node '{edge.a}' does not exist.")
            if edge.b not in node_ids:
                raise ValueError(f"Dangling edge endpoint at index {idx}: node '{edge.b}' does not exist.")
            if edge.cost < 0:
                raise ValueError(f"Negative edge cost at index {idx} ({edge.a}-{edge.b}): {edge.cost}")

        # 3. Graph is connected (undirected traversal from any node reaches all nodes)
        if node_ids:
            adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
            for edge in self.edges:
                adj[edge.a].append(edge.b)
                adj[edge.b].append(edge.a)

            start_node = next(iter(node_ids))
            visited: Set[str] = set()
            queue = [start_node]
            visited.add(start_node)

            while queue:
                curr = queue.pop(0)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            if len(visited) != len(node_ids):
                unvisited = node_ids - visited
                raise ValueError(
                    f"Graph is not connected. {len(unvisited)} unreachable nodes: {sorted(list(unvisited))}"
                )

        return self

    def recompute_edge_costs(self, cost_model: Optional[CostModel] = None) -> None:
        """Dynamically recomputes edge costs using the cost model."""
        cm = cost_model or self.costModel
        node_map = {n.id: n for n in self.nodes}

        for edge in self.edges:
            na = node_map[edge.a]
            nb = node_map[edge.b]

            if edge.type == "s":
                edge.cost = cm.stair
                edge.accessible = False
            elif edge.type == "l":
                edge.cost = cm.lift
                edge.accessible = True
            elif edge.type == "d":
                edge.cost = cm.door
                edge.accessible = True
            else:
                dist = math.hypot(na.x - nb.x, na.y - nb.y)
                is_outdoor = (na.level == "c" or nb.level == "c")
                scale = cm.campus if is_outdoor else cm.int_
                edge.cost = round(dist * scale, 2)
                edge.accessible = True
                edge.outdoor = is_outdoor

    @classmethod
    def load_from_file(cls, path: str = "campus-graph.json") -> "CampusGraphData":
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        return cls(**raw_data)

    def save_to_file(self, path: str = "campus-graph.json") -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(by_alias=True, indent=2))
