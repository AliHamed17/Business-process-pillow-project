import argparse
from pathlib import Path

import matplotlib.pyplot as plt

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import annotate_bars, finalize_and_save, set_plot_style
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import annotate_bars, finalize_and_save, set_plot_style


REQUIRED_COLUMNS = ['case_id', 'timestamp', 'stage_responsible', 'changed_field', 'activity']


def _save_responsible_change_plots(case_changes, comparison, output_dir: Path) -> None:
    set_plot_style()
    if not comparison.empty:
        fig, ax = plt.subplots(figsize=(6.5, 4.5))
        labels = comparison['has_reassignment'].map({False: 'No Reassignment', True: 'Has Reassignment'})
        ax.bar(labels, comparison['mean'], color=['#4C72B0', '#DD8452'])
        ax.set_title('Average Cycle Time by Reassignment')
        ax.set_ylabel('Average Cycle Time (Days)')
        annotate_bars(ax, horizontal=False)
        finalize_and_save(fig, output_dir / 'responsible_change_cycle_time_comparison.png')

    if not case_changes.empty:
        fig, ax = plt.subplots(figsize=(6.5, 4.5))
        box_data = [
            case_changes.loc[~case_changes['has_reassignment'], 'cycle_time_days'].dropna(),
            case_changes.loc[case_changes['has_reassignment'], 'cycle_time_days'].dropna(),
        ]
        if any(len(x) > 0 for x in box_data):
            ax.boxplot(box_data, labels=['No Reassignment', 'Has Reassignment'])
            ax.set_title('Cycle Time Distribution by Reassignment')
            ax.set_ylabel('Cycle Time (Days)')
            finalize_and_save(fig, output_dir / 'responsible_change_cycle_time_boxplot.png')
        else:
            plt.close(fig)

        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        case_changes['reassignment_count'].plot(kind='hist', bins=20, ax=ax, color='#55A868')
        ax.set_title('Distribution of Reassignment Count per Case')
        ax.set_xlabel('Reassignment Count')
        ax.set_ylabel('Case Count')
        finalize_and_save(fig, output_dir / 'responsible_change_count_distribution.png')


def analyze_responsible_change(logfile_path, output_dir):
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='responsible change analysis')
    df.sort_values(['case_id', 'timestamp'], inplace=True)

    df['prev_responsible'] = df.groupby('case_id')['stage_responsible'].shift(1)
    df['responsible_changed'] = (
        (df['stage_responsible'] != df['prev_responsible'])
        & (df['prev_responsible'].notna())
    )

    df['responsible_change_flag'] = (
        df['changed_field'].astype(str).str.contains('אחראי', na=False)
        | df['responsible_changed']
    )

    case_changes = df.groupby('case_id').agg(
        reassignment_count=('responsible_change_flag', 'sum'),
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    ).reset_index()

    case_changes['cycle_time_days'] = (
        case_changes['end_time'] - case_changes['start_time']
    ).dt.total_seconds() / (24 * 3600)

    case_changes['has_reassignment'] = case_changes['reassignment_count'] > 0
    comparison = case_changes.groupby('has_reassignment')['cycle_time_days'].agg(
        ['count', 'mean', 'median', 'std']
    ).reset_index()

    comparison.to_csv(output_dir / 'responsible_change_analysis.csv', index=False)
    _save_responsible_change_plots(case_changes, comparison, output_dir)
    print("Responsible change analysis complete.")


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze the impact of responsible-person changes")
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated outputs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    output_dir = ensure_output_dir(args.output_dir)
    analyze_responsible_change(logfile, output_dir)
