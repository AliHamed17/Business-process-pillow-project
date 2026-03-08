"""
Sojourn Time (Stage Dwell Time) Analysis
==========================================
Academic Justification:
  Sojourn time measures the time a case spends *within* a stage from its
  first entry to its last exit.  This is distinct from the inter-event
  "wait time" (time between consecutive events), which can conflate
  processing time with idle time between stages.

  For municipal processes with well-defined stage boundaries, sojourn
  time is the standard bottleneck metric recommended in van der Aalst
  (2016, Chapter 6) and Dumas et al. (2018, Section 8.3).

Outputs:
  - sojourn_time_by_stage.csv   : per-stage aggregated sojourn statistics
  - sojourn_time_by_department.csv : per-department cycle and sojourn stats
  - sojourn_time_distribution.png  : box-plot of top sojourn stages
  - sojourn_vs_cycle_scatter.png    : stage sojourn vs overall cycle time
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import annotate_bars, apply_rtl_text, finalize_and_save, set_plot_style, truncate_label
except ModuleNotFoundError:
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import annotate_bars, apply_rtl_text, finalize_and_save, set_plot_style, truncate_label


REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']


def _compute_sojourn_times(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute sojourn time per (case_id, activity) pair.

    For each case, group events by activity and compute:
      - entry_time  : first timestamp for that activity in this case
      - exit_time   : last timestamp for that activity in this case
      - sojourn_days: exit_time - entry_time (in days)
      - event_count : number of events within this stage visit
    """
    stage_visits = df.groupby(['case_id', 'activity']).agg(
        entry_time=('timestamp', 'min'),
        exit_time=('timestamp', 'max'),
        event_count=('timestamp', 'size'),
    ).reset_index()

    stage_visits['sojourn_days'] = (
        stage_visits['exit_time'] - stage_visits['entry_time']
    ).dt.total_seconds() / (24 * 3600)

    return stage_visits


def _save_sojourn_plots(stage_stats: pd.DataFrame, stage_visits: pd.DataFrame,
                        output_dir: Path) -> None:
    set_plot_style()

    # 1. Top 10 stages by mean sojourn time (horizontal bar)
    top_stages = stage_stats.head(10).copy()
    if not top_stages.empty:
        fig, ax = plt.subplots(figsize=(10, 5.5))
        labels = [truncate_label(x, 42) for x in top_stages['activity'].astype(str)]
        ax.barh(labels, top_stages['mean_sojourn_days'], color='#E07B39')
        ax.invert_yaxis()
        apply_rtl_text(ax, title='Top 10 Stages by Mean Sojourn Time', xlabel='Mean Sojourn Time (Days)')
        annotate_bars(ax, horizontal=True)
        finalize_and_save(fig, output_dir / 'sojourn_top10_mean.png')

    # 2. Box-plot of sojourn distribution for top stages
    top_names = top_stages['activity'].astype(str).tolist()
    if top_names:
        subset = stage_visits[stage_visits['activity'].astype(str).isin(top_names)].copy()
        subset = subset.dropna(subset=['sojourn_days'])
        if not subset.empty:
            grouped = [
                subset.loc[subset['activity'].astype(str) == name, 'sojourn_days'].values
                for name in top_names
            ]
            fig, ax = plt.subplots(figsize=(11, 6))
            ax.boxplot(grouped, labels=[truncate_label(x, 22) for x in top_names],
                       showfliers=False)
            apply_rtl_text(ax, title='Sojourn Time Distribution by Top Bottleneck Stages', ylabel='Sojourn Time (Days)')
            ax.tick_params(axis='x', rotation=40)
            finalize_and_save(fig, output_dir / 'sojourn_time_distribution.png')

    # 3. Median vs P90 comparison
    if not top_stages.empty:
        fig, ax = plt.subplots(figsize=(10, 5.5))
        labels = [truncate_label(x, 30) for x in top_stages['activity'].astype(str)]
        x = range(len(labels))
        ax.bar([i - 0.2 for i in x], top_stages['median_sojourn_days'], width=0.4,
               label='Median', color='#4C72B0')
        ax.bar([i + 0.2 for i in x], top_stages['p90_sojourn_days'], width=0.4,
               label='P90', color='#C44E52')
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=40, ha='right', fontsize=8)
        apply_rtl_text(ax, title='Median vs P90 Sojourn Time by Stage', ylabel='Sojourn Time (Days)')
        ax.legend()
        finalize_and_save(fig, output_dir / 'sojourn_median_vs_p90.png')


def analyze_sojourn_times(logfile_path, output_dir):
    """Main entry point for sojourn time analysis."""
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='sojourn time analysis')
    df.sort_values(['case_id', 'timestamp'], inplace=True)

    # Compute per-(case, stage) sojourn times
    stage_visits = _compute_sojourn_times(df)

    # Aggregate per-stage statistics
    stage_stats = stage_visits.groupby('activity')['sojourn_days'].agg(
        case_count='count',
        mean_sojourn_days='mean',
        median_sojourn_days='median',
        std_sojourn_days='std',
        p90_sojourn_days=lambda x: x.quantile(0.9),
        p95_sojourn_days=lambda x: x.quantile(0.95),
        max_sojourn_days='max',
    ).reset_index()
    stage_stats.sort_values('mean_sojourn_days', ascending=False, inplace=True)
    stage_stats.to_csv(output_dir / 'sojourn_time_by_stage.csv', index=False)

    # Department-level aggregation
    if 'department' in df.columns:
        dept_visits = df.groupby(['case_id', 'department']).agg(
            case_start=('timestamp', 'min'),
            case_end=('timestamp', 'max'),
        ).reset_index()
        dept_visits['cycle_time_days'] = (
            dept_visits['case_end'] - dept_visits['case_start']
        ).dt.total_seconds() / (24 * 3600)
        dept_stats = dept_visits.groupby('department')['cycle_time_days'].agg(
            case_count='count',
            mean_cycle_days='mean',
            median_cycle_days='median',
            p90_cycle_days=lambda x: x.quantile(0.9),
        ).reset_index()
        dept_stats.sort_values('mean_cycle_days', ascending=False, inplace=True)
        dept_stats.to_csv(output_dir / 'sojourn_time_by_department.csv', index=False)

    _save_sojourn_plots(stage_stats, stage_visits, output_dir)
    print("Sojourn time analysis complete.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze sojourn (dwell) time within stages"
    )
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs",
                        help="Directory for generated outputs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    output_dir = ensure_output_dir(args.output_dir)
    analyze_sojourn_times(logfile, output_dir)
