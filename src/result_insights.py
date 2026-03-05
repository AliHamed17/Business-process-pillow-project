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


def _as_float(value) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _fmt(value, digits: int = 2) -> str:
    numeric = _as_float(value)
    return f"{numeric:.{digits}f}" if numeric is not None else 'N/A'


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


def _build_key_messages(summary: dict) -> list[str]:
    messages = []
    kpis = summary.get('kpis', {})
    if kpis.get('p90_cycle_time_days') is not None:
        messages.append(
            f"Long-tail performance remains material (P90 cycle time: {kpis['p90_cycle_time_days']:.2f} days)."
        )

    top_bottlenecks = summary.get('top_bottlenecks', [])
    if top_bottlenecks:
        messages.append(
            f"Highest waiting stage is '{top_bottlenecks[0]['activity']}' with {top_bottlenecks[0]['mean_wait_days']:.2f} mean days."
        )

    reassignment = summary.get('reassignment_impact', {})
    if reassignment.get('relative_increase_pct') is not None:
        pct = reassignment['relative_increase_pct']
        direction = 'increase' if pct >= 0 else 'decrease'
        messages.append(f"Reassignment is associated with a {abs(pct):.1f}% {direction} in cycle time.")

    quality = summary.get('result_quality', {})
    missing = quality.get('missing_sources', [])
    if missing:
        messages.append(f"Some insights are partial because source artifacts are missing: {', '.join(missing)}.")

    return messages


def generate_result_insights(output_dir: str | Path) -> dict:
    """Generate an executive summary and prioritized improvement opportunities."""
    output_dir = Path(output_dir)

    source_paths = {
        'case_performance': output_dir / 'case_performance.csv',
        'bottleneck_analysis': output_dir / 'bottleneck_analysis.csv',
        'variants': output_dir / 'variants.csv',
        'workload_analysis': output_dir / 'workload_analysis.csv',
        'responsible_change_analysis': output_dir / 'responsible_change_analysis.csv',
        'internal_process_analysis': output_dir / 'internal_process_analysis.csv',
    }
    frames = {name: _read_csv_if_exists(path) for name, path in source_paths.items()}

    case_perf = frames['case_performance']
    bottleneck = frames['bottleneck_analysis']
    variants = frames['variants']
    workload = frames['workload_analysis']
    reassign = frames['responsible_change_analysis']
    internal = frames['internal_process_analysis']

    present_sources = [name for name, df in frames.items() if not df.empty]
    missing_sources = [name for name, df in frames.items() if df.empty]

    summary: dict[str, object] = {
        'kpis': {},
        'top_bottlenecks': [],
        'top_rework_activities': [],
        'variant_snapshot': [],
        'workload_hotspots': [],
        'reassignment_impact': {},
        'priority_recommendations': [],
        'risk_signals': {},
        'result_quality': {
            'present_sources': present_sources,
            'missing_sources': missing_sources,
            'completeness_ratio': len(present_sources) / len(frames) if frames else 0.0,
        },
        'key_messages': [],
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

    cycle_p90 = summary['kpis'].get('p90_cycle_time_days') if summary['kpis'] else None
    top_wait = summary['top_bottlenecks'][0]['mean_wait_days'] if summary['top_bottlenecks'] else None
    top_dept = summary['workload_hotspots'][0]['avg_open_cases'] if summary['workload_hotspots'] else None
    summary['risk_signals'] = {
        'long_tail_cycle_time': _as_float(cycle_p90) is not None and float(cycle_p90) > 30,
        'high_stage_wait': _as_float(top_wait) is not None and float(top_wait) > 10,
        'department_load_concentration': _as_float(top_dept) is not None and float(top_dept) > 20,
    }

    summary['key_messages'] = _build_key_messages(summary)

    json_path = output_dir / 'executive_summary.json'
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')

    md_lines = [
        '# Executive Process Mining Summary',
        '',
        '## KPIs',
        f"- Cases analyzed: {summary['kpis'].get('cases_analyzed', 'N/A')}",
        f"- Avg cycle time (days): {_fmt(summary['kpis'].get('avg_cycle_time_days'))}",
        f"- Median cycle time (days): {_fmt(summary['kpis'].get('median_cycle_time_days'))}",
        f"- P90 cycle time (days): {_fmt(summary['kpis'].get('p90_cycle_time_days'))}",
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

    md_lines.extend(['', '## Top Rework Activities'])
    if summary['top_rework_activities']:
        md_lines.extend([
            f"- {x['activity']}: rework ratio {x['rework_ratio']:.2f}"
            for x in summary['top_rework_activities']
        ])
    else:
        md_lines.append('- N/A')

    md_lines.extend(['', '## Workload Hotspots'])
    if summary['workload_hotspots']:
        md_lines.extend([
            f"- {x['department']}: avg open cases {x['avg_open_cases']:.2f}"
            for x in summary['workload_hotspots']
        ])
    else:
        md_lines.append('- N/A')

    md_lines.extend(['', '## Reassignment Impact'])
    reassignment = summary['reassignment_impact']
    if reassignment:
        md_lines.extend([
            f"- Mean cycle time (no reassignment): {_fmt(reassignment.get('mean_cycle_time_no_reassignment'))}",
            f"- Mean cycle time (with reassignment): {_fmt(reassignment.get('mean_cycle_time_with_reassignment'))}",
            f"- Delta days: {_fmt(reassignment.get('delta_days'))}",
            f"- Relative increase (%): {_fmt(reassignment.get('relative_increase_pct'))}",
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

    md_lines.extend(['', '## Risk Signals'])
    for key, value in summary['risk_signals'].items():
        md_lines.append(f"- {key}: {'YES' if value else 'NO'}")

    md_lines.extend([
        '',
        '## Result Quality',
        f"- Source completeness: {summary['result_quality']['completeness_ratio']:.2f}",
        f"- Present sources: {', '.join(summary['result_quality']['present_sources']) if summary['result_quality']['present_sources'] else 'N/A'}",
        f"- Missing sources: {', '.join(summary['result_quality']['missing_sources']) if summary['result_quality']['missing_sources'] else 'None'}",
        '',
        '## Key Messages',
    ])
    if summary['key_messages']:
        md_lines.extend([f'- {msg}' for msg in summary['key_messages']])
    else:
        md_lines.append('- N/A')

    md_path = output_dir / 'executive_summary.md'
    md_path.write_text('\n'.join(md_lines) + '\n', encoding='utf-8')

    _save_executive_dashboard(summary, output_dir)
    print(f"Executive summary written to {json_path} and {md_path}")
    return summary
