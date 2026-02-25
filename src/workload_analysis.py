import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log


REQUIRED_COLUMNS = ['case_id', 'department', 'timestamp', 'activity']


def _save_workload_plots(wl_df: pd.DataFrame, output_dir: Path) -> None:
    if wl_df.empty:
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    for dept, group in wl_df.groupby('Department'):
        ax.plot(group['Week'], group['Open_Cases'], label=str(dept), alpha=0.45)
        ax.plot(group['Week'], group['Moving_Avg_4W'], linewidth=2)
    ax.set_title('Open Cases by Department (Weekly + 4W MA)')
    ax.set_xlabel('Week')
    ax.set_ylabel('Open Cases')
    if wl_df['Department'].nunique() <= 12:
        ax.legend(loc='best', fontsize=8)
    fig.tight_layout()
    fig.savefig(output_dir / 'workload_trend_by_department.png', dpi=150)
    plt.close(fig)


def analyze_workload(logfile_path, output_dir):
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='workload analysis')

    cases = df.groupby(['case_id', 'department']).agg(
        start=('timestamp', 'min'),
        end=('timestamp', 'max')
    ).reset_index()

    date_range = pd.date_range(cases['start'].min(), cases['end'].max(), freq='W')
    if len(date_range) == 0:
        date_range = pd.DatetimeIndex([cases['end'].max().normalize()])

    workload_data = []
    for week in date_range:
        for dept in cases['department'].dropna().unique():
            active_count = cases[
                (cases['department'] == dept)
                & (cases['start'] <= week)
                & (cases['end'] >= week)
            ].shape[0]
            workload_data.append({'Week': week, 'Department': dept, 'Open_Cases': active_count})

    wl_df = pd.DataFrame(workload_data, columns=['Week', 'Department', 'Open_Cases'])
    if wl_df.empty:
        wl_df['Moving_Avg_4W'] = pd.Series(dtype=float)
    else:
        wl_df['Moving_Avg_4W'] = wl_df.groupby('Department')['Open_Cases'].transform(
            lambda x: x.rolling(4, min_periods=1).mean()
        )

    wl_df.to_csv(output_dir / 'workload_analysis.csv', index=False)
    _save_workload_plots(wl_df, output_dir)
    print("Workload analysis complete.")


def parse_args():
    parser = argparse.ArgumentParser(description="Run workload-over-time analysis")
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated outputs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    output_dir = ensure_output_dir(args.output_dir)
    analyze_workload(logfile, output_dir)
