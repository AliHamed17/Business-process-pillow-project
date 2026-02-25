import argparse
from pathlib import Path

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log


REQUIRED_COLUMNS = ['case_id', 'timestamp', 'stage_responsible', 'changed_field', 'activity']


def analyze_responsible_change(logfile_path, output_dir):
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

    comparison.to_csv(Path(output_dir) / 'responsible_change_analysis.csv', index=False)
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
