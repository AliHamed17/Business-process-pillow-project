import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns

def generate_preprocessing_evidence(logfile_path, output_dir):
    print("[Preprocessing Evidence] Generating charts for report...")
    df = pd.read_csv(logfile_path)
    
    plots_dir = os.path.join(output_dir, "plots", "preprocessing")
    os.makedirs(plots_dir, exist_ok=True)
    
    # 1. Event Distribution by Month (Impact of Merging Parts 1 & 2)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['month'] = df['timestamp'].dt.to_period('M').astype(str)
    
    plt.figure(figsize=(10, 5))
    df['month'].value_counts().sort_index().plot(kind='bar', color='skyblue')
    plt.title("Event Frequency by Month (Unified Log)")
    plt.ylabel("Event Count")
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "event_volume_monthly.png"))
    plt.close()
    
    # 2. Duplicate Audit
    # (Since they were already dropped, we show the scale of the original log vs cleaned)
    # We'll use a summary pie chart
    labels = ['Cleaned Records', 'Removed Duplicates']
    sizes = [len(df), 85991] # From data_preprocessing logic
    
    plt.figure(figsize=(8, 8))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#66b3ff','#ff9999'], startangle=140)
    plt.title("Data Cleaning Audit: Duplicate Removal")
    plt.savefig(os.path.join(plots_dir, "duplicate_audit_pie.png"))
    plt.close()
    
    print(f"[Preprocessing Evidence] Charts saved to {plots_dir}")

if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    logfile = os.path.join(base, "outputs", "cleaned_log.csv")
    out = os.path.join(base, "outputs")
    generate_preprocessing_evidence(logfile, out)
