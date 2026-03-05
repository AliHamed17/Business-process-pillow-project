import pandas as pd
import os
import matplotlib.colors as mcolors

def generate_interactive_sna(handover_csv, output_html):
    """
    Generates a dynamic, interactive HTML Social Network using pyvis.
    """
    try:
        from pyvis.network import Network
    except ImportError:
        print("[Interactive SNA] pyvis not installed. Skipping...")
        return

    if not os.path.exists(handover_csv):
        print(f"[Interactive SNA] File {handover_csv} not found.")
        return

    print("[Interactive SNA] Building dynamic graph...")
    df = pd.read_csv(handover_csv)
    
    import networkx as nx
    
    # Filter out very low weights for clarity
    df = df[df['weight'] > 0.01]
    
    # ── Compute Centrality with NetworkX ──
    G = nx.from_pandas_edgelist(df, 'source', 'target', ['weight'], create_using=nx.DiGraph())
    betweenness = nx.betweenness_centrality(G, weight='weight')
    closeness = nx.closeness_centrality(G, distance='weight')
    degree = dict(G.degree())
    
    # Save centrality to CSV for academic report
    csv_path = str(output_html).replace('.html', '_centrality.csv')
    cent_df = pd.DataFrame({
        'node': list(G.nodes()),
        'betweenness': [betweenness[n] for n in G.nodes()],
        'closeness': [closeness[n] for n in G.nodes()],
        'degree': [degree[n] for n in G.nodes()]
    }).sort_values('betweenness', ascending=False)
    cent_df.to_csv(csv_path, index=False)
    print(f"[Interactive SNA] Centrality metrics saved to {csv_path}")

    net = Network(height='750px', width='100%', bgcolor='#222222', font_color='white', select_menu=True, filter_menu=True)
    net.force_atlas_2based()

    # Add nodes and edges
    for node in G.nodes():
        node_size = 10 + (degree.get(node, 0) * 2) # Size by degree
        btn = betweenness.get(node, 0)
        
        # Color by betweenness: red for high betweenness (bottlenecks), blue for low
        r = int(min(255, max(50, 50 + btn * 5000)))
        g = int(max(50, 150 - btn * 1000))
        b = int(max(50, 200 - btn * 1000))
        color = f'#{r:02x}{g:02x}{b:02x}'
        
        hover_text = (f"Resource: {node}\n"
                      f"Degree: {degree.get(node, 0)}\n"
                      f"Betweenness: {btn:.4f}\n"
                      f"Closeness: {closeness.get(node, 0):.4f}")
        
        net.add_node(node, label=str(node), title=hover_text, color=color, size=node_size)

    for _, row in df.iterrows():
        # Scale width by weight
        width = 1 + row['weight'] * 5
        net.add_edge(row['source'], row['target'], value=row['weight'], width=width, title=f"Weight: {row['weight']:.2f}", arrows='to')


    net.set_options("""
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": { "iterations": 150 }
      }
    }
    """)

    # Pyvis requires strings, not pathlib.Path objects
    out_str = str(output_html)
    net.save_graph(out_str)
    print(f"[Interactive SNA] Interactive graph saved to {out_str}")

if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    csv = os.path.join(base, "outputs", "handover_list.csv")
    out = os.path.join(base, "outputs", "interactive_sna.html")
    
    generate_interactive_sna(csv, out)
