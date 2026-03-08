
import argparse
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
import pm4py

try:
    from cli_utils import ensure_exists, ensure_output_dir
    from plot_utils import save_plot
except ModuleNotFoundError:
    from .cli_utils import ensure_exists, ensure_output_dir
    from .plot_utils import save_plot


def analyze_department_performance(log_path, output_dir):
    """
    Generates a department-level performance dashboard.

    - Average case cycle time per department.
    - Case status distribution per department.
    - Inter-departmental handover heatmap.
    """
    df = pd.read_csv(log_path, parse_dates=['timestamp'])
    output_dir = Path(output_dir)

    # 1. Average case cycle time per department
    case_cycle_time = pm4py.business_hours.cases.get_case_arrival_and_end_time(df, 
                                                                                case_id_key='case_id',
                                                                                timestamp_key='timestamp')
    case_cycle_time['cycle_time_days'] = (case_cycle_time['end_time'] - case_cycle_time['start_time']).dt.days
    
    # Get the department for each case. A case can have multiple departments, we take the last one.
    case_department = df.groupby('case_id')['department'].last().reset_index()
    
    case_cycle_time_with_dept = pd.merge(case_cycle_time, case_department, on='case_id')
    
    avg_cycle_time_per_dept = case_cycle_time_with_dept.groupby('department')['cycle_time_days'].mean().sort_values(ascending=False)

    plt.figure(figsize=(12, 8))
    avg_cycle_time_per_dept.plot(kind='barh')
    plt.xlabel('Average Cycle Time (days)')
    plt.ylabel('Department')
    plt.title('Average Case Cycle Time per Department')
    plt.tight_layout()
    save_plot(plt, 'department_avg_cycle_time.png', output_dir)
    plt.close()


    # 2. Case status distribution per department
    # Get the latest status for each case
    case_status = df.sort_values('timestamp').groupby('case_id')['request_status'].last().reset_index()
    case_status_dept = pd.merge(case_status, case_department, on='case_id')
    
    status_distribution = case_status_dept.groupby(['department', 'request_status']).size().unstack(fill_value=0)
    
    plt.figure(figsize=(14, 10))
    status_distribution.plot(kind='bar', stacked=True, figsize=(14, 10))
    plt.xlabel('Department')
    plt.ylabel('Number of Cases')
    plt.title('Case Status Distribution per Department')
    plt.xticks(rotation=45, ha='right')
    plt.legend(title='Request Status')
    plt.tight_layout()
    save_plot(plt, 'department_case_status.png', output_dir)
    plt.close()


    # 3. Inter-departmental handover heatmap
    df_sorted = df.sort_values(by=['case_id', 'timestamp'])
    df_sorted['next_department'] = df_sorted.groupby('case_id')['department'].shift(-1)
    
    handovers = df_sorted.dropna(subset=['department', 'next_department'])
    handovers = handovers[handovers['department'] != handovers['next_department']]
    
    handover_counts = handovers.groupby(['department', 'next_department']).size().unstack(fill_value=0)

    if not handover_counts.empty:
        plt.figure(figsize=(12, 10))
        sns.heatmap(handover_counts, annot=True, fmt='d', cmap='viridis')
        plt.xlabel('To Department')
        plt.ylabel('From Department')
        plt.title('Inter-Departmental Handover Matrix')
        plt.tight_layout()
        save_plot(plt, 'department_handover_heatmap.png', output_dir)
        plt.close()
    else:
        print("No inter-departmental handovers found to generate a heatmap.")


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze department-level performance.")
    parser.add_argument("log_path", help="Path to the cleaned event log CSV file.")
    parser.add_argument("--output-dir", default="outputs/plots/advanced", help="Directory for generated plots.")
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    log_file = ensure_exists(args.log_path)
    output_dir = ensure_output_dir(args.output_dir)
    analyze_department_performance(log_file, output_dir)
    print(f"Department performance analysis plots saved to {output_dir}")
