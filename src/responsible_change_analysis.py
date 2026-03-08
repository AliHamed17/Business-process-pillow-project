import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import annotate_bars, apply_rtl_text, finalize_and_save, set_plot_style
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import annotate_bars, apply_rtl_text, finalize_and_save, set_plot_style


REQUIRED_COLUMNS = ['case_id', 'timestamp', 'stage_responsible', 'changed_field', 'activity']


def _save_responsible_change_plots(case_changes, comparison, controlled, output_dir: Path) -> None:
    set_plot_style()
    if not comparison.empty:
        fig, ax = plt.subplots(figsize=(6.5, 4.5))
        labels = comparison['has_reassignment'].map({False: 'No Reassignment', True: 'Has Reassignment'})
        ax.bar(labels, comparison['mean'], color=['#4C72B0', '#DD8452'])
        apply_rtl_text(ax, title='Average Cycle Time by Reassignment', ylabel='Average Cycle Time (Days)')
        annotate_bars(ax, horizontal=False)
        finalize_and_save(fig, output_dir / 'responsible_change_cycle_time_comparison.png')

    if not case_changes.empty:
        cap = case_changes['cycle_time_days'].quantile(0.95)
        fig, ax = plt.subplots(figsize=(6.5, 4.5))
        box_data = [
            case_changes.loc[~case_changes['has_reassignment'], 'cycle_time_days'].dropna().clip(upper=cap),
            case_changes.loc[case_changes['has_reassignment'], 'cycle_time_days'].dropna().clip(upper=cap),
        ]
        if any(len(x) > 0 for x in box_data):
            ax.boxplot(box_data, labels=['No Reassignment', 'Has Reassignment'])
            apply_rtl_text(ax, title='Cycle Time Distribution by Reassignment (Capped at P95)', ylabel='Cycle Time (Days)')
            finalize_and_save(fig, output_dir / 'responsible_change_cycle_time_boxplot.png')
        else:
            plt.close(fig)

        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        case_changes['reassignment_count'].plot(kind='hist', bins=20, ax=ax, color='#55A868')
        apply_rtl_text(ax, title='Distribution of Reassignment Count per Case', xlabel='Reassignment Count', ylabel='Case Count')
        finalize_and_save(fig, output_dir / 'responsible_change_count_distribution.png')

    if not controlled.empty:
        plot_df = controlled.copy()
        plot_df['bucket_label'] = plot_df['complexity_bucket'].astype(int).add(1).astype(str).radd('Q')
        pivot = plot_df.pivot(index='bucket_label', columns='has_reassignment', values='median').fillna(0)
        if not pivot.empty:
            fig, ax = plt.subplots(figsize=(8.5, 5))
            order = list(pivot.index)
            x = range(len(order))
            with_reassign = [pivot.loc[label, True] if True in pivot.columns else 0 for label in order]
            without_reassign = [pivot.loc[label, False] if False in pivot.columns else 0 for label in order]
            ax.bar([i - 0.18 for i in x], without_reassign, width=0.36, label='No Reassignment', color='#4C72B0')
            ax.bar([i + 0.18 for i in x], with_reassign, width=0.36, label='Has Reassignment', color='#DD8452')
            ax.set_xticks(list(x))
            ax.set_xticklabels(order)
            apply_rtl_text(
                ax,
                title='Median Cycle Time by Complexity Quartile',
                xlabel='Event-Count Quartile',
                ylabel='Median Cycle Time (Days)',
            )
            ax.legend(loc='upper left')
            finalize_and_save(fig, output_dir / 'responsible_change_lift_by_complexity.png')

    if not case_changes.empty:
        fig, ax = plt.subplots(figsize=(8.5, 5))
        # Add slight jitter to the count to separate dots
        import numpy as np
        jitter = np.random.normal(0, 0.1, size=len(case_changes))
        ax.scatter(case_changes['reassignment_count'] + jitter, case_changes['cycle_time_days'], alpha=0.3, color='#4C72B0')
        apply_rtl_text(ax, title='Correlation: Reassignment Count vs Total Cycle Time', xlabel='Number of Reassignments', ylabel='Case Cycle Time (Days)')
        
        from scipy import stats
        slope, intercept, _, _, _ = stats.linregress(case_changes['reassignment_count'], case_changes['cycle_time_days'].fillna(0))
        x_vals = np.array(ax.get_xlim())
        y_vals = intercept + slope * x_vals
        ax.plot(x_vals, y_vals, '--', color='#C44E52', label='Linear Trend')
        ax.legend()
        
        finalize_and_save(fig, output_dir / 'reassignment_impact_scatter.png')


def analyze_responsible_change(logfile_path, output_dir):
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='responsible change analysis')
    df.sort_values(['case_id', 'timestamp'], inplace=True)

    df['prev_responsible'] = df.groupby('case_id')['stage_responsible'].shift(1)
    df['responsible_changed'] = (
        (df['stage_responsible'] != df['prev_responsible'])
        & (df['prev_responsible'].notna())
    )

    df['responsible_change_flag'] = (
        df['changed_field'].astype(str).str.contains('אחראי', na=False)
        | df['responsible_changed']
    )

    case_changes = df.groupby('case_id').agg(
        reassignment_count=('responsible_change_flag', 'sum'),
        event_count=('activity', 'size'),
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    ).reset_index()

    case_changes['cycle_time_days'] = (
        case_changes['end_time'] - case_changes['start_time']
    ).dt.total_seconds() / (24 * 3600)

    case_changes['has_reassignment'] = case_changes['reassignment_count'] > 0

    # ── Correlation analysis ──────────────────────────────────────────
    # Compute Spearman rank correlation (robust to outliers) between
    # reassignment count and cycle time.
    try:
        from scipy.stats import spearmanr
        corr, pvalue = spearmanr(
            case_changes['reassignment_count'],
            case_changes['cycle_time_days']
        )
        print(f"[Responsible Change] Spearman corr(reassignments, cycle_time): "
              f"{corr:.4f} (p={pvalue:.4e})")
    except ImportError:
        corr, pvalue = None, None

    # ── Controlled comparison ─────────────────────────────────────────
    # Bucket cases by event_count to control for case complexity.
    # Within each bucket, compare cycle times with vs without reassignment.
    case_changes['complexity_bucket'] = pd.qcut(
        case_changes['event_count'], q=4, labels=False,
        duplicates='drop'
    )
    controlled = case_changes.groupby(
        ['complexity_bucket', 'has_reassignment']
    )['cycle_time_days'].agg(['count', 'mean', 'median']).reset_index()
    controlled.to_csv(
        output_dir / 'responsible_change_controlled.csv', index=False
    )

    # ── Simple comparison (original) ──────────────────────────────────
    comparison = case_changes.groupby('has_reassignment')['cycle_time_days'].agg(
        ['count', 'mean', 'median', 'std']
    ).reset_index()

    comparison.to_csv(output_dir / 'responsible_change_analysis.csv', index=False)
    _save_responsible_change_plots(case_changes, comparison, controlled, output_dir)
    print("Responsible change analysis complete.")


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze the impact of responsible-person changes")
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated outputs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    output_dir = ensure_output_dir(args.output_dir)
    analyze_responsible_change(logfile, output_dir)
