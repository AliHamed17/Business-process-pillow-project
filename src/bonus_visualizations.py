import argparse
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns

try:
    from cli_utils import ensure_output_dir, load_clean_log
    from plot_utils import fix_hebrew, set_plot_style
except ModuleNotFoundError:
    from .cli_utils import ensure_output_dir, load_clean_log
    from .plot_utils import fix_hebrew, set_plot_style


def generate_sankey_diagram(wl_df, output_dir):
    """Generate an interactive Sankey Diagram mapping Department to Final Outcome."""
    print("[Bonus] Generating Sankey Flow Diagram...")
    
    # Needs to be grouped by Case ID to get the Dept and Final Status
    cases = wl_df.sort_values(['case_id', 'timestamp'])
    last_state = cases.groupby('case_id').apply(
        lambda x: pd.Series({
            'department': x['department'].iloc[0],
            'request_status': x['request_status'].dropna().iloc[-1] if not x['request_status'].dropna().empty else 'Unresolved'
        })
    ).reset_index()

    flow_counts = last_state.groupby(['department', 'request_status']).size().reset_index(name='count')
    # Focus on top 10 departments for readability
    top_depts = flow_counts.groupby('department')['count'].sum().nlargest(10).index
    flow_counts = flow_counts[flow_counts['department'].isin(top_depts)]

    # Plotly Sankey
    all_nodes = list(flow_counts['department'].unique()) + list(flow_counts['request_status'].unique())
    node_mapping = {node: i for i, node in enumerate(all_nodes)}
    
    source = flow_counts['department'].map(node_mapping).tolist()
    target = flow_counts['request_status'].map(node_mapping).tolist()
    value = flow_counts['count'].tolist()

    labels_reversed = [fix_hebrew(node) for node in all_nodes]
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=labels_reversed,
            color="royalblue"
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color="rgba(173, 216, 230, 0.5)"
        )
    )])
    
    fig.update_layout(title_text="Case Flow: Department Request to Final Outcome", font_size=12)
    
    out_path = Path(output_dir) / 'bonus_sankey_flow.html'
    fig.write_html(str(out_path))
    print(f"  -> Saved {out_path}")


def generate_sunburst_chart(wl_df, output_dir):
    """Generate an interactive Sunburst Chart."""
    print("[Bonus] Generating Sunburst Hierarchical Chart...")
    
    cases = wl_df.sort_values(['case_id', 'timestamp'])
    last_state = cases.groupby('case_id').apply(
        lambda x: pd.Series({
            'department': x['department'].iloc[0],
            'request_status': x['request_status'].dropna().iloc[-1] if not x['request_status'].dropna().empty else 'Unresolved',
            'position_type': x['position_type'].iloc[0] if 'position_type' in x.columns else 'Unknown'
        })
    ).reset_index()
    
    last_state['department'] = last_state['department'].apply(fix_hebrew)
    last_state['request_status'] = last_state['request_status'].apply(fix_hebrew)
    last_state['position_type'] = last_state['position_type'].apply(fix_hebrew)

    fig = px.sunburst(
        last_state, 
        path=['request_status', 'position_type', 'department'], 
        title="Hierarchical Breakdown of Recruitment Cases"
    )
    
    out_path = Path(output_dir) / 'bonus_sunburst_outcomes.html'
    fig.write_html(str(out_path))
    print(f"  -> Saved {out_path}")


def generate_time_heatmap(wl_df, output_dir):
    """Generate a heatmap of when activity actually happens (Day vs Hour)."""
    print("[Bonus] Generating Activity Time Heatmap...")
    set_plot_style()
    
    # Extract day of week and hour
    df = wl_df.copy()
    df['day_of_week'] = df['timestamp'].dt.day_name()
    df['hour'] = df['timestamp'].dt.hour
    
    # Order days
    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    df['day_of_week'] = pd.Categorical(df['day_of_week'], categories=days_order, ordered=True)
    
    heatmap_data = df.groupby(['day_of_week', 'hour']).size().unstack(fill_value=0)
    
    plt.figure(figsize=(12, 6))
    sns.heatmap(heatmap_data, cmap='YlGnBu', linewidths=.5)
    plt.title('Municipality Activity Heatmap (Day of Week vs Hour)')
    plt.xlabel('Hour of Day (24H)')
    plt.ylabel('Day of Week')
    plt.tight_layout()
    
    out_path = Path(output_dir) / 'bonus_activity_time_heatmap.png'
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"  -> Saved {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate bonus visualisations")
    parser.add_argument("--log", default=r"outputs\cleaned_log.csv", help="Path to cleaned log")
    parser.add_argument("--output-dir", default=r"outputs\plots\advanced", help="Output directory")
    args = parser.parse_args()

    cfg_out = ensure_output_dir(args.output_dir)
    df = load_clean_log(
        args.log, 
        required_columns=['case_id', 'department', 'timestamp', 'activity'], 
        context='bonus visualizations'
    )
    
    generate_sankey_diagram(df, cfg_out)
    generate_sunburst_chart(df, cfg_out)
    generate_time_heatmap(df, cfg_out)
    
    print("[Bonus] All extensive bonus visualisations complete!")

if __name__ == "__main__":
    main()
