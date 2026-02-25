import pandas as pd
import os

def analyze_responsible_change(logfile_path, output_dir):
    df = pd.read_csv(logfile_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Sort
    df.sort_values(['case_id', 'timestamp'], inplace=True)
    
    # Look for changes in responsible person
    # Prompt: changed_field indicates responsible reassignment or stage_responsible changes
    df['prev_responsible'] = df.groupby('case_id')['stage_responsible'].shift(1)
    df['responsible_changed'] = (df['stage_responsible'] != df['prev_responsible']) & (df['prev_responsible'].notna())
    
    # Additionally check changed_field
    df['responsible_change_flag'] = df['changed_field'].astype(str).str.contains('אחראי', na=False) | df['responsible_changed']
    
    case_changes = df.groupby('case_id').agg(
        reassignment_count=('responsible_change_flag', 'sum'),
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    ).reset_index()
    
    case_changes['cycle_time_days'] = (case_changes['end_time'] - case_changes['start_time']).dt.total_seconds() / (24*3600)
    
    # Comparison
    case_changes['has_reassignment'] = case_changes['reassignment_count'] > 0
    comparison = case_changes.groupby('has_reassignment')['cycle_time_days'].agg(['count', 'mean', 'median', 'std']).reset_index()
    
    comparison.to_csv(os.path.join(output_dir, 'responsible_change_analysis.csv'), index=False)
    print("Responsible Change analysis complete.")

if __name__ == "__main__":
    out = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining\outputs"
    f = os.path.join(out, "cleaned_log.csv")
    analyze_responsible_change(f, out)
