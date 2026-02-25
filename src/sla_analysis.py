import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_sla_compliance(logfile_path, output_dir):
    print("[SLA Analysis] Comparing Target Dates vs. Completion Dates...")
    df = pd.read_csv(logfile_path)
    
    # Ensure date columns are formatted
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # In the provided log description, 'Target Date' and 'Completion Date' are key.
    # Note: If these fields were empty in the raw log, we use our calculated durations.
    # But often 'Target Date' is a column we can compare against the current timestamp.
    
    if 'target_date' in df.columns:
        df['target_date'] = pd.to_datetime(df['target_date'], errors='coerce')
        df = df.dropna(subset=['target_date'])
        
        # A stage is "Overdue" if the timestamp (event time) is later than the target date
        df['is_late'] = df['timestamp'] > df['target_date']
        df['delay_from_target'] = (df['timestamp'] - df['target_date']).dt.total_seconds() / 86400
        
        sla_stats = df.groupby('activity').agg(
            total_events=('case_id', 'count'),
            late_events=('is_late', 'sum'),
            avg_delay_days=('delay_from_target', 'mean')
        ).reset_index()
        
        sla_stats['compliance_rate'] = (1 - (sla_stats['late_events'] / sla_stats['total_events'])) * 100
        sla_stats.sort_values('compliance_rate', inplace=True)
        
        sla_stats.to_csv(os.path.join(output_dir, 'sla_performance.csv'), index=False)
        print(f"[SLA Analysis] Compliance report saved.")
        
        # Plot
        plt.figure(figsize=(10, 6))
        sns.barplot(data=sla_stats.head(10), x='compliance_rate', y='activity', palette='RdYlGn')
        plt.title("Top 10 Stages with Lowest SLA Compliance")
        plt.xlabel("Compliance Rate (%)")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "plots", "advanced", "sla_compliance_bars.png"))
        plt.close()
    else:
        print("[SLA Analysis] Warning: 'target_date' column not found in cleaned log. Skipping SLA comparison.")

if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    logfile = os.path.join(base, "outputs", "cleaned_log.csv")
    out = os.path.join(base, "outputs")
    analyze_sla_compliance(logfile, out)
