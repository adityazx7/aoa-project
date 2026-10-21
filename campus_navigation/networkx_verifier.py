import networkx as nx
from typing import Dict, Any, Optional, Tuple, List
from .models import CampusGraphData
from .algorithms import CampusRouter, RoutingOptions

class NetworkXVerifier:
    def __init__(self, graph_data: CampusGraphData):
        self.graph_data = graph_data

    def to_networkx(self, options: Optional[RoutingOptions] = None) -> nx.Graph:
        """Constructs a networkx.Graph with matching dynamic weights and exclusions."""
        opt = options or RoutingOptions()
        G = nx.Graph()

        for node in self.graph_data.nodes:
            G.add_node(node.id, label=node.label, level=node.level, x=node.x, y=node.y, type=node.type)

        router = CampusRouter(self.graph_data)
        for edge in self.graph_data.edges:
            eff_cost = router.get_effective_edge_cost(edge, opt)
            if eff_cost is not None:
                G.add_edge(edge.a, edge.b, weight=eff_cost, type=edge.type, accessible=edge.accessible, outdoor=edge.outdoor)

        return G

    def shortest_path(
        self,
        source: str,
        target: str,
        options: Optional[RoutingOptions] = None
    ) -> Tuple[Optional[List[str]], float]:
        G = self.to_networkx(options)
        if not nx.has_path(G, source, target):
            return None, float("inf")

        path = nx.dijkstra_path(G, source, target, weight="weight")
        length = nx.dijkstra_path_length(G, source, target, weight="weight")
        return path, length
