import pandas as pd
import pm4py
import os
import matplotlib.pyplot as plt
from pm4py.algo.organizational_mining.sna import algorithm as sn_discovery
from pm4py.visualization.sna import visualizer as sn_visualizer

def perform_sna_analysis(logfile_path, output_dir):
    """
    Performs Social Network Analysis (SNA) on the event log.
    """
    if not os.path.exists(logfile_path):
        print(f"Error: Log file {logfile_path} not found.")
        return

    print("[SNA Analysis] Loading log...")
    # Read the CSV log
    df = pd.read_csv(logfile_path, encoding='utf-8-sig')
    # Manual renaming for SNA
    df = df.rename(columns={
        'case_id': 'case:concept:name',
        'activity': 'concept:name',
        'timestamp': 'time:timestamp',
        'resource': 'org:resource'
    })
    df['time:timestamp'] = pd.to_datetime(df['time:timestamp'], errors='coerce')
    log = df # SNA PANDAS variants just need the columns named correctly
    
    plots_dir = os.path.join(output_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    # 1. Handover of Work Network
    print("[SNA Analysis] Discovering Handover of Work network...")
    handover_nw = sn_discovery.apply(log, variant=sn_discovery.Variants.HANDOVER_PANDAS)
    
    # 2. Working Together Network
    print("[SNA Analysis] Discovering Working Together network...")
    working_together_nw = sn_discovery.apply(log, variant=sn_discovery.Variants.WORKING_TOGETHER_PANDAS)

    # Export metrics (Handover connections)
    connections = handover_nw.connections
    handover_data = []
    for (r1, r2), weight in connections.items():
        handover_data.append({'source': r1, 'target': r2, 'weight': weight})
    
    handover_df = pd.DataFrame(handover_data)
    handover_csv = os.path.join(output_dir, "handover_list.csv")
    handover_df.to_csv(handover_csv, index=False, encoding='utf-8-sig')
    print(f"[SNA Analysis] Metrics saved to {handover_csv}")

    # Visualizations
    # Note: sn_visualizer uses graphviz. If it fails, we fall back to manual plotting or logs.
    try:
        print("[SNA Analysis] Generating visualizations...")
        gviz_handover = sn_visualizer.apply(handover_nw, variant=sn_visualizer.Variants.NETWORKX)
        handover_plot = os.path.join(plots_dir, "sna_handover.png")
        sn_visualizer.save(gviz_handover, handover_plot)
        print(f"[SNA Analysis] Handover plot saved to {handover_plot}")
        
        # Working Together
        gviz_wt = sn_visualizer.apply(working_together_nw, variant=sn_visualizer.Variants.NETWORKX)
        wt_plot = os.path.join(plots_dir, "sna_working_together.png")
        sn_visualizer.save(gviz_wt, wt_plot)
        print(f"[SNA Analysis] Working Together plot saved to {wt_plot}")
    except Exception as e:
        print(f"Warning: SNA Visualization failed: {e}")
        # Graphviz might not be in PATH. We'll still have the CSV data.

    # Identify Key Players (Centrality - simplified as sum of handovers)
    if not handover_df.empty:
        player_impact = handover_df.groupby('source')['weight'].sum().sort_values(ascending=False).head(10)
        print("\n[Top 10 Key Resources by Handover Activity (Out-degree)]")
        print(player_impact)
    else:
        player_impact = pd.Series()
        print("\n[SNA Analysis] No handover activity found.")

    return player_impact

if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    logfile = os.path.join(base, "outputs", "cleaned_log.csv")
    outdir = os.path.join(base, "outputs")
    
    perform_sna_analysis(logfile, outdir)
