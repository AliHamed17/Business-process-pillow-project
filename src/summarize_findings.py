import pandas as pd
import os

repo_dir = r'c:\Users\ahamed\business process pillow\haifa-municipality-process-mining'
d = os.path.join(repo_dir, 'outputs')
out_report = os.path.join(repo_dir, 'analysis_findings.txt')

with open(out_report, 'w', encoding='utf-8') as f:
    f.write("PROCESS MINING ANALYSIS FINDINGS\n")
    f.write("================================\n\n")

    # Bottlenecks
    try:
        df = pd.read_csv(os.path.join(d, 'bottleneck_analysis.csv'))
        f.write("TOP 10 BOTTLENECK STAGES (by average wait time in days):\n")
        f.write(df.sort_values(by='mean', ascending=False).head(10).to_string())
        f.write("\n\n")
    except Exception as e:
        f.write(f"Error reading bottlenecks: {e}\n\n")

    # Variants
    try:
        df = pd.read_csv(os.path.join(d, 'variants.csv'))
        f.write("TOP 10 PROCESS VARIANTS:\n")
        f.write(df.head(10).to_string())
        f.write("\n\n")
    except Exception as e:
        f.write(f"Error reading variants: {e}\n\n")

    # Internal Process
    try:
        df = pd.read_csv(os.path.join(d, 'internal_process_analysis.csv'))
        f.write("INTERNAL COMPLEXITY (Rework within stages):\n")
        f.write(df.sort_values(by='rework_ratio', ascending=False).head(10).to_string())
        f.write("\n\n")
    except Exception as e:
        f.write(f"Error reading internal process: {e}\n\n")

    # Responsible Change
    try:
        df = pd.read_csv(os.path.join(d, 'responsible_change_analysis.csv'))
        f.write("RESPONSIBLE CHANGE IMPACT ON CYCLE TIME (Days):\n")
        f.write(df.to_string())
        f.write("\n\n")
    except Exception as e:
        f.write(f"Error reading responsible change: {e}\n\n")

    # Performance summary
    try:
        df = pd.read_csv(os.path.join(d, 'case_performance.csv'))
        f.write("GENERAL PERFORMANCE SUMMARY (Cycle Time Days):\n")
        f.write(df['cycle_time_days'].describe().to_string())
        f.write("\n")
    except Exception as e:
        f.write(f"Error reading performance: {e}\n")

print(f"Summary written to {out_report}")
