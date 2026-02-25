import pandas as pd
import os
import matplotlib.pyplot as plt

def analyze_performance(logfile_path, output_dir):
    df = pd.read_csv(logfile_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Sort
    df.sort_values(['case_id', 'timestamp'], inplace=True)
    
    # Group by Case ID
    case_perf = df.groupby('case_id').agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max'),
        event_count=('activity', 'size')
    ).reset_index()
    
    case_perf['cycle_time_days'] = (case_perf['end_time'] - case_perf['start_time']).dt.total_seconds() / (24*3600)
    
    # Bottlenecks and wait times
    df['next_timestamp'] = df.groupby('case_id')['timestamp'].shift(-1)
    df['wait_time_days'] = (df['next_timestamp'] - df['timestamp']).dt.total_seconds() / (24*3600)
    
    stage_wait = df.groupby('activity')['wait_time_days'].agg(['mean', 'median', 'std', 'max']).reset_index()
    stage_wait.sort_values(by='mean', ascending=False, inplace=True)
    
    role_wait = df.groupby('stage_responsible')['wait_time_days'].agg(['mean', 'median', 'count']).reset_index()
    role_wait.sort_values(by='mean', ascending=False, inplace=True)

    user_wait = df.groupby('resource')['wait_time_days'].agg(['mean', 'median', 'count']).reset_index()
    user_wait.sort_values(by='mean', ascending=False, inplace=True)

    # Save outputs
    case_perf.to_csv(os.path.join(output_dir, 'case_performance.csv'), index=False)
    stage_wait.to_csv(os.path.join(output_dir, 'bottleneck_analysis.csv'), index=False)
    role_wait.to_csv(os.path.join(output_dir, 'role_bottleneck_analysis.csv'), index=False)
    user_wait.to_csv(os.path.join(output_dir, 'user_bottleneck_analysis.csv'), index=False)
    
    print("Performance analysis complete.")

if __name__ == "__main__":
    out = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining\outputs"
    f = os.path.join(out, "cleaned_log.csv")
    analyze_performance(f, out)
