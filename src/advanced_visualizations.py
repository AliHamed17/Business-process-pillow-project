import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
import squarify
import pm4py

seaborn_style = {"axes.spines.right": False, "axes.spines.top": False}
sns.set_theme(style="whitegrid", rc=seaborn_style)


def generate_advanced_plots(logfile_path, output_dir):
    print("[Advanced Viz] Loading and preparing data...")
    df = pd.read_csv(logfile_path, encoding='utf-8-sig')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])

    plots_dir = os.path.join(output_dir, "plots", "advanced")
    os.makedirs(plots_dir, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 1. Violin Plot – Cycle Time Distribution by Top 10 Departments
    # ------------------------------------------------------------------ #
    print("[Advanced Viz] Plot 1: Cycle Time Violin by Department...")
    case_perf = df.groupby(['case_id', 'department']).agg(
        start=('timestamp', 'min'),
        end=('timestamp', 'max')
    ).reset_index()
    case_perf['cycle_days'] = (
        (case_perf['end'] - case_perf['start']).dt.total_seconds() / 86400
    )

    top_depts = case_perf['department'].value_counts().head(10).index
    subset_depts = case_perf[case_perf['department'].isin(top_depts)].copy()
    # Cap extreme outliers for readability
    cap = subset_depts['cycle_days'].quantile(0.95)
    subset_depts['cycle_days'] = subset_depts['cycle_days'].clip(upper=cap)

    fig, ax = plt.subplots(figsize=(13, 6))
    sns.violinplot(
        data=subset_depts, x='department', y='cycle_days',
        inner="quart", hue='department', palette="muted", legend=False, ax=ax
    )
    ax.tick_params(axis='x', rotation=40, labelsize=8)
    ax.set_title("Cycle Time Distribution – Top 10 Departments\n(capped at P95 for readability)", fontsize=13)
    ax.set_ylabel("Cycle Time (Days)")
    ax.set_xlabel("")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "dept_cycle_time_violin.png"), dpi=200)
    plt.close()
    print("  Saved: dept_cycle_time_violin.png")

    # ------------------------------------------------------------------ #
    # 2. Monthly Trend – Process Load Over Time
    # ------------------------------------------------------------------ #
    print("[Advanced Viz] Plot 2: Monthly Load Trend...")
    df['month_year'] = df['timestamp'].dt.to_period('M')
    monthly_stats = df.groupby('month_year').agg(
        event_count=('activity', 'count'),
        unique_cases=('case_id', 'nunique')
    ).reset_index()
    monthly_stats['month_year'] = monthly_stats['month_year'].astype(str)

    fig, ax1 = plt.subplots(figsize=(13, 5))
    ax2 = ax1.twinx()
    ax1.fill_between(
        monthly_stats['month_year'],
        monthly_stats['unique_cases'],
        color='crimson', alpha=0.15
    )
    ax1.plot(
        monthly_stats['month_year'], monthly_stats['unique_cases'],
        marker='o', color='crimson', linewidth=2, label='Unique Cases'
    )
    ax2.bar(
        monthly_stats['month_year'], monthly_stats['event_count'],
        color='steelblue', alpha=0.3, label='Total Events'
    )
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Active Cases", color='crimson')
    ax2.set_ylabel("Event Volume", color='steelblue')
    ax1.tick_params(axis='x', rotation=45, labelsize=8)
    ax1.set_title("Monthly Recruitment Activity – Cases & Event Volume", fontsize=13)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "monthly_load_trend.png"), dpi=200)
    plt.close()
    print("  Saved: monthly_load_trend.png")

    # ------------------------------------------------------------------ #
    # 3. Efficiency Frontier – Resource Workload vs. Avg Delay
    # ------------------------------------------------------------------ #
    print("[Advanced Viz] Plot 3: Resource Efficiency Frontier...")
    df['next_ts'] = df.groupby('case_id')['timestamp'].shift(-1)
    df['wait_days'] = (df['next_ts'] - df['timestamp']).dt.total_seconds() / 86400

    res_perf = df.groupby('stage_responsible').agg(
        workload=('case_id', 'nunique'),
        avg_wait=('wait_days', 'mean')
    ).reset_index()
    res_perf = res_perf[res_perf['workload'] > 5]
    # Cap avg_wait at 95th pct for readability
    wait_cap = res_perf['avg_wait'].quantile(0.95)
    res_perf['avg_wait'] = res_perf['avg_wait'].clip(upper=wait_cap)

    fig, ax = plt.subplots(figsize=(11, 7))
    scatter = ax.scatter(
        res_perf['workload'], res_perf['avg_wait'],
        s=res_perf['workload'] * 2,
        c=res_perf['avg_wait'],
        cmap='RdYlGn_r', alpha=0.7, edgecolors='grey', linewidths=0.5
    )
    plt.colorbar(scatter, ax=ax, label='Avg Wait (days)')

    # Label top-10 by workload
    for _, row in res_perf.nlargest(10, 'workload').iterrows():
        label = str(row['stage_responsible'])[:25]
        ax.annotate(label, (row['workload'], row['avg_wait']),
                    fontsize=7, alpha=0.85,
                    xytext=(4, 4), textcoords='offset points')

    ax.set_xlabel("Workload (Unique Cases Handled)")
    ax.set_ylabel("Avg Handling Delay (Days)")
    ax.set_title("Resource Efficiency Frontier\n(High-right = bottleneck; Low-left = efficient)", fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "resource_efficiency_frontier.png"), dpi=200)
    plt.close()
    print("  Saved: resource_efficiency_frontier.png")

    # ------------------------------------------------------------------ #
    # 4. Variant Treemap – Top Process Paths by Frequency
    # ------------------------------------------------------------------ #
    print("[Advanced Viz] Plot 4: Variant Treemap...")
    # Build variant paths per case (first 6 distinct stages to keep readable)
    def summarise_path(activities):
        seen, path = set(), []
        for a in activities:
            if a not in seen:
                seen.add(a)
                path.append(a)
            if len(path) == 6:
                break
        return " → ".join(path)

    variant_series = (
        df.sort_values(['case_id', 'timestamp'])
          .groupby('case_id')['activity']
          .apply(summarise_path)
    )
    top_variants = variant_series.value_counts().head(15).reset_index()
    top_variants.columns = ['path', 'count']
    top_variants['label'] = [
        f"V{i+1}\n({c} cases)" for i, c in enumerate(top_variants['count'])
    ]

    fig, ax = plt.subplots(figsize=(13, 8))
    colors = sns.color_palette("Spectral", len(top_variants))
    squarify.plot(
        sizes=top_variants['count'],
        label=top_variants['label'],
        alpha=0.85, color=colors,
        text_kwargs={'fontsize': 8},
        ax=ax
    )
    ax.axis('off')
    ax.set_title("Top 15 Process Variant Paths (Area = Case Count)", fontsize=13, pad=10)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "variant_treemap.png"), dpi=200)
    plt.close()
    print("  Saved: variant_treemap.png")

    # ------------------------------------------------------------------ #
    # 5. Stage Wait-Time Heatmap – Bottleneck Heat by Stage & Month
    # ------------------------------------------------------------------ #
    print("[Advanced Viz] Plot 5: Stage x Month Wait-Time Heatmap...")
    top_stages = (
        df.groupby('activity')['wait_days'].mean()
          .nlargest(12).index.tolist()
    )
    df_top = df[df['activity'].isin(top_stages)].copy()
    df_top['month'] = df_top['timestamp'].dt.strftime('%Y-%m')

    pivot = (
        df_top.groupby(['activity', 'month'])['wait_days']
              .mean()
              .unstack(fill_value=0)
    )
    # Shorten Hebrew labels for the axis
    short_labels = {s: s[:30] for s in pivot.index}
    pivot.index = [short_labels[s] for s in pivot.index]

    fig, ax = plt.subplots(figsize=(14, 7))
    sns.heatmap(
        pivot, cmap='YlOrRd', linewidths=0.3,
        cbar_kws={'label': 'Avg Wait (days)'}, ax=ax
    )
    ax.set_title("Stage Bottleneck Heat Map – Avg Wait by Month", fontsize=13)
    ax.set_xlabel("Month")
    ax.set_ylabel("Stage")
    ax.tick_params(axis='x', rotation=45, labelsize=7)
    ax.tick_params(axis='y', labelsize=7)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "stage_bottleneck_heatmap.png"), dpi=200)
    plt.close()
    print("  Saved: stage_bottleneck_heatmap.png")

    print(f"\n[Advanced Viz] All plots saved to {plots_dir}")
    return plots_dir


if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    logfile = os.path.join(base, "outputs", "cleaned_log.csv")
    outdir = os.path.join(base, "outputs")
    generate_advanced_plots(logfile, outdir)
