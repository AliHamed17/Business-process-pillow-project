import argparse
from pathlib import Path

import matplotlib.pyplot as plt

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import finalize_and_save, set_plot_style
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import finalize_and_save, set_plot_style


REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']


def _save_performance_plots(case_perf, stage_wait, df, output_dir: Path) -> None:
    set_plot_style()
    if not case_perf.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        case_perf['cycle_time_days'].dropna().plot(kind='hist', bins=20, ax=ax, color='#4C72B0')
        ax.set_title('Case Cycle Time Distribution (Days)')
        ax.set_xlabel('Cycle Time (Days)')
        ax.set_ylabel('Case Count')
        finalize_and_save(fig, output_dir / 'case_cycle_time_distribution.png')

    top_wait = stage_wait.dropna(subset=['mean']).head(10)
    if not top_wait.empty:
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.barh(top_wait['activity'].astype(str), top_wait['mean'], color='#C44E52')
        ax.invert_yaxis()
        ax.set_title('Top Activities by Average Wait Time')
        ax.set_xlabel('Average Wait Time (Days)')
        ax.set_ylabel('Activity')
        finalize_and_save(fig, output_dir / 'bottleneck_top10_mean_wait.png')

    # distribution spread by top bottleneck activities
    if 'wait_time_days' in df.columns:
        top_names = top_wait['activity'].astype(str).tolist()
        if top_names:
            subset = df[df['activity'].astype(str).isin(top_names)].copy()
            subset = subset.dropna(subset=['wait_time_days'])
            if not subset.empty:
                grouped = [
                    subset.loc[subset['activity'].astype(str) == name, 'wait_time_days'].values
                    for name in top_names
                ]
                fig, ax = plt.subplots(figsize=(10, 5.5))
                ax.boxplot(grouped, labels=top_names, showfliers=False)
                ax.set_title('Wait Time Distribution by Top Bottleneck Activities')
                ax.set_ylabel('Wait Time (Days)')
                ax.tick_params(axis='x', rotation=45)
                finalize_and_save(fig, output_dir / 'bottleneck_wait_distribution_boxplot.png')


def analyze_performance(logfile_path, output_dir):
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='performance analysis')
    df.sort_values(['case_id', 'timestamp'], inplace=True)

    case_perf = df.groupby('case_id').agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max'),
        event_count=('activity', 'size')
    ).reset_index()

    case_perf['cycle_time_days'] = (
        case_perf['end_time'] - case_perf['start_time']
    ).dt.total_seconds() / (24 * 3600)

    df['next_timestamp'] = df.groupby('case_id')['timestamp'].shift(-1)
    df['wait_time_days'] = (
        df['next_timestamp'] - df['timestamp']
    ).dt.total_seconds() / (24 * 3600)

    stage_wait = df.groupby('activity')['wait_time_days'].agg(['mean', 'median', 'std', 'max']).reset_index()
    stage_wait.sort_values(by='mean', ascending=False, inplace=True)

    case_perf.to_csv(output_dir / 'case_performance.csv', index=False)
    stage_wait.to_csv(output_dir / 'bottleneck_analysis.csv', index=False)
    _save_performance_plots(case_perf, stage_wait, df, output_dir)

    print("Performance analysis complete.")


def parse_args():
    parser = argparse.ArgumentParser(description="Run performance and bottleneck analyses")
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated outputs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    output_dir = ensure_output_dir(args.output_dir)
    analyze_performance(logfile, output_dir)
