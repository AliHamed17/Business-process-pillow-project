from __future__ import annotations

from pathlib import Path

import json
import pandas as pd


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()




def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _top_rows(df: pd.DataFrame, cols: list[str], n: int = 5) -> list[str]:
    if df.empty:
        return ['- N/A']
    lines = []
    for _, row in df.head(n).iterrows():
        parts = [f"{c}={row[c]}" for c in cols if c in df.columns]
        lines.append('- ' + ', '.join(parts))
    return lines


def generate_final_project_report(output_dir: str | Path) -> Path:
    """Generate a structured final-project markdown report aligned to the brief sections."""
    output_dir = Path(output_dir)

    quality = _read_json(output_dir / 'preprocessing_quality_report.json')
    variants = _read_csv(output_dir / 'variants.csv')
    bottleneck_stage = _read_csv(output_dir / 'bottleneck_by_stage.csv')
    dept_cycle = _read_csv(output_dir / 'cycle_time_by_department.csv')
    outcome_cycle = _read_csv(output_dir / 'cycle_time_by_request_status.csv')
    ownership = _read_csv(output_dir / 'responsible_change_analysis.csv')
    internal = _read_csv(output_dir / 'internal_process_analysis.csv')
    workload = _read_csv(output_dir / 'workload_analysis.csv')
    legal = _read_csv(output_dir / 'legal_interval_analysis.csv')
    junior = _read_csv(output_dir / 'junior_position_path_analysis.csv')
    stations = _read_csv(output_dir / 'station_mapping_coverage.csv')
    exec_md = (output_dir / 'executive_summary.md').read_text(encoding='utf-8') if (output_dir / 'executive_summary.md').exists() else ''

    lines: list[str] = []
    lines.append('# Final Project Report: Job Staffing Process at Haifa Municipality')
    lines.append('')
    lines.append('## Executive Summary (≤1 page)')
    lines.append('This section synthesizes goals, key findings, and recommendations. For compact KPI wording, see `executive_summary.md`.')
    if exec_md:
        lines.append('')
        lines.extend(exec_md.splitlines()[:20])

    lines.append('')
    lines.append('## Introduction')
    lines.append('This report analyzes the staffing/recruitment lifecycle to identify delay drivers and propose concrete operational improvements.')
    lines.append('The analysis combines event-log preprocessing, process pathing, performance/workload diagnostics, ownership/rework effects, and alignment checks.')

    lines.append('')
    lines.append('## Preprocessing')
    lines.append('Purpose: standardize log schema, parse dates, remove invalid records, and produce analysis-ready event traces.')
    lines.append('Artifacts: `cleaned_log.csv`, `event_log.xes`, `preprocessing_quality_report.json`, and preprocessing plots in outputs.')
    if quality:
        lines.append(f"Quality snapshot: rows_after_cleaning={quality.get('rows_after_cleaning')}, dropped_missing={quality.get('dropped_missing_core_fields')}, dropped_duplicates={quality.get('dropped_duplicates')}")
    lines.append('Suggested evidence charts: `activity_frequency_top15.png`, `case_cycle_time_distribution.png`.')

    lines.append('')
    lines.append('## Process Pathing (Variants)')
    lines.append('Main variants extracted from the cleaned event log:')
    lines.extend(_top_rows(variants, ['Variant', 'Frequency'], n=8))
    lines.append('Interpretation support: `variant_frequency_top15.png`, `activity_transition_heatmap_top12.png`.')

    lines.append('')
    lines.append('## Analyses (Business Questions)')
    lines.append('### 1) Where are the delays?')
    lines.append('Top bottleneck stages:')
    lines.extend(_top_rows(bottleneck_stage, ['activity', 'mean_wait_days'], n=8))
    lines.append('Top delaying departments:')
    lines.extend(_top_rows(dept_cycle, ['department', 'mean_cycle_time_days'], n=5))
    lines.append('Delays by outcomes/status:')
    lines.extend(_top_rows(outcome_cycle, ['request_status', 'mean_cycle_time_days'], n=5))

    lines.append('')
    lines.append('### 2) Variants and longest delays')
    lines.append('Use `variants.csv` with bottleneck tables to inspect which paths coincide with prolonged waits.')

    lines.append('')
    lines.append('### 3) Workload vs Speed')
    if not workload.empty and {'Department', 'Open_Cases'}.issubset(workload.columns):
        agg = workload.groupby('Department')['Open_Cases'].mean().sort_values(ascending=False).reset_index()
        lines.append('Average open cases by department:')
        lines.extend(_top_rows(agg, ['Department', 'Open_Cases'], n=5))
    else:
        lines.append('- N/A')

    lines.append('')
    lines.append('### 4) Ownership changes and delays')
    lines.extend(_top_rows(ownership, ['has_reassignment', 'mean'], n=5))

    lines.append('')
    lines.append('### 5) Internal subprocesses and delays')
    lines.extend(_top_rows(internal, ['activity', 'rework_ratio', 'avg_duration_days'], n=8))

    lines.append('')
    lines.append('### 6) Process-specific checks (legal windows, junior path, station mapping)')
    lines.append('Legal-interval candidate summary:')
    lines.extend(_top_rows(legal, ['activity', 'mean_wait_days', 'regulated_window_14_45_ratio'], n=5))
    lines.append('Junior-position path proxy:')
    lines.extend(_top_rows(junior, ['is_junior_proxy', 'mean'], n=2))
    lines.append('Station mapping coverage (municipality narrative):')
    lines.extend(_top_rows(stations, ['station', 'covered', 'matched_activity_count'], n=9))

    lines.append('')
    lines.append('## Conclusions & Recommendations')
    lines.append('Prioritize interventions on stages with both high mean wait and high rework ratio.')
    lines.append('Stabilize ownership handoffs for stages where reassignment is associated with longer cycle times.')
    lines.append('Use workload heatmaps and department cycle-time tables to balance staffing and SLA commitments.')
    lines.append('Track legal-window and committee/screening stages with dedicated KPIs each reporting cycle.')

    lines.append('')
    lines.append('## Appendices')
    lines.append('- Code: `src/`')
    lines.append('- Artifacts: `outputs/` (CSV, PNG, JSON, MD)')
    lines.append('- Alignment checklist: `alignment_report.md`')

    report_path = output_dir / 'final_project_report.md'
    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Final project report written to {report_path}')
    return report_path
