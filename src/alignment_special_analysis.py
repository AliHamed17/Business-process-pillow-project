import pandas as pd
import os
import json

def analyze_special_alignment(logfile_path, output_dir):
    print("[Alignment Analysis] Running Parallelism & Semantic Sub-Process checks...")
    df = pd.read_csv(logfile_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 1. Parallelism Audit (Internal vs Approval Tracks)
    # Target Stages: 'בדיקת נתוני תנאי שרות' (Service Conditions) vs 'אישור' (Approvals)
    # We find cases where both exist and check if they overlap.
    
    results = {}
    
    # Identify track markers
    approval_keywords = ['אישור', 'מנהל אגף', 'ראש מינהל']
    salary_keywords = ['הדמיית שכר', 'תנאי שרות', 'שכר עידוד']
    
    # Label event tracks
    df['track'] = 'Other'
    df.loc[df['activity'].str.contains('|'.join(approval_keywords), na=False), 'track'] = 'Approval'
    df.loc[df['activity'].str.contains('|'.join(salary_keywords), na=False), 'track'] = 'Salary'
    
    parallelism_data = []
    cases = df.groupby('case_id')
    
    total_relevant = 0
    overlap_count = 0
    
    for cid, group in cases:
        app_times = group[group['track'] == 'Approval']['timestamp']
        sal_times = group[group['track'] == 'Salary']['timestamp']
        
        if not app_times.empty and not sal_times.empty:
            total_relevant += 1
            # Check for overlap: Did Salary start before Approval finished?
            app_start, app_end = app_times.min(), app_times.max()
            sal_start, sal_end = sal_times.min(), sal_times.max()
            
            # Intersection check
            if (sal_start <= app_end) and (app_start <= sal_end):
                overlap_count += 1
                
    parallelism_score = (overlap_count / total_relevant * 100) if total_relevant > 0 else 0
    results['parallel_track_concurrency'] = round(parallelism_score, 2)

    # 2. Semantic Sub-Process Analysis (Using Changed Field)
    # Identify which fields are changed most often in "Looping" stages
    if 'changed_field' in df.columns:
        # Get count of changes per field per stage
        rework_reasons = df.dropna(subset=['changed_field']).groupby(['activity', 'changed_field']).size().reset_index(name='count')
        # Sort to find top reasons for sub-processes
        top_reasons = rework_reasons.sort_values(['activity', 'count'], ascending=[True, False]).groupby('activity').head(1)
        top_reasons.to_csv(os.path.join(output_dir, 'sub_process_reasons.csv'), index=False)
        results['top_rework_field'] = top_reasons.sort_values('count', ascending=False).iloc[0]['changed_field']
    
    # 3. Outcome-Based Bottlenecks
    if 'request_status' in df.columns:
        # Compare cycle time of Approved vs Cancelled cases
        outcome_perf = df.groupby(['case_id', 'request_status'])['timestamp'].agg(['min', 'max']).reset_index()
        outcome_perf['duration'] = (outcome_perf['max'] - outcome_perf['min']).dt.total_seconds() / 86400
        
        outcome_summary = outcome_perf.groupby('request_status')['duration'].mean().to_dict()
        results['outcome_durations'] = outcome_summary

    # Save findings
    with open(os.path.join(output_dir, 'special_alignment_results.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)
        
    print("[Alignment Analysis] Special analysis complete.")

if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    logfile = os.path.join(base, "outputs", "cleaned_log.csv")
    out = os.path.join(base, "outputs")
    analyze_special_alignment(logfile, out)
