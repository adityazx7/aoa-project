import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from engine import StoreEngine

def run_demonstration():
    print("=====================================================")
    print("  Store Navigator - Standalone Route Engine Demo   ")
    print("=====================================================")

    # Initialize 6-node store floorplan
    store = StoreEngine(6)
    store.set_node_metadata(0, "Entrance", "Entry", "🚪", 100, 250)
    store.set_node_metadata(1, "Produce", "Grocery", "🥦", 250, 150)
    store.set_node_metadata(2, "Bakery", "Fresh", "🥖", 250, 350)
    store.set_node_metadata(3, "Dairy", "Chilled", "🧀", 450, 150)
    store.set_node_metadata(4, "Beverages", "Drinks", "🥤", 450, 350)
    store.set_node_metadata(5, "Checkout", "Exit", "🛒", 600, 250)

    store.add_aisle(0, 1, 4)
    store.add_aisle(0, 2, 2)
    store.add_aisle(1, 2, 1)
    store.add_aisle(1, 3, 5)
    store.add_aisle(2, 3, 8)
    store.add_aisle(2, 4, 10)
    store.add_aisle(3, 5, 6)
    store.add_aisle(4, 5, 2)

    # 1. Dijkstra Path
    dists, preds, trace, stats = store.dijkstra(0, 5)
    path = []
    curr = 5
    while curr != -1:
        path.append(curr)
        curr = preds[curr]
    path.reverse()

    print(f"Optimal Dijkstra Path: {' -> '.join(map(str, path))}")
    print(f"Total Distance/Time Cost: {dists[5]} meters")
    print(f"Operations: {stats['operations_count']}, Time: {stats['execution_time_ms']} ms")

    # 2. Render and save network map
    G = nx.Graph()
    for u, v, w in store.edges:
        G.add_edge(u, v, weight=w)

    pos = {i: store.node_positions[i] for i in range(store.V)}
    plt.figure(figsize=(9, 6), dpi=150)
    plt.style.use('dark_background')

    # Draw all edges
    nx.draw_networkx_edges(G, pos, edge_color='#334155', width=2)
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='#94a3b8', font_size=9)

    # Highlight optimal path
    route_edges = [(path[i], path[i+1]) for i in range(len(path)-1)]
    nx.draw_networkx_edges(G, pos, edgelist=route_edges, edge_color='#10b981', width=4)

    # Draw nodes
    node_colors = ['#10b981' if i in path else '#0284c7' for i in range(store.V)]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=800)
    labels = {i: f"{i}\n{store.node_metadata[i]['name']}" for i in range(store.V)}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_color='white', font_weight='bold')

    plt.title(f"Optimal Store Indoor Route (0 -> 5) [Cost: {dists[5]}]", fontsize=14, color='#38bdf8', fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig("store_route.png")
    print("[SUCCESS] Floorplan visualization saved as 'store_route.png'")

if __name__ == "__main__":
    run_demonstration()