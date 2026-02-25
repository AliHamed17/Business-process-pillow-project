import argparse
from pathlib import Path

from cli_utils import ensure_exists, ensure_output_dir, load_clean_log


REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']


def analyze_performance(logfile_path, output_dir):
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

    case_perf.to_csv(Path(output_dir) / 'case_performance.csv', index=False)
    stage_wait.to_csv(Path(output_dir) / 'bottleneck_analysis.csv', index=False)

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
