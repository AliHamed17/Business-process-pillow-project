import argparse
from pathlib import Path

import matplotlib.pyplot as plt

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import annotate_bars, apply_rtl_text, finalize_and_save, set_plot_style, truncate_label
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import annotate_bars, apply_rtl_text, finalize_and_save, set_plot_style, truncate_label


REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']


def _save_performance_plots(case_perf, stage_wait, df, top_variants_cycle, output_dir: Path) -> None:
    set_plot_style()
    
    if top_variants_cycle and not df.empty:
        fig, ax = plt.subplots(figsize=(11, 7))
        box_data = [group for _, group in top_variants_cycle]
        labels = [truncate_label(name, 45) for name, _ in top_variants_cycle]
        
        ax.boxplot(box_data, labels=labels, showfliers=False)
        apply_rtl_text(ax, title='Cycle Time Distribution by Top 5 Most Frequent Variants', ylabel='Cycle Time (Days)')
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        
        finalize_and_save(fig, output_dir / 'variants_cycle_time_boxplot.png')
    if not case_perf.empty:
        cycle = case_perf['cycle_time_days'].dropna()
        fig, ax = plt.subplots(figsize=(8.5, 5))
        cycle.plot(kind='hist', bins=20, ax=ax, color='#4C72B0', alpha=0.75)
        if not cycle.empty:
            ax.axvline(cycle.median(), color='red', linestyle='--', linewidth=1.5, label=f"Median={cycle.median():.2f}")
            ax.axvline(cycle.quantile(0.9), color='purple', linestyle=':', linewidth=1.5, label=f"P90={cycle.quantile(0.9):.2f}")
            ax.legend(loc='best')
        apply_rtl_text(ax, title='Case Cycle Time Distribution', xlabel='Cycle Time (Days)', ylabel='Case Count')
        finalize_and_save(fig, output_dir / 'case_cycle_time_distribution.png')

    top_wait = stage_wait.dropna(subset=['mean']).head(10).copy()
    if not top_wait.empty:
        fig, ax = plt.subplots(figsize=(10, 5.5))
        labels = [
            f"{truncate_label(activity, 34)} (n={int(count)})"
            for activity, count in zip(top_wait['activity'].astype(str), top_wait['transition_count'])
        ]
        ax.barh(labels, top_wait['mean'], color='#C44E52')
        ax.invert_yaxis()
        apply_rtl_text(ax, title='Top Activities by Average Wait Time', xlabel='Average Wait Time (Days)')
        annotate_bars(ax, horizontal=True)
        finalize_and_save(fig, output_dir / 'bottleneck_top10_mean_wait.png')

    if 'wait_time_days' in df.columns:
        top_names = top_wait['activity'].astype(str).tolist()
        if top_names:
            subset = df[df['activity'].astype(str).isin(top_names)].copy().dropna(subset=['wait_time_days'])
            if not subset.empty:
                grouped = [
                    subset.loc[subset['activity'].astype(str) == name, 'wait_time_days'].values
                    for name in top_names
                ]
                fig, ax = plt.subplots(figsize=(11, 6))
                ax.boxplot(grouped, labels=[truncate_label(x, 22) for x in top_names], showfliers=False)
                apply_rtl_text(ax, title='Wait Time Distribution by Top Bottleneck Activities', ylabel='Wait Time (Days)')
                ax.tick_params(axis='x', rotation=40)
                finalize_and_save(fig, output_dir / 'bottleneck_wait_distribution_boxplot.png')

    impact = stage_wait.dropna(subset=['total_wait_days']).sort_values('total_wait_days', ascending=False).head(10).copy()
    if not impact.empty:
        impact = impact.iloc[::-1]
        impact['cumulative_pct'] = impact['total_wait_days'].cumsum() / impact['total_wait_days'].sum() * 100
        fig, ax1 = plt.subplots(figsize=(11, 6))
        labels = [truncate_label(x, 26) for x in impact['activity'].astype(str)]
        y_pos = list(range(len(labels)))
        ax1.barh(labels, impact['total_wait_days'], color='#4C72B0', alpha=0.85)
        apply_rtl_text(
            ax1,
            title='Delay Contribution by Activity',
            xlabel='Total Wait Time (Days)',
            ylabel='Activity',
        )
        ax2 = ax1.twiny()
        ax2.plot(impact['cumulative_pct'], y_pos, color='#C44E52', marker='o', linewidth=2)
        ax2.set_xlim(0, 100)
        ax2.set_xlabel('Cumulative Share of Total Delay (%)')
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels([])
        finalize_and_save(fig, output_dir / 'bottleneck_delay_contribution_pareto.png')


def analyze_performance(logfile_path, output_dir):
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='performance analysis')
    df.sort_values(['case_id', 'timestamp'], inplace=True)

    case_perf = df.groupby('case_id').agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max'),
        event_count=('activity', 'size')
    ).reset_index()

    case_perf['cycle_time_days'] = (
        case_perf['end_time'] - case_perf['start_time']
    ).dt.total_seconds() / (24 * 3600)

    df['next_timestamp'] = df.groupby('case_id')['timestamp'].shift(-1)
    df['wait_time_days'] = (
        df['next_timestamp'] - df['timestamp']
    ).dt.total_seconds() / (24 * 3600)

    stage_wait = df.groupby('activity')['wait_time_days'].agg(
        transition_count='count',
        mean='mean',
        median='median',
        std='std',
        max='max',
        total_wait_days='sum',
    ).reset_index()
    total_wait = stage_wait['total_wait_days'].sum()
    stage_wait['delay_share_pct'] = (
        stage_wait['total_wait_days'] / total_wait * 100 if total_wait else 0.0
    )
    stage_wait.sort_values(by='mean', ascending=False, inplace=True)

    # Role-level bottleneck
    if 'stage_responsible' in df.columns:
        role_wait = df.groupby('stage_responsible')['wait_time_days'].agg(['mean', 'median', 'count']).reset_index()
        role_wait.sort_values(by='mean', ascending=False, inplace=True)
        role_wait.to_csv(output_dir / 'role_bottleneck_analysis.csv', index=False)

    # User-level bottleneck
    if 'resource' in df.columns:
        user_wait = df.groupby('resource')['wait_time_days'].agg(['mean', 'median', 'count']).reset_index()
        user_wait.sort_values(by='mean', ascending=False, inplace=True)
        user_wait.to_csv(output_dir / 'user_bottleneck_analysis.csv', index=False)

    case_perf.to_csv(output_dir / 'case_performance.csv', index=False)
    stage_wait.to_csv(output_dir / 'bottleneck_analysis.csv', index=False)
    
    # Calculate variants for top 5 plot
    def summarise_path(activities):
        seen, path = set(), []
        for a in activities:
            if a not in seen:
                seen.add(a)
                path.append(a)
            if len(path) == 6:
                break
        return " -> ".join(path)

    case_variants = df.groupby('case_id')['activity'].apply(summarise_path).reset_index(name='variant')
    case_perf_v = case_perf.merge(case_variants, on='case_id')
    top_5_vars = case_perf_v['variant'].value_counts().nlargest(5).index
    
    top_variants_cycle = [
        (v, case_perf_v[case_perf_v['variant'] == v]['cycle_time_days'].dropna())
        for v in top_5_vars
    ]
    
    _save_performance_plots(case_perf, stage_wait, df, top_variants_cycle, output_dir)

    print("Performance analysis complete.")


def parse_args():
    parser = argparse.ArgumentParser(description="Run performance and bottleneck analyses")
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated outputs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    output_dir = ensure_output_dir(args.output_dir)
    analyze_performance(logfile, output_dir)
