import os
os.environ["PATH"] += os.pathsep + r'C:\Program Files\Graphviz\bin'
import pandas as pd
import pm4py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict


def filter_dfg_by_weight(dfg: dict, threshold_pct: float = 0.10) -> dict:
    """
    Filters a DFG dict to retain only edges whose frequency is at least
    `threshold_pct` of the maximum edge frequency.

    Academic Justification:
      A raw DFG on high-noise logs (such as this recruitment log) contains
      hundreds of infrequent arcs that represent data-entry artefacts rather
      than real process flows. Filtering edges below 10% of the maximum
      frequency is a standard noise-reduction step (van der Aalst, 2016,
      Chapter 7) and produces a model readable enough for academic reporting.

    Parameters
    ----------
    dfg           : dict mapping (source, target) -> frequency count
    threshold_pct : minimum fraction of the max frequency to keep an edge

    Returns
    -------
    Filtered DFG dict
    """
    if not dfg:
        return dfg
    max_freq = max(dfg.values())
    cutoff = max_freq * threshold_pct
    filtered = {arc: freq for arc, freq in dfg.items() if freq >= cutoff}
    print(f"[DFG Filter] Retained {len(filtered)}/{len(dfg)} edges "
          f"(threshold: {threshold_pct*100:.0f}% of max={max_freq})")
    return filtered


def _plot_dfg(dfg: dict, start_activities: dict, end_activities: dict,
              output_path: str, title: str = "DFG"):
    """
    Draws a simple DFG diagram using matplotlib (no Graphviz required).
    Activities are laid out in a column; edge widths scale with frequency.
    """
    if not dfg:
        print("[DFG Plot] Empty DFG, skipping plot.")
        return

    node_freq: dict = defaultdict(int)
    for (src, tgt), freq in dfg.items():
        node_freq[src] += freq
        node_freq[tgt] += freq

    nodes = sorted(node_freq, key=lambda n: node_freq[n], reverse=True)
    n = len(nodes)
    pos = {node: (0.5, 1.0 - i / max(n - 1, 1)) for i, node in enumerate(nodes)}

    max_freq = max(dfg.values()) if dfg else 1

    fig, ax = plt.subplots(figsize=(12, max(8, n * 0.4)))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.05, 1.05)
    ax.axis('off')
    ax.set_title(title, fontsize=13, fontweight='bold')

    for (src, tgt), freq in dfg.items():
        if src not in pos or tgt not in pos:
            continue
        x0, y0 = pos[src]
        x1, y1 = pos[tgt]
        lw = 0.5 + 4.5 * (freq / max_freq)
        alpha = 0.3 + 0.6 * (freq / max_freq)
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", lw=lw,
                                   color='steelblue', alpha=alpha))
        mid_x = (x0 + x1) / 2 + 0.02
        mid_y = (y0 + y1) / 2
        ax.text(mid_x, mid_y, str(freq), fontsize=6, color='gray', ha='left')

    for node, (x, y) in pos.items():
        is_start = node in start_activities
        is_end = node in end_activities
        color = '#2ecc71' if is_start else ('#e74c3c' if is_end else '#3498db')
        ax.plot(x, y, 'o', markersize=12, color=color, zorder=5)
        label = node[:40] + '…' if len(node) > 40 else node
        ax.text(x + 0.015, y, label, fontsize=7, va='center', ha='left', zorder=6)

    legend_handles = [
        mpatches.Patch(color='#2ecc71', label='Start Activity'),
        mpatches.Patch(color='#e74c3c', label='End Activity'),
        mpatches.Patch(color='#3498db', label='Intermediate Activity'),
    ]
    ax.legend(handles=legend_handles, loc='lower right', fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[DFG Plot] Saved to {output_path}")


def generate_process_models(logfile_path, output_dir, dfg_threshold: float = 0.10):
    """
    Generates process discovery models (DFG, Inductive tree, Variants).

    Parameters
    ----------
    logfile_path  : path to cleaned_log.csv
    output_dir    : output directory
    dfg_threshold : minimum relative edge weight to include (default 10%)
    """
    print(f"Reading cleaned log from {logfile_path}")
    df = pd.read_csv(logfile_path, encoding='utf-8-sig')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df.dropna(subset=['timestamp'], inplace=True)

    # pm4py requires standard format
    log = pm4py.format_dataframe(
        df, case_id='case_id', activity_key='activity', timestamp_key='timestamp'
    )

    # 1) DFG – raw
    print("Generating DFG...")
    dfg_raw, start_activities, end_activities = pm4py.discover_dfg(log)

    # 2) Filter DFG to edges >= 10% of max frequency
    dfg_filtered = filter_dfg_by_weight(dfg_raw, threshold_pct=dfg_threshold)

    # Save filtered DFG edge stats
    dfg_records = [
        {'source': src, 'target': tgt, 'frequency': freq}
        for (src, tgt), freq in sorted(dfg_filtered.items(), key=lambda x: -x[1])
    ]
    dfg_csv = os.path.join(output_dir, 'dfg_filtered_edges.csv')
    pd.DataFrame(dfg_records).to_csv(dfg_csv, index=False, encoding='utf-8-sig')
    print(f"Filtered DFG edges saved to {dfg_csv}")

    # 3) Plot filtered DFG
    plots_dir = os.path.join(output_dir, 'plots')
    os.makedirs(plots_dir, exist_ok=True)
    _plot_dfg(
        dfg_filtered, start_activities, end_activities,
        output_path=os.path.join(plots_dir, 'dfg_filtered.png'),
        title=f'Filtered DFG (edges >= {int(dfg_threshold*100)}% of max frequency)'
    )

    # 4) Inductive Miner
    print("Generating Inductive Miner model...")
    try:
        tree = pm4py.discover_process_tree_inductive(log)
        print("Inductive Miner process tree discovered successfully.")
    except Exception as e:
        print(f"Inductive Miner warning: {e}")

    # 5) Variant Analysis
    print("Extracting variants...")
    variants = pm4py.get_variants(log)
    var_list = [
        {'Variant': str(var), 'Frequency': count}
        for var, count in variants.items()
    ]
    df_var = pd.DataFrame(var_list).sort_values(by='Frequency', ascending=False)
    df_var.head(20).to_csv(
        os.path.join(output_dir, 'variants.csv'), index=False, encoding='utf-8-sig'
    )

    # 6) Variant frequency bar chart (top 15)
    top_variants = df_var.head(15).copy()
    top_variants['short_label'] = [f"V{i+1}" for i in range(len(top_variants))]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(top_variants['short_label'], top_variants['Frequency'], color='steelblue')
    ax.set_xlabel('Variant')
    ax.set_ylabel('Case Count')
    ax.set_title('Top 15 Process Variants by Frequency')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'variant_frequency.png'), dpi=150)
    plt.close()

    print("Process discovery complete.")
    return dfg_filtered, start_activities, end_activities


if __name__ == "__main__":
    out = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining\outputs"
    f = os.path.join(out, "cleaned_log.csv")
    generate_process_models(f, out, dfg_threshold=0.10)
