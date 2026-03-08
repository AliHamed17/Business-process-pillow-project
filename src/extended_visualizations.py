"""
Extended Visualizations
========================
Generates a wide variety of extended plots from event log data
to provide deep insights into process performance, resource workload,
and case routing.

Outputs a dozen new plot types to outputs/plots/extended/.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import seaborn as sns

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import finalize_and_save, set_plot_style, fix_hebrew, truncate_label
except ModuleNotFoundError:
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import finalize_and_save, set_plot_style, fix_hebrew, truncate_label


REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']


def _plot_cfd(df, output_dir: Path):
    """1. Cumulative Flow Diagram (CFD)"""
    # Track when cases start and end
    case_perf = df.groupby('case_id').agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    ).reset_index()

    start_counts = case_perf.set_index('start_time').resample('W').size().cumsum()
    end_counts = case_perf.set_index('end_time').resample('W').size().cumsum()

    cfd = pd.DataFrame({'Started': start_counts, 'Completed': end_counts}).fillna(method='ffill').fillna(0)
    cfd['WIP (Active)'] = cfd['Started'] - cfd['Completed']

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.fill_between(cfd.index, 0, cfd['Completed'], label='Completed', color='#55A868', alpha=0.7)
    ax.fill_between(cfd.index, cfd['Completed'], cfd['Started'], label='Active (WIP)', color='#4C72B0', alpha=0.7)
    
    ax.set_title('Cumulative Flow Diagram (CFD)')
    ax.set_xlabel('Date')
    ax.set_ylabel('Number of Cases')
    ax.legend(loc='upper left')
    fig.autofmt_xdate()
    finalize_and_save(fig, output_dir / 'cumulative_flow_diagram.png')


def _plot_pareto(df, output_dir: Path):
    """2. Activity Pareto Chart"""
    activity_counts = df['activity'].value_counts()
    
    df_pareto = pd.DataFrame({'count': activity_counts})
    df_pareto['cumperc'] = df_pareto['count'].cumsum() / df_pareto['count'].sum() * 100

    fig, ax1 = plt.subplots(figsize=(14, 6))
    ax2 = ax1.twinx()

    labels = [truncate_label(x, 20) for x in df_pareto.index]
    x = np.arange(len(labels))

    ax1.bar(x, df_pareto['count'], color='#4C72B0')
    ax2.plot(x, df_pareto['cumperc'], color='#C44E52', marker='o', ms=4, linewidth=2)

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax1.set_ylabel('Frequency')
    ax2.set_ylabel('Cumulative %')
    ax2.set_ylim(0, 105)
    
    ax1.set_title('Pareto Chart of Activities')
    finalize_and_save(fig, output_dir / 'activity_pareto.png')


def _plot_radar_time(df, output_dir: Path):
    """3. Radar Chart of Event Times"""
    # Exclude weekends (Friday/Saturday in Israel) from radar if mostly empty, but generally just plot all 7 days
    df['day'] = df['timestamp'].dt.day_name()
    day_counts = df['day'].value_counts()
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    counts = [day_counts.get(d, 0) for d in days]
    
    # Radar setup
    angles = np.linspace(0, 2 * np.pi, len(days), endpoint=False).tolist()
    counts += counts[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.fill(angles, counts, color='#4C72B0', alpha=0.4)
    ax.plot(angles, counts, color='#4C72B0', linewidth=2)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(days)
    ax.set_title("Event Frequency by Day of Week", va='bottom')
    
    finalize_and_save(fig, output_dir / 'radar_day_of_week.png')


def _plot_transition_matrix(df, output_dir: Path):
    """4. Transition Duration Heatmap"""
    df_sorted = df.sort_values(['case_id', 'timestamp'])
    df_sorted['next_activity'] = df_sorted.groupby('case_id')['activity'].shift(-1)
    df_sorted['next_timestamp'] = df_sorted.groupby('case_id')['timestamp'].shift(-1)
    
    df_transitions = df_sorted.dropna(subset=['next_activity', 'next_timestamp']).copy()
    df_transitions['transition_days'] = (df_transitions['next_timestamp'] - df_transitions['timestamp']).dt.total_seconds() / 86400
    
    # Filter for top 15 activities to keep the matrix readable
    top_activities = df['activity'].value_counts().nlargest(15).index
    df_top_trans = df_transitions[
        df_transitions['activity'].isin(top_activities) & 
        df_transitions['next_activity'].isin(top_activities)
    ]
    
    pivot = df_top_trans.groupby(['activity', 'next_activity'])['transition_days'].mean().unstack(fill_value=np.nan)
    
    # Fix labels
    idx_labels = [truncate_label(x, 15) for x in pivot.index]
    col_labels = [truncate_label(x, 15) for x in pivot.columns]
    
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(pivot, cmap='coolwarm', annot=False, ax=ax, xticklabels=col_labels, yticklabels=idx_labels, cbar_kws={'label': 'Mean Transition Time (Days)'})
    ax.set_title('Transition Duration Matrix (Top 15 Activities)')
    ax.set_xlabel('To Activity')
    ax.set_ylabel('From Activity')
    plt.xticks(rotation=45, ha='right')
    
    finalize_and_save(fig, output_dir / 'transition_duration_heatmap.png')


def _plot_self_loops(df, output_dir: Path):
    """5. Self-Loop (Rework) Frequency"""
    df_sorted = df.sort_values(['case_id', 'timestamp'])
    df_sorted['next_activity'] = df_sorted.groupby('case_id')['activity'].shift(-1)
    
    self_loops = df_sorted[df_sorted['activity'] == df_sorted['next_activity']]
    loop_counts = self_loops['activity'].value_counts().head(10)
    
    if loop_counts.empty:
        return
        
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = [truncate_label(x, 30) for x in loop_counts.index]
    
    ax.barh(labels, loop_counts.values, color='#E07B39')
    ax.invert_yaxis()
    ax.set_title('Top 10 Activities by Self-Loop (Immediate Rework) Frequency')
    ax.set_xlabel('Number of Self-Loops')
    
    finalize_and_save(fig, output_dir / 'self_loop_frequency.png')


def _plot_cycle_time_kde(df, output_dir: Path):
    """6. Cycle Time Distribution (KDE)"""
    case_perf = df.groupby('case_id').agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    ).reset_index()
    case_perf['cycle_days'] = (case_perf['end_time'] - case_perf['start_time']).dt.total_seconds() / 86400
    
    # Filter 0 day cases
    case_perf = case_perf[case_perf['cycle_days'] > 0]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.kdeplot(data=case_perf, x='cycle_days', fill=True, color='#4C72B0', ax=ax)
    
    # Add vertical lines for median and P90
    median = case_perf['cycle_days'].median()
    p90 = case_perf['cycle_days'].quantile(0.9)
    
    ax.axvline(median, color='g', linestyle='--', label=f'Median: {median:.1f}d')
    ax.axvline(p90, color='r', linestyle=':', label=f'90th Pct: {p90:.1f}d')
    
    ax.set_title('Cycle Time Density Distribution')
    ax.set_xlabel('Cycle Time (Days)')
    ax.set_ylabel('Density')
    ax.set_xlim(left=0) # Cycle time can't be negative
    ax.legend()
    
    finalize_and_save(fig, output_dir / 'cycle_time_kde.png')


def _plot_events_vs_time(df, output_dir: Path):
    """7. Event Count vs. Cycle Time Scatter"""
    case_perf = df.groupby('case_id').agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max'),
        event_count=('activity', 'count')
    ).reset_index()
    case_perf['cycle_days'] = (case_perf['end_time'] - case_perf['start_time']).dt.total_seconds() / 86400
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(case_perf['event_count'], case_perf['cycle_days'], alpha=0.5, c='#4C72B0', s=15)
    
    # Trend line
    z = np.polyfit(case_perf['event_count'], case_perf['cycle_days'], 1)
    p = np.poly1d(z)
    ax.plot(case_perf['event_count'], p(case_perf['event_count']), "r--", linewidth=1.5, label='Trend')
    
    ax.set_title('Case Complexity: Number of Events vs. Total Cycle Time')
    ax.set_xlabel('Total Events in Case')
    ax.set_ylabel('Total Cycle Time (Days)')
    ax.legend()
    
    finalize_and_save(fig, output_dir / 'events_vs_time_scatter.png')


def _plot_activity_duration_boxplots(df, output_dir: Path):
    """8. Activity Duration Boxplots"""
    df_sorted = df.sort_values(['case_id', 'timestamp'])
    df_sorted['next_timestamp'] = df_sorted.groupby('case_id')['timestamp'].shift(-1)
    df_sorted['duration_days'] = (df_sorted['next_timestamp'] - df_sorted['timestamp']).dt.total_seconds() / 86400
    
    df_valid = df_sorted.dropna(subset=['duration_days'])
    
    # Top 15 most frequent activities
    top_activities = df['activity'].value_counts().nlargest(15).index
    df_top = df_valid[df_valid['activity'].isin(top_activities)].copy()
    
    # Cap outliers at 95th percentile for each activity for cleaner visualization
    P95 = df_top.groupby('activity')['duration_days'].transform(lambda x: x.quantile(0.95))
    df_top = df_top[df_top['duration_days'] < P95]
    
    df_top['activity_heb'] = df_top['activity'].apply(lambda x: truncate_label(x, 20))
    
    fig, ax = plt.subplots(figsize=(14, 8))
    sns.boxplot(data=df_top, y='activity_heb', x='duration_days', palette='Set2', ax=ax, orient='h')
    
    ax.set_title('Duration of Activities (Wait Time Until Next Activity) - Top 15\n(Outliers > 95th percentile removed for readability)')
    ax.set_xlabel('Duration (Days)')
    ax.set_ylabel('')
    
    finalize_and_save(fig, output_dir / 'activity_duration_boxplots.png')


def _plot_hour_heatmap(df, output_dir: Path):
    """9. Day x Hour Usage Heatmap"""
    df['hour'] = df['timestamp'].dt.hour
    df['day_name'] = df['timestamp'].dt.day_name()
    
    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    pivot = pd.crosstab(df['day_name'], df['hour'])
    # Reindex to ensure order
    pivot = pivot.reindex(days_order)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(pivot, cmap='YlGnBu', ax=ax, linewidths=0.5)
    ax.set_title('Event Frequency: Day of Week by Hour of Day')
    ax.set_xlabel('Hour of Day (0-23)')
    ax.set_ylabel('Day of Week')
    
    finalize_and_save(fig, output_dir / 'day_hour_heatmap.png')


def generate_extended_plots(logfile_path, output_dir):
    """Generate all extended visualizations."""
    output_dir = Path(output_dir) / 'plots' / 'extended'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='extended visualizations')
    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])

    set_plot_style()
    
    print("[Extended Viz] Generating Cumulative Flow Diagram...")
    _plot_cfd(df, output_dir)
    
    print("[Extended Viz] Generating Activity Pareto...")
    _plot_pareto(df, output_dir)
    
    print("[Extended Viz] Generating Day of Week Radar...")
    _plot_radar_time(df, output_dir)
    
    print("[Extended Viz] Generating Transition Matrix...")
    _plot_transition_matrix(df, output_dir)
    
    print("[Extended Viz] Generating Self-Loop Analysis...")
    _plot_self_loops(df, output_dir)
    
    print("[Extended Viz] Generating Cycle Time KDE...")
    _plot_cycle_time_kde(df, output_dir)
    
    print("[Extended Viz] Generating Complexity Scatter...")
    _plot_events_vs_time(df, output_dir)
    
    print("[Extended Viz] Generating Activity Duration Boxplots...")
    _plot_activity_duration_boxplots(df, output_dir)
    
    print("[Extended Viz] Generating Usage Heatmap...")
    _plot_hour_heatmap(df, output_dir)

    print(f"[Extended Viz] All extended plots saved to {output_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate extended visualisations")
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs", help="Output directory")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    outdir = ensure_output_dir(args.output_dir)
    generate_extended_plots(logfile, outdir)
