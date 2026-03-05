import argparse
from pathlib import Path

import matplotlib.pyplot as plt

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import annotate_bars, finalize_and_save, set_plot_style, truncate_label
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import annotate_bars, finalize_and_save, set_plot_style, truncate_label


REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']


def _save_performance_plots(case_perf, stage_wait, df, output_dir: Path) -> None:
    set_plot_style()
    if not case_perf.empty:
        cycle = case_perf['cycle_time_days'].dropna()
        fig, ax = plt.subplots(figsize=(8.5, 5))
        cycle.plot(kind='hist', bins=20, ax=ax, color='#4C72B0', alpha=0.75)
        if not cycle.empty:
            ax.axvline(cycle.median(), color='red', linestyle='--', linewidth=1.5, label=f"Median={cycle.median():.2f}")
            ax.axvline(cycle.quantile(0.9), color='purple', linestyle=':', linewidth=1.5, label=f"P90={cycle.quantile(0.9):.2f}")
            ax.legend(loc='best')
        ax.set_title('Case Cycle Time Distribution (Days)')
        ax.set_xlabel('Cycle Time (Days)')
        ax.set_ylabel('Case Count')
        finalize_and_save(fig, output_dir / 'case_cycle_time_distribution.png')

    top_wait = stage_wait.dropna(subset=['mean']).head(10).copy()
    if not top_wait.empty:
        fig, ax = plt.subplots(figsize=(10, 5.5))
        labels = [truncate_label(x, 42) for x in top_wait['activity'].astype(str)]
        ax.barh(labels, top_wait['mean'], color='#C44E52')
        ax.invert_yaxis()
        ax.set_title('Top Activities by Average Wait Time')
        ax.set_xlabel('Average Wait Time (Days)')
        annotate_bars(ax, horizontal=True)
        finalize_and_save(fig, output_dir / 'bottleneck_top10_mean_wait.png')

    if 'wait_time_days' in df.columns:
        top_names = top_wait['activity'].astype(str).tolist()
        if top_names:
            subset = df[df['activity'].astype(str).isin(top_names)].copy().dropna(subset=['wait_time_days'])
            if not subset.empty:
                grouped = [
                    subset.loc[subset['activity'].astype(str) == name, 'wait_time_days'].values
                    for name in top_names
                ]
                fig, ax = plt.subplots(figsize=(11, 6))
                ax.boxplot(grouped, labels=[truncate_label(x, 22) for x in top_names], showfliers=False)
                ax.set_title('Wait Time Distribution by Top Bottleneck Activities')
                ax.set_ylabel('Wait Time (Days)')
                ax.tick_params(axis='x', rotation=40)
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
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
    
    role_wait = df.groupby('stage_responsible')['wait_time_days'].agg(['mean', 'median', 'count']).reset_index()
    role_wait.sort_values(by='mean', ascending=False, inplace=True)

    user_wait = df.groupby('resource')['wait_time_days'].agg(['mean', 'median', 'count']).reset_index()
    user_wait.sort_values(by='mean', ascending=False, inplace=True)

    # Save outputs
    case_perf.to_csv(os.path.join(output_dir, 'case_performance.csv'), index=False)
    stage_wait.to_csv(os.path.join(output_dir, 'bottleneck_analysis.csv'), index=False)
    role_wait.to_csv(os.path.join(output_dir, 'role_bottleneck_analysis.csv'), index=False)
    user_wait.to_csv(os.path.join(output_dir, 'user_bottleneck_analysis.csv'), index=False)
    
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs

    case_perf.to_csv(output_dir / 'case_performance.csv', index=False)
    stage_wait.to_csv(output_dir / 'bottleneck_analysis.csv', index=False)
    _save_performance_plots(case_perf, stage_wait, df, output_dir)

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
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
