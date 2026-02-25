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
    
    # Filter out very low weights for clarity
    df = df[df['weight'] > 0.01]

    net = Network(height='750px', width='100%', bgcolor='#222222', font_color='white', select_menu=True, filter_menu=True)
    net.force_atlas_2based()

    # Add nodes and edges
    nodes = set(df['source']).union(set(df['target']))
    for node in nodes:
        net.add_node(node, label=str(node), title=f"Resource: {node}", color='#3498db')

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

    net.save_graph(output_html)
    print(f"[Interactive SNA] Interactive graph saved to {output_html}")

if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    csv = os.path.join(base, "outputs", "handover_list.csv")
    out = os.path.join(base, "outputs", "interactive_sna.html")
    
    generate_interactive_sna(csv, out)
