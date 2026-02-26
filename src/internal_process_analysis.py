import argparse
from pathlib import Path

import matplotlib.pyplot as plt

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import annotate_bars, finalize_and_save, set_plot_style
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import annotate_bars, finalize_and_save, set_plot_style


REQUIRED_COLUMNS = ['case_id', 'activity', 'event_type', 'timestamp']


def _save_internal_process_plots(stage_complexity, output_dir: Path) -> None:
    set_plot_style()
    top_rework = stage_complexity.sort_values('rework_ratio', ascending=False).head(10)
    if not top_rework.empty:
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.barh(top_rework['activity'].astype(str), top_rework['rework_ratio'], color='#8172B2')
        ax.invert_yaxis()
        ax.set_title('Top 10 Activities by Rework Ratio')
        ax.set_xlabel('Rework Ratio')
        ax.set_ylabel('Activity')
        annotate_bars(ax, horizontal=True)
        finalize_and_save(fig, output_dir / 'internal_rework_ratio_top10.png')

    # Scatter to inspect duration-vs-rework relationship
    scatter_df = stage_complexity.dropna(subset=['rework_ratio', 'avg_duration_days'])
    if not scatter_df.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.scatter(scatter_df['avg_duration_days'], scatter_df['rework_ratio'], alpha=0.75, color='#C44E52')
        ax.set_title('Stage Duration vs Rework Ratio')
        ax.set_xlabel('Average Stage Duration (Days)')
        ax.set_ylabel('Rework Ratio')
        finalize_and_save(fig, output_dir / 'internal_rework_duration_scatter.png')


def analyze_internal_process(logfile_path, output_dir):
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='internal process analysis')
    df.sort_values(['case_id', 'timestamp'], inplace=True)

    internal_updates = df.groupby(['case_id', 'activity']).agg(
        event_count=('event_type', 'count'),
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    ).reset_index()

    internal_updates['is_internal_rework'] = internal_updates['event_count'] > 1
    internal_updates['stage_duration_days'] = (
        internal_updates['end_time'] - internal_updates['start_time']
    ).dt.total_seconds() / (24 * 3600)

    stage_complexity = internal_updates.groupby('activity').agg(
        total_cases=('case_id', 'count'),
        cases_with_rework=('is_internal_rework', 'sum'),
        avg_events_per_case=('event_count', 'mean'),
        avg_duration_days=('stage_duration_days', 'mean')
    ).reset_index()

    stage_complexity['rework_ratio'] = (
        stage_complexity['cases_with_rework'] / stage_complexity['total_cases']
    )
    stage_complexity.sort_values(by='avg_events_per_case', ascending=False, inplace=True)

    stage_complexity.to_csv(output_dir / 'internal_process_analysis.csv', index=False)
    _save_internal_process_plots(stage_complexity, output_dir)
    print("Internal process analysis complete.")


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze internal rework within stages")
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated outputs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    output_dir = ensure_output_dir(args.output_dir)
    analyze_internal_process(logfile, output_dir)
