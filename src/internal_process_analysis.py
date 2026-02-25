import argparse
from pathlib import Path

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log


REQUIRED_COLUMNS = ['case_id', 'activity', 'event_type', 'timestamp']


def analyze_internal_process(logfile_path, output_dir):
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

    stage_complexity.to_csv(Path(output_dir) / 'internal_process_analysis.csv', index=False)
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
