import pandas as pd
import pm4py
import numpy as np
import os
import matplotlib.pyplot as plt

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
    
    # 4) Convert "NULL" strings to NaN
    df.replace("NULL", np.nan, inplace=True)
    df.replace("—", np.nan, inplace=True)  # Using Em-dash as NaN based on exploration
    
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
    
    # Drop rows without an activity/stage name unless it's a structural creation
    # The prompt says: "Should activity be only 'Stage Name'? Or 'Stage Name + Event Type'?"
    # Justification: Stage Name represents the business step. Combining with Event Type (e.g. עדכן = update)
    # helps distinguish between the start, update, and end of a stage.
    # We will create a combined activity column for precise tracking.
    df['combined_activity'] = df['activity'].astype(str) + " - " + df['event_type'].astype(str)
    
    # For standard process discovery, we'll use just the activity, but clean up NaNs
    df['activity'] = df['activity'].fillna('Unknown Stage')
    
    # 5) Convert date columns to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['target_date'] = pd.to_datetime(df['target_date'], errors='coerce')
    
    # Stage end date seems to be float in exploration (mostly missing). Convert to empty if needed.
    
    # 6) Sort by Case ID + Timestamp
    df.sort_values(by=['case_id', 'timestamp'], inplace=True)
    
    # 8) Detect duplicate events (same case, same time, same activity, same update)
    before_drop = len(df)
    df.drop_duplicates(subset=['case_id', 'timestamp', 'activity', 'event_type', 'changed_field'], inplace=True)
    print(f"Dropped {before_drop - len(df)} duplicate rows")
    
    # Handle missing stage end dates - if not provided, we rely on the next event's timestamp
    
    # Save cleaned CSV
    output_csv = os.path.join(output_dir, 'cleaned_log.csv')
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"Cleaned CSV saved to {output_csv}")
    
    # 11) Convert to pm4py EventLog object
    # pm4py requires standard column names
    df_pm4py = pm4py.format_dataframe(df, case_id='case_id', activity_key='activity', timestamp_key='timestamp')
    try:
        event_log = pm4py.convert_to_event_log(df_pm4py)
        # 13) Save XES file
        output_xes = os.path.join(output_dir, 'event_log.xes')
        pm4py.write_xes(event_log, output_xes)
        print(f"XES saved to {output_xes}")
    except Exception as e:
        print(f"Warning: Could not save XES directly due to complex objects: {e}")
        # Simplistic XES dump
        df_simple = df[['case_id', 'timestamp', 'activity', 'resource', 'event_type']].copy()
        df_simple = pm4py.format_dataframe(df_simple, case_id='case_id', activity_key='activity', timestamp_key='timestamp')
        event_log = pm4py.convert_to_event_log(df_simple)
        output_xes = os.path.join(output_dir, 'event_log.xes')
        pm4py.write_xes(event_log, output_xes)
        print(f"Simplified XES saved to {output_xes}")
        
    return df, event_log

if __name__ == "__main__":
    bdir = r"c:\Users\ahamed\business process pillow"
    f1 = os.path.join(bdir, r"extracted_data\לוגים איוש משרה - חלק 1.xlsx")
    f2 = os.path.join(bdir, r"extracted_data\לוגים איוש משרה - חלק 2.xlsx")
    out = os.path.join(bdir, r"haifa-municipality-process-mining\outputs")
    os.makedirs(out, exist_ok=True)
    
    df, log = preprocess_logs(f1, f2, out)
