import argparse
from pathlib import Path

import pandas as pd

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log


REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']


STATION_KEYWORDS = {
    'Initiation': ['תקן', 'position', 'open'],
    'Approval Hierarchy': ['department manager', 'division manager', 'head of administration', 'אישור'],
    'HR Control': ['hr', 'משאבי אנוש'],
    'Recruitment Strategy': ['recruitment', 'internal', 'external', 'מכרז'],
    'Financial & Executive Oversight': ['budget', 'treasurer', 'ceo', 'מנכ', 'תקציב', 'גזבר'],
    'Parallel Tracks': ['payroll', 'salary simulation', 'service conditions', 'o&m', 'שכר'],
    'Implementation': ['job description', 'standards', 'labor union', 'תיאור משרה', 'ועד'],
    'Selection': ['screen', 'sort', 'committee', 'מיון', 'ועדה'],
    'Outcomes': ['cancel', 'approved', 'hired', 'ביטול', 'נקלט'],
}


def _event_wait(df: pd.DataFrame) -> pd.DataFrame:
    e = df.sort_values(['case_id', 'timestamp']).copy()
    e['next_timestamp'] = e.groupby('case_id')['timestamp'].shift(-1)
    e['wait_time_days'] = (e['next_timestamp'] - e['timestamp']).dt.total_seconds() / (24 * 3600)
    return e


def analyze_policy_and_path_alignment(logfile_path, output_dir):
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='policy and path analysis')

    if 'position_type' not in df.columns:
        df['position_type'] = 'Unknown'

    waits = _event_wait(df)

    # Legal-interval candidate analysis around screening/committee windows
    legal_mask = waits['activity'].astype(str).str.lower().str.contains('screen|sort|committee|מיון|ועדה', na=False)
    legal_subset = waits[legal_mask].copy()
    if legal_subset.empty:
        legal_subset = waits.copy()

    legal_summary = legal_subset.groupby('activity', dropna=False)['wait_time_days'].agg(
        events='count',
        mean_wait_days='mean',
        median_wait_days='median',
        p90_wait_days=lambda x: x.quantile(0.9),
    ).reset_index()
    legal_summary['regulated_window_14_45_ratio'] = legal_subset.groupby('activity')['wait_time_days'].apply(
        lambda x: ((x >= 14) & (x <= 45)).mean() if len(x) else 0
    ).values if not legal_summary.empty else []
    legal_summary.to_csv(output_dir / 'legal_interval_analysis.csv', index=False)

    # Junior position special path proxy using position_type field
    case_path = df.groupby('case_id').agg(
        position_type=('position_type', 'last'),
        event_count=('activity', 'size'),
        start=('timestamp', 'min'),
        end=('timestamp', 'max'),
    ).reset_index()
    case_path['cycle_time_days'] = (case_path['end'] - case_path['start']).dt.total_seconds() / (24 * 3600)
    junior_mask = case_path['position_type'].astype(str).str.lower().str.contains('help|junior|עוזר|זוטר', na=False)
    case_path['is_junior_proxy'] = junior_mask
    junior_summary = case_path.groupby('is_junior_proxy')['cycle_time_days'].agg(['count', 'mean', 'median', 'max']).reset_index()
    junior_summary.to_csv(output_dir / 'junior_position_path_analysis.csv', index=False)

    # Station mapping coverage to requested process narrative
    activities = [a.lower() for a in df['activity'].astype(str).dropna().unique()]
    rows = []
    for station, keywords in STATION_KEYWORDS.items():
        matched = [a for a in activities if any(k.lower() in a for k in keywords)]
        rows.append(
            {
                'station': station,
                'matched_activity_count': len(matched),
                'covered': len(matched) > 0,
                'sample_matches': '; '.join(matched[:5]),
            }
        )
    station_df = pd.DataFrame(rows)
    station_df.to_csv(output_dir / 'station_mapping_coverage.csv', index=False)

    print('Policy and path alignment analysis complete.')


def parse_args():
    parser = argparse.ArgumentParser(description='Analyze legal-window patterns, junior-path proxy, and station mapping coverage')
    parser.add_argument('logfile', help='Path to cleaned_log.csv')
    parser.add_argument('--output-dir', default='outputs', help='Directory for generated outputs')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    logfile = ensure_exists(args.logfile, 'Cleaned log')
    output_dir = ensure_output_dir(args.output_dir)
    analyze_policy_and_path_alignment(logfile, output_dir)
