import pandas as pd
import os

def analyze_internal_process(logfile_path, output_dir):
    df = pd.read_csv(logfile_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.sort_values(['case_id', 'timestamp'], inplace=True)
    
    # Internal process is defined as multiple updates within the same stage
    # Group by case and stage, count events
    internal_updates = df.groupby(['case_id', 'activity']).agg(
        event_count=('event_type', 'count'),
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    ).reset_index()
    
    # Filter for stages that had multiple events
    internal_updates['is_internal_rework'] = internal_updates['event_count'] > 1
    internal_updates['stage_duration_days'] = (internal_updates['end_time'] - internal_updates['start_time']).dt.total_seconds() / (24*3600)
    
    # Summarize by stage
    stage_complexity = internal_updates.groupby('activity').agg(
        total_cases=('case_id', 'count'),
        cases_with_rework=('is_internal_rework', 'sum'),
        avg_events_per_case=('event_count', 'mean'),
        avg_duration_days=('stage_duration_days', 'mean')
    ).reset_index()
    
    stage_complexity['rework_ratio'] = stage_complexity['cases_with_rework'] / stage_complexity['total_cases']
    stage_complexity.sort_values(by='avg_events_per_case', ascending=False, inplace=True)
    
    stage_complexity.to_csv(os.path.join(output_dir, 'internal_process_analysis.csv'), index=False)
    print("Internal Process analysis complete.")

if __name__ == "__main__":
    out = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining\outputs"
    f = os.path.join(out, "cleaned_log.csv")
    analyze_internal_process(f, out)
