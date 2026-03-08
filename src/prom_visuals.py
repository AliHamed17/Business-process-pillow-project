import argparse
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pm4py
import seaborn as sns
from pyvis.network import Network

try:
    from cli_utils import ensure_output_dir, load_clean_log, ensure_exists
    from plot_utils import fix_hebrew, set_plot_style
except ModuleNotFoundError:
    from .cli_utils import ensure_output_dir, load_clean_log, ensure_exists
    from .plot_utils import fix_hebrew, set_plot_style


def generate_interactive_dfg(log_path, output_dir):
    """Generate an interactive HTML Directly-Follows Graph bypassing Graphviz."""
    print("[ProM/PM4Py Vis] Generating Interactive DFG...")
    
    # Load DataFrame and convert to PM4Py Event Log
    df = pm4py.format_dataframe(
        pd.read_csv(log_path), 
        case_id='case_id', 
        activity_key='activity', 
        timestamp_key='timestamp'
    )
    
    # Discover DFG
    dfg, start_activities, end_activities = pm4py.discover_dfg(df)
    
    # Calculate node frequencies
    activities_count = pm4py.statistics.attributes.log.get.get_attribute_values(df, 'activity')
    
    # Filter edges to reduce noise (keep top 30% of edges)
    edge_frequencies = list(dfg.values())
    if not edge_frequencies:
        print("[ProM/PM4Py Vis] DFG is empty.")
        return
        
    threshold = np.percentile(edge_frequencies, 70) 
    
    net = Network(height='800px', width='100%', directed=True, bgcolor='#ffffff', font_color='black')
    
    # Add Nodes
    for act, freq in activities_count.items():
        # Node size based on frequency
        size = 10 + (freq / max(activities_count.values()) * 40)
        color = '#3CB371' if act in start_activities else ('#CD5C5C' if act in end_activities else '#87CEEB')
        
        net.add_node(
            act, 
            label=fix_hebrew(act), 
            title=f"Activity: {fix_hebrew(act)}<br>Frequency: {freq}", 
            size=size,
            color=color,
            borderWidth=2
        )
        
    # Add Edges
    for (source, target), freq in dfg.items():
        if freq >= threshold:
            # Edge width based on frequency
            width = 1 + (freq / max(edge_frequencies) * 10)
            net.add_edge(
                source, 
                target, 
                value=freq,
                title=f"Transitions: {freq}",
                width=width,
                arrows='to'
            )
            
    # Physics options for good layout
    net.set_options("""
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.01,
          "springLength": 150,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": { "iterations": 150 }
      }
    }
    """)
    
    out_path = Path(output_dir) / 'interactive_process_dfg.html'
    net.save_graph(str(out_path))
    print(f"  -> Saved Interactive DFG to {out_path}")
    return df


def generate_prom_petri_net(df, output_dir):
    """Discover a Petri Net and export to .pnml for ProM."""
    print("[ProM/PM4Py Vis] Exporting Petri Net for ProM (.pnml)...")
    
    # Discover using Inductive Miner (ensures block-structured, sound models)
    try:
        net, im, fm = pm4py.discover_petri_net_inductive(df)
        out_path = Path(output_dir) / 'prom_petri_net.pnml'
        pm4py.write_pnml(net, im, fm, str(out_path))
        print(f"  -> Saved ProM-compatible Petri Net to {out_path}")
        return net, im, fm
    except Exception as e:
        print(f"  -> Failed to generate Petri Net: {e}")
        return None, None, None


def generate_conformance_visuals(output_dir):
    """Generate beautiful conformance metrics visualizations from existing logs."""
    print("[ProM/PM4Py Vis] Generating Conformance Diagnostics Visuals...")
    
    results_path = Path("outputs/conformance_results.csv")
    if not results_path.exists():
        print(f"  -> Skipping conformance visualisations: {results_path} not found.")
        return

    try:
        df_conf = pd.read_csv(results_path)
        fitness_values = df_conf['fitness'].dropna()
        is_fit = df_conf['trace_is_fit'].dropna()
        
        # 1. Trace Fitness Distribution Box/Violin plot
        set_plot_style()
        plt.figure(figsize=(10, 5))
        sns.histplot(fitness_values, bins=20, kde=True, color='#2E86AB')
        plt.title('Trace Fitness Distribution (Heuristics Miner Model)')
        plt.xlabel('Trace Fitness (0.0 to 1.0)')
        plt.ylabel('Number of Cases')
        plt.axvline(np.mean(fitness_values), color='red', linestyle='dashed', linewidth=2, label=f'Mean: {np.mean(fitness_values):.2f}')
        plt.legend()
        plt.tight_layout()
        out_path1 = Path(output_dir) / 'conformance_fitness_distribution.png'
        plt.savefig(out_path1, dpi=300)
        plt.close()
        print(f"  -> Saved {out_path1}")
        
        # 2. Perfect vs Imperfect Fit Pie Chart
        plt.figure(figsize=(6, 6))
        # trace_is_fit might be boolean string or bool type
        fit_true = is_fit.astype(str).str.lower() == 'true'
        fit_counts = [fit_true.sum(), (~fit_true).sum()]
        labels = ['Perfectly Fit (100%)', 'Contains Violations (<100%)']
        colors = ['#3CB371', '#FF6347']
        plt.pie(fit_counts, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, wedgeprops={'edgecolor': 'white'})
        plt.title('Overall Conformance Fitness')
        plt.tight_layout()
        out_path2 = Path(output_dir) / 'conformance_pie_chart.png'
        plt.savefig(out_path2, dpi=300)
        plt.close()
        print(f"  -> Saved {out_path2}")
        
    except Exception as e:
        print(f"  -> Failed to generate conformance charts: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate pm4py/ProM visuals")
    parser.add_argument("--log", default=r"outputs\cleaned_log.csv", help="Path to cleaned log")
    parser.add_argument("--output-dir", default=r"outputs\plots\prom_pm4py", help="Output directory")
    args = parser.parse_args()

    cfg_out = ensure_output_dir(args.output_dir)
    log_path = ensure_exists(args.log, "Cleaned Log")
    
    # 1. Interactive DFG
    df_pm4py = generate_interactive_dfg(log_path, cfg_out)
    
    # 2. ProM Petri Net
    net, im, fm = generate_prom_petri_net(df_pm4py, cfg_out)
    
    # 3. Conformance Visuals
    generate_conformance_visuals(cfg_out)
    
    print("[ProM/PM4Py Vis] All ProM/pm4py visualisations complete!")

if __name__ == "__main__":
    main()
