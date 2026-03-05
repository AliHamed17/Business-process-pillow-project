"""
Temporal Trend Analysis
========================
Academic Justification:
  Temporal analysis is a core process mining technique that reveals how
  process performance evolves over time, identifies seasonal patterns,
  and detects whether improvement initiatives have had measurable impact
  (Dumas et al., 2018, Chapter 8).

Outputs:
  - monthly_cycle_time_trend.png     : monthly median + P90 cycle time
  - monthly_throughput.png           : cases completed per month
  - monthly_trend_stats.csv          : raw statistics per month
  - dotted_chart.png                 : event distribution over time
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import finalize_and_save, set_plot_style
except ModuleNotFoundError:
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import finalize_and_save, set_plot_style


REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']


def analyze_temporal_trends(logfile_path, output_dir):
    """Compute monthly cycle-time trends and throughput."""
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='temporal trend analysis')
    df.sort_values(['case_id', 'timestamp'], inplace=True)

    # ── Per-case cycle time ───────────────────────────────────────────
    case_perf = df.groupby('case_id').agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max'),
        event_count=('activity', 'size'),
    ).reset_index()
    case_perf['cycle_time_days'] = (
        case_perf['end_time'] - case_perf['start_time']
    ).dt.total_seconds() / (24 * 3600)
    case_perf['start_month'] = case_perf['start_time'].dt.to_period('M').dt.to_timestamp()
    case_perf['end_month'] = case_perf['end_time'].dt.to_period('M').dt.to_timestamp()

    # ── Monthly cycle-time statistics ─────────────────────────────────
    monthly_stats = case_perf.groupby('end_month')['cycle_time_days'].agg(
        cases_completed='count',
        mean_cycle_days='mean',
        median_cycle_days='median',
        p90_cycle_days=lambda x: x.quantile(0.9),
        p95_cycle_days=lambda x: x.quantile(0.95),
        std_cycle_days='std',
    ).reset_index().rename(columns={'end_month': 'month'})
    monthly_stats.to_csv(output_dir / 'monthly_trend_stats.csv', index=False)

    # ── Cases started per month (throughput in) ───────────────────────
    monthly_started = case_perf.groupby('start_month')['case_id'].count().reset_index()
    monthly_started.columns = ['month', 'cases_started']

    # Merge
    monthly_full = monthly_stats.merge(monthly_started, on='month', how='outer').sort_values('month')
    monthly_full.fillna(0, inplace=True)

    set_plot_style()
    _plot_cycle_time_trend(monthly_stats, output_dir)
    _plot_throughput(monthly_full, output_dir)
    _plot_dotted_chart(df, output_dir)

    print("Temporal trend analysis complete.")


def _plot_cycle_time_trend(monthly_stats, output_dir: Path):
    """Monthly median + P90 cycle time with trend line."""
    if monthly_stats.empty:
        return
    fig, ax = plt.subplots(figsize=(11, 5.5))

    ax.plot(monthly_stats['month'], monthly_stats['median_cycle_days'],
            marker='o', linewidth=2, color='#4C72B0', label='Median', markersize=5)
    ax.fill_between(monthly_stats['month'],
                    monthly_stats['median_cycle_days'],
                    monthly_stats['p90_cycle_days'],
                    alpha=0.2, color='#C44E52', label='P90 band')
    ax.plot(monthly_stats['month'], monthly_stats['p90_cycle_days'],
            linewidth=1, color='#C44E52', linestyle='--', label='P90')

    # Trend line (linear regression on median)
    try:
        x_num = mdates.date2num(monthly_stats['month'])
        z = np.polyfit(x_num, monthly_stats['median_cycle_days'].values, 1)
        p = np.poly1d(z)
        ax.plot(monthly_stats['month'], p(x_num), linewidth=1.5,
                color='gray', linestyle=':', label='Trend')
        slope_per_month = z[0] * 30  # approximate slope per 30 days
        direction = "improving" if slope_per_month < 0 else "deteriorating"
        ax.annotate(f"Trend: {slope_per_month:+.1f} days/month ({direction})",
                    xy=(0.02, 0.95), xycoords='axes fraction', fontsize=9,
                    color='gray', va='top')
    except Exception:
        pass

    ax.set_title('Monthly Cycle Time Trend')
    ax.set_xlabel('Month')
    ax.set_ylabel('Cycle Time (Days)')
    ax.legend(loc='upper right')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=30)
    finalize_and_save(fig, output_dir / 'monthly_cycle_time_trend.png')


def _plot_throughput(monthly_full, output_dir: Path):
    """Monthly cases started vs completed."""
    if monthly_full.empty:
        return
    fig, ax = plt.subplots(figsize=(11, 5))
    width = 15  # bar width in days
    ax.bar(monthly_full['month'] - pd.Timedelta(days=width / 2),
           monthly_full.get('cases_started', 0), width=width,
           label='Cases Started', color='#55A868', alpha=0.75)
    ax.bar(monthly_full['month'] + pd.Timedelta(days=width / 2),
           monthly_full['cases_completed'], width=width,
           label='Cases Completed', color='#4C72B0', alpha=0.75)
    ax.set_title('Monthly Process Throughput')
    ax.set_xlabel('Month')
    ax.set_ylabel('Number of Cases')
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=30)
    finalize_and_save(fig, output_dir / 'monthly_throughput.png')


def _plot_dotted_chart(df, output_dir: Path):
    """Dotted chart: each event as a dot, cases on y-axis, time on x-axis."""
    if df.empty:
        return

    # Sample if too many cases for readability
    case_ids = df['case_id'].unique()
    if len(case_ids) > 200:
        sampled = np.random.RandomState(42).choice(case_ids, 200, replace=False)
        sub = df[df['case_id'].isin(sampled)].copy()
    else:
        sub = df.copy()

    case_order = sub.groupby('case_id')['timestamp'].min().sort_values().index
    case_map = {c: i for i, c in enumerate(case_order)}
    sub['case_y'] = sub['case_id'].map(case_map)

    fig, ax = plt.subplots(figsize=(12, max(6, len(case_order) * 0.03)))
    ax.scatter(sub['timestamp'], sub['case_y'], s=1.5, alpha=0.5, color='#4C72B0')
    ax.set_title(f'Dotted Chart ({len(case_order)} cases)')
    ax.set_xlabel('Time')
    ax.set_ylabel('Case Index')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=30)
    finalize_and_save(fig, output_dir / 'dotted_chart.png')


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze temporal trends in process performance")
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated outputs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    output_dir = ensure_output_dir(args.output_dir)
    analyze_temporal_trends(logfile, output_dir)
