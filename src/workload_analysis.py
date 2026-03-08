import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import annotate_bars, apply_rtl_text, finalize_and_save, fix_hebrew, set_plot_style, truncate_label
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import annotate_bars, apply_rtl_text, finalize_and_save, fix_hebrew, set_plot_style, truncate_label


REQUIRED_COLUMNS = ['case_id', 'department', 'timestamp', 'activity']


def _save_workload_plots(wl_df: pd.DataFrame, workload_summary: pd.DataFrame, output_dir: Path) -> None:
    if wl_df.empty:
        return

    set_plot_style()
    fig, ax = plt.subplots(figsize=(11.5, 5.5))
    focus_depts = (
        wl_df.groupby('Department')['Open_Cases']
        .max()
        .sort_values(ascending=False)
        .head(8)
        .index
    )
    focused = wl_df[wl_df['Department'].isin(focus_depts)].copy()
    for dept, group in focused.groupby('Department'):
        group = group.sort_values('Week')
        ax.plot(
            group['Week'],
            group['Moving_Avg_4W'],
            linewidth=2.2,
            label=truncate_label(dept, 28),
        )
    apply_rtl_text(ax, title='Open Cases by Department (4-Week Moving Average)', xlabel='Week', ylabel='Open Cases')
    ax.legend(loc='upper left', fontsize=8, ncol=2)
    finalize_and_save(fig, output_dir / 'workload_trend_by_department.png')

    # Department-week heatmap
    top_heatmap_depts = (
        wl_df.groupby('Department')['Open_Cases']
        .mean()
        .sort_values(ascending=False)
        .head(15)
        .index
    )
    pivot = (
        wl_df[wl_df['Department'].isin(top_heatmap_depts)]
        .pivot_table(index='Department', columns='Week', values='Open_Cases', aggfunc='mean')
        .fillna(0)
    )
    if not pivot.empty:
        fig, ax = plt.subplots(figsize=(11, max(4, len(pivot) * 0.4)))
        im = ax.imshow(pivot.values, aspect='auto', cmap='YlOrRd')
        apply_rtl_text(ax, title='Department Workload Heatmap', xlabel='Week Index', ylabel='Department')
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels([truncate_label(x, 28) for x in pivot.index], fontsize=8)
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in pivot.columns], rotation=45, ha='right', fontsize=7)
        fig.colorbar(im, ax=ax, label='Avg Open Cases')
        finalize_and_save(fig, output_dir / 'workload_heatmap_department_week.png')

    if not workload_summary.empty:
        fig, ax = plt.subplots(figsize=(9.5, 6))
        scatter = ax.scatter(
            workload_summary['avg_open_cases'],
            workload_summary['avg_cycle_time_days'],
            s=workload_summary['weeks_observed'] * 10,
            c=workload_summary['p90_open_cases'],
            cmap='YlOrRd',
            alpha=0.8,
            edgecolors='grey',
            linewidths=0.6,
        )
        x_cut = workload_summary['avg_open_cases'].median()
        y_cut = workload_summary['avg_cycle_time_days'].median()
        ax.axvline(x_cut, linestyle='--', color='grey', linewidth=1)
        ax.axhline(y_cut, linestyle='--', color='grey', linewidth=1)
        for _, row in workload_summary.nlargest(8, 'priority_score').iterrows():
            ax.annotate(
                truncate_label(row['Department'], 24),
                (row['avg_open_cases'], row['avg_cycle_time_days']),
                xytext=(4, 4),
                textcoords='offset points',
                fontsize=8,
            )
        apply_rtl_text(
            ax,
            title='Department Workload vs Cycle Time',
            xlabel='Average Open Cases',
            ylabel='Average Cycle Time (Days)',
        )
        fig.colorbar(scatter, ax=ax, label='P90 Open Cases')
        finalize_and_save(fig, output_dir / 'department_workload_vs_cycle_time.png')


def analyze_workload(logfile_path, output_dir):
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='workload analysis')

    cases = df.groupby(['case_id', 'department']).agg(
        start=('timestamp', 'min'),
        end=('timestamp', 'max')
    ).reset_index()

    date_range = pd.date_range(cases['start'].min(), cases['end'].max(), freq='W')
    if len(date_range) == 0:
        date_range = pd.DatetimeIndex([cases['end'].max().normalize()])

    workload_data = []
    for week in date_range:
        for dept in cases['department'].dropna().unique():
            active_count = cases[
                (cases['department'] == dept)
                & (cases['start'] <= week)
                & (cases['end'] >= week)
            ].shape[0]
            workload_data.append({'Week': week, 'Department': dept, 'Open_Cases': active_count})

    wl_df = pd.DataFrame(workload_data, columns=['Week', 'Department', 'Open_Cases'])
    if wl_df.empty:
        wl_df['Moving_Avg_4W'] = pd.Series(dtype=float)
    else:
        wl_df['Moving_Avg_4W'] = wl_df.groupby('Department')['Open_Cases'].transform(
            lambda x: x.rolling(4, min_periods=1).mean()
        )

    # Calculate Correlation between Workload and Cycle Time
    cases['cycle_time'] = (cases['end'] - cases['start']).dt.total_seconds() / 86400
    cases['end_week'] = cases['end'].dt.to_period('W').dt.start_time
    weekly_perf = cases.groupby(['end_week', 'department'])['cycle_time'].mean().reset_index()
    weekly_perf.columns = ['Week', 'Department', 'Avg_Cycle_Time']

    correlation_df = wl_df.merge(weekly_perf, on=['Week', 'Department'], how='inner')

    if len(correlation_df) > 1:
        corr_score = correlation_df[['Open_Cases', 'Avg_Cycle_Time']].corr().iloc[0, 1]
    else:
        corr_score = 0

    if pd.isna(corr_score):
        corr_score = 0.0

    print(f"[Workload] Correlation between Workload and Cycle Time: {corr_score:.4f}")

    # Save correlation score
    corr_path = output_dir / 'workload_correlation.json'
    corr_path.write_text(json.dumps({'correlation_workload_cycle_time': round(float(corr_score), 4)}))

    # Save outputs
    wl_df.to_csv(output_dir / 'workload_analysis.csv', index=False)
    if correlation_df.empty:
        workload_summary = pd.DataFrame(
            columns=['Department', 'avg_open_cases', 'p90_open_cases', 'avg_cycle_time_days', 'weeks_observed', 'priority_score']
        )
    else:
        workload_summary = correlation_df.groupby('Department').agg(
            avg_open_cases=('Open_Cases', 'mean'),
            p90_open_cases=('Open_Cases', lambda x: x.quantile(0.9)),
            avg_cycle_time_days=('Avg_Cycle_Time', 'mean'),
            weeks_observed=('Week', 'nunique'),
        ).reset_index()
        workload_summary['priority_score'] = (
            workload_summary['avg_open_cases'] * workload_summary['avg_cycle_time_days']
        )
        workload_summary.sort_values('priority_score', ascending=False, inplace=True)
        workload_summary.to_csv(output_dir / 'department_workload_cycle_summary.csv', index=False)

    _save_workload_plots(wl_df, workload_summary, output_dir)
    print("Workload analysis complete.")


def parse_args():
    parser = argparse.ArgumentParser(description="Run workload-over-time analysis")
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated outputs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    output_dir = ensure_output_dir(args.output_dir)
    analyze_workload(logfile, output_dir)
