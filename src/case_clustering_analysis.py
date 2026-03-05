"""
Case Clustering Analysis
========================
Uses K-Means clustering to segment cases based on:
1. Cycle time (duration)
2. Number of events
3. Total reassignments
4. Internal rework events

Outputs:
  - case_clusters.csv  : The cluster assignments mapping for every case
  - cluster_profiles.png : Visual boxplots describing each cluster
"""

import argparse
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

import matplotlib
matplotlib.use('Agg')

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import finalize_and_save, set_plot_style
except ModuleNotFoundError:
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import finalize_and_save, set_plot_style

REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']

def analyze_case_clusters(logfile_path, output_dir):
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='case clustering')
    df.sort_values(['case_id', 'timestamp'], inplace=True)
    
    # 1. Feature Engineering per case
    case_features = df.groupby('case_id').agg(
        event_count=('activity', 'size'),
        case_start=('timestamp', 'min'),
        case_end=('timestamp', 'max')
    ).reset_index()
    
    case_features['cycle_time_days'] = (case_features['case_end'] - case_features['case_start']).dt.total_seconds() / (24*3600)
    
    # If possible, add reassignments
    if 'stage_responsible' in df.columns:
        df['prev_resp'] = df.groupby('case_id')['stage_responsible'].shift(1)
        df['is_reassignment'] = (df['stage_responsible'] != df['prev_resp']) & df['prev_resp'].notna()
        reassigns = df.groupby('case_id')['is_reassignment'].sum().reset_index(name='reassignment_count')
        case_features = case_features.merge(reassigns, on='case_id', how='left')
    else:
        case_features['reassignment_count'] = 0

    # Fill NaNs and prepare matrix
    features_to_cluster = ['event_count', 'cycle_time_days', 'reassignment_count']
    X = case_features[features_to_cluster].fillna(0).values
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Run K-Means (4 clusters chosen via heuristic)
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    case_features['cluster'] = kmeans.fit_predict(X_scaled)
    
    # Assign human-readable labels based on cycle time means
    cluster_means = case_features.groupby('cluster')['cycle_time_days'].mean().sort_values()
    size_map = {
        cluster_means.index[0]: 'Fast/Simple',
        cluster_means.index[1]: 'Average',
        cluster_means.index[2]: 'Complex/Slow',
        cluster_means.index[3]: 'Extreme Outliers'
    }
    case_features['cluster_profile'] = case_features['cluster'].map(size_map)
    
    # Save CSV
    case_features.to_csv(output_dir / 'case_clusters.csv', index=False, encoding='utf-8-sig')
    
    # Visualization
    set_plot_style()
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    for idx, feature in enumerate(features_to_cluster):
        groups = [case_features[case_features['cluster_profile'] == profile][feature].values 
                  for profile in ['Fast/Simple', 'Average', 'Complex/Slow', 'Extreme Outliers']]
        
        axes[idx].boxplot(groups, labels=['Fast', 'Avg', 'Complex', 'Outliers'])
        axes[idx].set_title(f'Distribution of {feature}')
        axes[idx].set_ylabel(feature)

    plt.tight_layout()
    finalize_and_save(fig, output_dir / 'cluster_profiles.png')
    
    print(f"[Case Clustering] Assigned {len(case_features)} cases into 4 distinct profiles.")

def parse_args():
    parser = argparse.ArgumentParser(description="Segment cases into distinct performance clusters")
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs", help="Output directory")
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    output_dir = ensure_output_dir(args.output_dir)
    analyze_case_clusters(logfile, output_dir)
