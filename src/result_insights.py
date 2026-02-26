import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

try:
    from plot_utils import finalize_and_save, set_plot_style
except ModuleNotFoundError:  # package-import fallback for tests
    from .plot_utils import finalize_and_save, set_plot_style


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _save_executive_dashboard(summary: dict, output_dir: Path) -> None:
    set_plot_style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    top_b = summary.get('top_bottlenecks', [])[:5]
    if top_b:
        labels = [x['activity'] for x in top_b]
        values = [x['mean_wait_days'] for x in top_b]
        axes[0].barh(labels, values, color='#C44E52')
        axes[0].invert_yaxis()
        axes[0].set_title('Top Bottlenecks')
        axes[0].set_xlabel('Mean Wait (Days)')
    else:
        axes[0].text(0.5, 0.5, 'No bottleneck data', ha='center', va='center')
        axes[0].set_axis_off()

    priorities = summary.get('priority_recommendations', [])[:5]
    if priorities:
        labels = [x['activity'] for x in priorities]
        values = [x['priority_score'] for x in priorities]
        axes[1].barh(labels, values, color='#4C72B0')
        axes[1].invert_yaxis()
        axes[1].set_title('Priority Recommendations')
        axes[1].set_xlabel('Priority Score')
    else:
        axes[1].text(0.5, 0.5, 'No recommendation data', ha='center', va='center')
        axes[1].set_axis_off()

    finalize_and_save(fig, output_dir / 'executive_dashboard.png')


def generate_result_insights(output_dir: str | Path) -> dict:
    """Generate an executive summary and prioritized improvement opportunities."""
    output_dir = Path(output_dir)

    case_perf = _read_csv_if_exists(output_dir / 'case_performance.csv')
    bottleneck = _read_csv_if_exists(output_dir / 'bottleneck_analysis.csv')
    variants = _read_csv_if_exists(output_dir / 'variants.csv')
    workload = _read_csv_if_exists(output_dir / 'workload_analysis.csv')
    reassign = _read_csv_if_exists(output_dir / 'responsible_change_analysis.csv')
    internal = _read_csv_if_exists(output_dir / 'internal_process_analysis.csv')

    summary: dict[str, object] = {
        'kpis': {},
        'top_bottlenecks': [],
        'top_rework_activities': [],
        'variant_snapshot': [],
        'workload_hotspots': [],
        'reassignment_impact': {},
        'priority_recommendations': [],
    }

    if not case_perf.empty and 'cycle_time_days' in case_perf.columns:
        cycle = pd.to_numeric(case_perf['cycle_time_days'], errors='coerce').dropna()
        summary['kpis'] = {
            'cases_analyzed': int(len(case_perf)),
            'avg_cycle_time_days': float(cycle.mean()) if not cycle.empty else None,
            'median_cycle_time_days': float(cycle.median()) if not cycle.empty else None,
            'p90_cycle_time_days': float(cycle.quantile(0.9)) if not cycle.empty else None,
        }

    if not bottleneck.empty and {'activity', 'mean'}.issubset(bottleneck.columns):
        top_b = bottleneck[['activity', 'mean']].dropna().sort_values('mean', ascending=False).head(5)
        summary['top_bottlenecks'] = [
            {'activity': str(r.activity), 'mean_wait_days': float(r.mean)}
            for r in top_b.itertuples(index=False)
        ]

    if not internal.empty and {'activity', 'rework_ratio'}.issubset(internal.columns):
        top_r = internal[['activity', 'rework_ratio']].dropna().sort_values('rework_ratio', ascending=False).head(5)
        summary['top_rework_activities'] = [
            {'activity': str(r.activity), 'rework_ratio': float(r.rework_ratio)}
            for r in top_r.itertuples(index=False)
        ]

    if not variants.empty and {'Variant', 'Frequency'}.issubset(variants.columns):
        top_v = variants[['Variant', 'Frequency']].head(5)
        summary['variant_snapshot'] = [
            {'variant': str(r.Variant), 'frequency': int(r.Frequency)}
            for r in top_v.itertuples(index=False)
        ]

    if not workload.empty and {'Department', 'Open_Cases'}.issubset(workload.columns):
        hotspot = workload.groupby('Department')['Open_Cases'].mean().sort_values(ascending=False).head(5)
        summary['workload_hotspots'] = [
            {'department': str(dept), 'avg_open_cases': float(value)}
            for dept, value in hotspot.items()
        ]

    if not reassign.empty and {'has_reassignment', 'mean'}.issubset(reassign.columns):
        r = reassign.copy()
        r['has_reassignment'] = r['has_reassignment'].astype(str).str.lower().map({'true': True, 'false': False})
        baseline = r.loc[r['has_reassignment'] == False, 'mean']
        changed = r.loc[r['has_reassignment'] == True, 'mean']
        if not baseline.empty and not changed.empty:
            delta = float(changed.iloc[0] - baseline.iloc[0])
            summary['reassignment_impact'] = {
                'mean_cycle_time_no_reassignment': float(baseline.iloc[0]),
                'mean_cycle_time_with_reassignment': float(changed.iloc[0]),
                'delta_days': delta,
                'relative_increase_pct': (delta / float(baseline.iloc[0]) * 100.0) if float(baseline.iloc[0]) else None,
            }

    priority_rows = []
    if not bottleneck.empty and not internal.empty and {'activity', 'mean'}.issubset(bottleneck.columns) and {'activity', 'rework_ratio'}.issubset(internal.columns):
        merged = bottleneck[['activity', 'mean']].merge(
            internal[['activity', 'rework_ratio']], on='activity', how='inner'
        ).dropna()
        if not merged.empty:
            wait = pd.to_numeric(merged['mean'], errors='coerce').fillna(0)
            rework = pd.to_numeric(merged['rework_ratio'], errors='coerce').fillna(0)
            wait_n = wait / wait.max() if wait.max() else wait
            rew_n = rework / rework.max() if rework.max() else rework
            merged['priority_score'] = 0.6 * wait_n + 0.4 * rew_n
            priority_rows = merged.sort_values('priority_score', ascending=False).head(5)

    if len(priority_rows):
        summary['priority_recommendations'] = [
            {
                'activity': str(r.activity),
                'priority_score': float(r.priority_score),
                'mean_wait_days': float(r.mean),
                'rework_ratio': float(r.rework_ratio),
            }
            for r in priority_rows.itertuples(index=False)
        ]

    json_path = output_dir / 'executive_summary.json'
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')

    md_lines = [
        '# Executive Process Mining Summary',
        '',
        '## KPIs',
        f"- Cases analyzed: {summary['kpis'].get('cases_analyzed', 'N/A')}",
        f"- Avg cycle time (days): {summary['kpis'].get('avg_cycle_time_days', 'N/A')}",
        f"- Median cycle time (days): {summary['kpis'].get('median_cycle_time_days', 'N/A')}",
        f"- P90 cycle time (days): {summary['kpis'].get('p90_cycle_time_days', 'N/A')}",
        '',
        '## Top Bottlenecks',
    ]
    if summary['top_bottlenecks']:
        md_lines.extend([
            f"- {x['activity']}: {x['mean_wait_days']:.2f} mean wait days"
            for x in summary['top_bottlenecks']
        ])
    else:
        md_lines.append('- N/A')

    md_lines.extend(['', '## Priority Recommendations'])
    if summary['priority_recommendations']:
        md_lines.extend([
            f"- {x['activity']} (score={x['priority_score']:.3f}, wait={x['mean_wait_days']:.2f}, rework={x['rework_ratio']:.2f})"
            for x in summary['priority_recommendations']
        ])
    else:
        md_lines.append('- N/A')

    md_path = output_dir / 'executive_summary.md'
    md_path.write_text('\n'.join(md_lines) + '\n', encoding='utf-8')

    _save_executive_dashboard(summary, output_dir)
    print(f"Executive summary written to {json_path} and {md_path}")
    return summary
