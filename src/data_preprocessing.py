import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pm4py

try:
    from cli_utils import ensure_exists, ensure_output_dir, validate_columns
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, validate_columns


SOURCE_REQUIRED_COLUMNS = [
    'מזהה רשומה',
    'תאריך שינוי',
    'אירוע',
    'שם שלב',
]


COLUMN_MAPPING = {
    'מזהה רשומה': 'case_id',
    'תאריך שינוי': 'timestamp',
    'מבצע שינוי': 'resource',
    'אירוע': 'event_type',
    'יישות בשינוי': 'entity_changed',
    'מזהה שלב': 'stage_id',
    'שם שלב': 'activity',
    'תאריך יעד לשלב': 'target_date',
    'תאריך סיום שלב': 'stage_end_date',
    'אחראי שלב': 'stage_responsible',
    'סטטוס בקשה ': 'request_status',
    'תקן': 'position_type',
    'מזהה בקשה': 'request_id',
    'מחלקה': 'department',
    'מספר מחלקה': 'department_id',
    'שדה שהשתנה': 'changed_field',
    'ערכים שהשתנו (גולמי)': 'raw_changed_values',
}


PM4PY_REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']


def preprocess_logs(file_path1, file_path2, output_dir):
    """Read, clean, and merge process logs into a structured Event Log."""
    print("Reading Excel files...")
    df1 = pd.read_excel(file_path1)
    df2 = pd.read_excel(file_path2)

    validate_columns(df1, SOURCE_REQUIRED_COLUMNS, context='raw log file 1')
    validate_columns(df2, SOURCE_REQUIRED_COLUMNS, context='raw log file 2')

    df = pd.concat([df1, df2], ignore_index=True)
    print(f"Initial shape: {df.shape}")

    df.replace(["NULL", "—"], np.nan, inplace=True)
    df.rename(columns=COLUMN_MAPPING, inplace=True)

    validate_columns(df, PM4PY_REQUIRED_COLUMNS, context='cleaned log')

    df['activity'] = df['activity'].fillna('Unknown Stage')
    df['combined_activity'] = df['activity'].astype(str) + " - " + df['event_type'].fillna('unknown_event').astype(str)

    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    if 'target_date' in df.columns:
        df['target_date'] = pd.to_datetime(df['target_date'], errors='coerce')
    if 'stage_end_date' in df.columns:
        df['stage_end_date'] = pd.to_datetime(df['stage_end_date'], errors='coerce')

    before_drop_missing = len(df)
    df.dropna(subset=PM4PY_REQUIRED_COLUMNS, inplace=True)
    dropped_missing = before_drop_missing - len(df)
    if dropped_missing:
        print(f"Dropped {dropped_missing} rows with missing case_id/activity/timestamp")

    df.sort_values(by=['case_id', 'timestamp'], inplace=True)

    before_drop_dupes = len(df)
    dedupe_keys = [col for col in ['case_id', 'timestamp', 'activity', 'event_type', 'changed_field'] if col in df.columns]
    df.drop_duplicates(subset=dedupe_keys, inplace=True)
    dropped_duplicates = before_drop_dupes - len(df)
    print(f"Dropped {dropped_duplicates} duplicate rows")

    # ── Consecutive duplicate activity removal ──────────────────────────
    # Academic justification: The raw log records every field-level change
    # as a separate event.  When a user updates 5 fields inside stage
    # "אישור מנהל אגף", the log contains 5 rows with the *same* activity
    # name.  Without collapsing these, the DFG and variant analysis will
    # show false self-loops and mono-stage "variants" (e.g. the same
    # activity repeated 10+ times).  This step keeps only the *first*
    # occurrence of each consecutive run, preserving genuine stage
    # transitions while eliminating intra-stage noise.
    before_consec = len(df)
    df['_prev_activity'] = df.groupby('case_id')['activity'].shift(1)
    df = df[df['activity'] != df['_prev_activity']].copy()
    df.drop(columns=['_prev_activity'], inplace=True)
    dropped_consecutive = before_consec - len(df)
    print(f"Dropped {dropped_consecutive} consecutive duplicate activity rows")

    output_csv = Path(output_dir) / 'cleaned_log.csv'
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"Cleaned CSV saved to {output_csv}")

    df_pm4py = pm4py.format_dataframe(df, case_id='case_id', activity_key='activity', timestamp_key='timestamp')
    try:
        event_log = pm4py.convert_to_event_log(df_pm4py)
        output_xes = Path(output_dir) / 'event_log.xes'
        pm4py.write_xes(event_log, output_xes)
        print(f"XES saved to {output_xes}")
    except Exception as exc:
        print(f"Warning: Could not save XES directly due to complex objects: {exc}")
        fallback_cols = [col for col in ['case_id', 'timestamp', 'activity', 'resource', 'event_type'] if col in df.columns]
        df_simple = pm4py.format_dataframe(
            df[fallback_cols].copy(),
            case_id='case_id',
            activity_key='activity',
            timestamp_key='timestamp',
        )
        event_log = pm4py.convert_to_event_log(df_simple)
        output_xes = Path(output_dir) / 'event_log.xes'
        pm4py.write_xes(event_log, output_xes)
        print(f"Simplified XES saved to {output_xes}")

    quality_report = {
        'rows_after_merge': int(len(df1) + len(df2)),
        'rows_after_cleaning': int(len(df)),
        'dropped_missing_core_fields': int(dropped_missing),
        'dropped_duplicates': int(dropped_duplicates),
        'dropped_consecutive_duplicates': int(dropped_consecutive),
        'unique_cases': int(df['case_id'].nunique()),
        'unique_activities': int(df['activity'].nunique()),
        'timestamp_min': df['timestamp'].min().isoformat() if not df.empty else None,
        'timestamp_max': df['timestamp'].max().isoformat() if not df.empty else None,
    }
    quality_path = Path(output_dir) / 'preprocessing_quality_report.json'
    quality_path.write_text(json.dumps(quality_report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Preprocessing quality report saved to {quality_path}")

    return df, event_log


def parse_args():
    parser = argparse.ArgumentParser(description="Preprocess two Excel logs into a cleaned process log and XES file")
    parser.add_argument("file1", help="Path to first Excel file")
    parser.add_argument("file2", help="Path to second Excel file")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated outputs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    file1 = ensure_exists(args.file1, "Excel file 1")
    file2 = ensure_exists(args.file2, "Excel file 2")
    output_dir = ensure_output_dir(args.output_dir)

    preprocess_logs(file1, file2, output_dir)
