import pandas as pd
import os
import matplotlib.pyplot as plt

def analyze_workload(logfile_path, output_dir):
    df = pd.read_csv(logfile_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Analyze open cases per department per week
    df['week'] = df['timestamp'].dt.to_period('W').dt.start_time
    
    # Active workload (naive assumption: open from first event to last event)
    cases = df.groupby(['case_id', 'department']).agg(
        start=('timestamp', 'min'),
        end=('timestamp', 'max')
    ).reset_index()
    
    date_range = pd.date_range(cases['start'].min(), cases['end'].max(), freq='W')
    
    workload_data = []
    for week in date_range:
        for dept in cases['department'].unique():
            active_count = cases[(cases['department'] == dept) & 
                                 (cases['start'] <= week) & 
                                 (cases['end'] >= week)].shape[0]
            workload_data.append({'Week': week, 'Department': dept, 'Open_Cases': active_count})
            
    wl_df = pd.DataFrame(workload_data)
    
    # Moving average
    wl_df['Moving_Avg_4W'] = wl_df.groupby('Department')['Open_Cases'].transform(lambda x: x.rolling(4, min_periods=1).mean())
    
    wl_df.to_csv(os.path.join(output_dir, 'workload_analysis.csv'), index=False)
    print("Workload analysis complete.")

if __name__ == "__main__":
    out = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining\outputs"
    f = os.path.join(out, "cleaned_log.csv")
    analyze_workload(f, out)
