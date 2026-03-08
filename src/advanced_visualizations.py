import os
import sys

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import squarify

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from plot_utils import apply_rtl_text, finalize_and_save, set_plot_style, truncate_label
except ImportError:
    def truncate_label(text, max_len=40):
        text = str(text)
        return text if len(text) <= max_len else text[: max_len - 3] + '...'

    def apply_rtl_text(ax, *, title=None, xlabel=None, ylabel=None):
        if title is not None:
            ax.set_title(str(title))
        if xlabel is not None:
            ax.set_xlabel(str(xlabel))
        if ylabel is not None:
            ax.set_ylabel(str(ylabel))

    def set_plot_style():
        sns.set_theme(style='whitegrid')

    def finalize_and_save(fig, output_path, dpi=150):
        fig.tight_layout()
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)


def _summarise_path(activities, max_steps: int = 6) -> str:
    seen = set()
    path = []
    for activity in activities:
        if activity not in seen:
            seen.add(activity)
            path.append(str(activity))
        if len(path) == max_steps:
            break
    return ' -> '.join(path)


def _variant_label(path: str, count: int, share_pct: float) -> str:
    return f"{truncate_label(path, 54)}\n{count} cases ({share_pct:.1f}%)"


def generate_advanced_plots(logfile_path, output_dir):
    print("[Advanced Viz] Loading and preparing data...")
    set_plot_style()
    df = pd.read_csv(logfile_path, encoding='utf-8-sig')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp']).copy()

    plots_dir = os.path.join(output_dir, "plots", "advanced")
    os.makedirs(plots_dir, exist_ok=True)

    case_perf = df.groupby(['case_id', 'department']).agg(
        start=('timestamp', 'min'),
        end=('timestamp', 'max')
    ).reset_index()
    case_perf['cycle_days'] = (
        (case_perf['end'] - case_perf['start']).dt.total_seconds() / 86400
    )

    df['next_ts'] = df.groupby('case_id')['timestamp'].shift(-1)
    df['wait_days'] = (df['next_ts'] - df['timestamp']).dt.total_seconds() / 86400

    print("[Advanced Viz] Plot 1: Cycle Time Violin by Department...")
    top_depts = case_perf['department'].value_counts().head(10).index
    subset_depts = case_perf[case_perf['department'].isin(top_depts)].copy()
    cap = subset_depts['cycle_days'].quantile(0.95)
    subset_depts['cycle_days'] = subset_depts['cycle_days'].clip(upper=cap)

    fig, ax = plt.subplots(figsize=(13, 6))
    sns.violinplot(
        data=subset_depts,
        x='department',
        y='cycle_days',
        inner='quart',
        hue='department',
        palette='muted',
        legend=False,
        ax=ax,
    )
    labels = [truncate_label(label.get_text(), 24) for label in ax.get_xticklabels()]
    ax.set_xticklabels(labels, rotation=25, ha='right')
    apply_rtl_text(
        ax,
        title='Cycle Time Distribution by Department (Top 10, capped at P95)',
        xlabel='',
        ylabel='Cycle Time (Days)',
    )
    finalize_and_save(fig, os.path.join(plots_dir, "dept_cycle_time_violin.png"), dpi=200)
    print("  Saved: dept_cycle_time_violin.png")

    print("[Advanced Viz] Plot 2: Monthly Load Trend...")
    df['month_year'] = df['timestamp'].dt.to_period('M').astype(str)
    monthly_stats = df.groupby('month_year').agg(
        event_count=('activity', 'count'),
        unique_cases=('case_id', 'nunique')
    ).reset_index()

    fig, ax1 = plt.subplots(figsize=(13, 5))
    ax2 = ax1.twinx()
    ax1.fill_between(monthly_stats['month_year'], monthly_stats['unique_cases'], color='crimson', alpha=0.15)
    ax1.plot(
        monthly_stats['month_year'],
        monthly_stats['unique_cases'],
        marker='o',
        color='crimson',
        linewidth=2,
        label='Unique Cases',
    )
    ax2.bar(
        monthly_stats['month_year'],
        monthly_stats['event_count'],
        color='steelblue',
        alpha=0.3,
        label='Total Events',
    )
    apply_rtl_text(ax1, title='Monthly Recruitment Activity', xlabel='Month', ylabel='Active Cases')
    ax2.set_ylabel('Event Volume', color='steelblue')
    ax1.tick_params(axis='x', rotation=45, labelsize=8)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)
    finalize_and_save(fig, os.path.join(plots_dir, "monthly_load_trend.png"), dpi=200)
    print("  Saved: monthly_load_trend.png")

    print("[Advanced Viz] Plot 3: Resource Efficiency Frontier...")
    res_perf = df.groupby('stage_responsible').agg(
        workload=('case_id', 'nunique'),
        avg_wait=('wait_days', 'mean')
    ).reset_index()
    res_perf = res_perf[res_perf['workload'] > 5].dropna(subset=['avg_wait']).copy()
    if not res_perf.empty:
        wait_cap = res_perf['avg_wait'].quantile(0.95)
        res_perf['avg_wait'] = res_perf['avg_wait'].clip(upper=wait_cap)

        fig, ax = plt.subplots(figsize=(11, 7))
        scatter = ax.scatter(
            res_perf['workload'],
            res_perf['avg_wait'],
            s=res_perf['workload'] * 2,
            c=res_perf['avg_wait'],
            cmap='RdYlGn_r',
            alpha=0.75,
            edgecolors='grey',
            linewidths=0.5,
        )
        ax.axvline(res_perf['workload'].median(), color='grey', linestyle='--', linewidth=1)
        ax.axhline(res_perf['avg_wait'].median(), color='grey', linestyle='--', linewidth=1)
        plt.colorbar(scatter, ax=ax, label='Average Wait (Days)')

        for _, row in res_perf.nlargest(10, 'workload').iterrows():
            ax.annotate(
                truncate_label(row['stage_responsible'], 24),
                (row['workload'], row['avg_wait']),
                fontsize=7,
                xytext=(4, 4),
                textcoords='offset points',
            )

        apply_rtl_text(
            ax,
            title='Resource Efficiency Frontier',
            xlabel='Workload (Unique Cases Handled)',
            ylabel='Average Wait (Days)',
        )
        finalize_and_save(fig, os.path.join(plots_dir, "resource_efficiency_frontier.png"), dpi=200)
        print("  Saved: resource_efficiency_frontier.png")

    print("[Advanced Viz] Plot 4: Variant Treemap...")
    variant_series = (
        df.sort_values(['case_id', 'timestamp'])
        .groupby('case_id')['activity']
        .apply(_summarise_path)
    )
    top_variants = variant_series.value_counts().head(15).reset_index()
    top_variants.columns = ['path', 'count']
    total = top_variants['count'].sum()
    top_variants['share_pct'] = top_variants['count'] / total * 100 if total else 0.0
    top_variants['label'] = [
        _variant_label(path, count, share)
        for path, count, share in top_variants[['path', 'count', 'share_pct']].itertuples(index=False)
    ]

    fig, ax = plt.subplots(figsize=(13, 8))
    colors = sns.color_palette('Spectral', len(top_variants))
    squarify.plot(
        sizes=top_variants['count'],
        label=top_variants['label'],
        alpha=0.85,
        color=colors,
        text_kwargs={'fontsize': 8},
        ax=ax,
    )
    ax.axis('off')
    apply_rtl_text(ax, title='Top Variant Paths (Area = Case Count)')
    finalize_and_save(fig, os.path.join(plots_dir, "variant_treemap.png"), dpi=200)
    print("  Saved: variant_treemap.png")

    print("[Advanced Viz] Plot 5: Stage x Role Wait-Time Heatmap...")
    top_stages = df.groupby('activity')['wait_days'].mean().nlargest(10).index.tolist()
    top_roles = (
        df.groupby('stage_responsible')['case_id']
        .nunique()
        .sort_values(ascending=False)
        .head(8)
        .index.tolist()
    )
    df_top = df[df['activity'].isin(top_stages) & df['stage_responsible'].isin(top_roles)].copy()
    pivot = (
        df_top.groupby(['activity', 'stage_responsible'])['wait_days']
        .mean()
        .unstack(fill_value=0)
    )
    if not pivot.empty:
        pivot.index = [truncate_label(label, 28) for label in pivot.index]
        pivot.columns = [truncate_label(label, 24) for label in pivot.columns]

        fig, ax = plt.subplots(figsize=(14, 7))
        sns.heatmap(
            pivot,
            cmap='YlOrRd',
            linewidths=0.3,
            cbar_kws={'label': 'Average Wait (Days)'},
            ax=ax,
        )
        apply_rtl_text(ax, title='Stage-Role Bottleneck Heatmap', xlabel='Role', ylabel='Stage')
        ax.tick_params(axis='x', rotation=35, labelsize=8)
        ax.tick_params(axis='y', labelsize=8)
        finalize_and_save(fig, os.path.join(plots_dir, "stage_bottleneck_heatmap.png"), dpi=200)
        print("  Saved: stage_bottleneck_heatmap.png")

    print(f"\n[Advanced Viz] All plots saved to {plots_dir}")
    return plots_dir


if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    logfile = os.path.join(base, "outputs", "cleaned_log.csv")
    outdir = os.path.join(base, "outputs")
    generate_advanced_plots(logfile, outdir)
