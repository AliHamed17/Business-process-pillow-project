import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pm4py

from cli_utils import ensure_exists, ensure_output_dir


def preprocess_logs(file_path1, file_path2, output_dir):
    """
    Reads, cleans, and merges process logs into a structured Event Log.
    """
    print("Reading Excel files...")
    df1 = pd.read_excel(file_path1)
    df2 = pd.read_excel(file_path2)

    # Concatenate
    df = pd.concat([df1, df2], ignore_index=True)

    print(f"Initial shape: {df.shape}")

    # Convert common placeholders to NaN
    df.replace("NULL", np.nan, inplace=True)
    df.replace("—", np.nan, inplace=True)

    # Rename columns to standard english for easier processing
    col_mapping = {
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
        'ערכים שהשתנו (גולמי)': 'raw_changed_values'
    }
    df.rename(columns=col_mapping, inplace=True)

    # Build combined activity for optional downstream use
    df['combined_activity'] = df['activity'].astype(str) + " - " + df['event_type'].astype(str)

    # For standard process discovery, we'll use just the activity, but clean up NaNs
    df['activity'] = df['activity'].fillna('Unknown Stage')

    # Convert date columns to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['target_date'] = pd.to_datetime(df['target_date'], errors='coerce')

    # Sort by Case ID + Timestamp
    df.sort_values(by=['case_id', 'timestamp'], inplace=True)

    # Detect duplicate events (same case, same time, same activity, same update)
    before_drop = len(df)
    df.drop_duplicates(subset=['case_id', 'timestamp', 'activity', 'event_type', 'changed_field'], inplace=True)
    print(f"Dropped {before_drop - len(df)} duplicate rows")

    # Save cleaned CSV
    output_csv = Path(output_dir) / 'cleaned_log.csv'
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"Cleaned CSV saved to {output_csv}")

    # Convert to pm4py EventLog object
    df_pm4py = pm4py.format_dataframe(df, case_id='case_id', activity_key='activity', timestamp_key='timestamp')
    try:
        event_log = pm4py.convert_to_event_log(df_pm4py)
        output_xes = Path(output_dir) / 'event_log.xes'
        pm4py.write_xes(event_log, output_xes)
        print(f"XES saved to {output_xes}")
    except Exception as e:
        print(f"Warning: Could not save XES directly due to complex objects: {e}")
        df_simple = df[['case_id', 'timestamp', 'activity', 'resource', 'event_type']].copy()
        df_simple = pm4py.format_dataframe(df_simple, case_id='case_id', activity_key='activity', timestamp_key='timestamp')
        event_log = pm4py.convert_to_event_log(df_simple)
        output_xes = Path(output_dir) / 'event_log.xes'
        pm4py.write_xes(event_log, output_xes)
        print(f"Simplified XES saved to {output_xes}")

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
