import json
from pathlib import Path

import pandas as pd


def _safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def debug_results(output_dir: str | Path) -> dict:
    """Run sanity checks on generated outputs and emit debug report."""
    output_dir = Path(output_dir)

    checks = []

    case_perf = _safe_read_csv(output_dir / 'case_performance.csv')
    if case_perf.empty:
        checks.append({'check': 'case_performance_non_empty', 'status': 'fail', 'detail': 'case_performance.csv is missing/empty'})
    else:
        cycle = pd.to_numeric(case_perf.get('cycle_time_days'), errors='coerce')
        checks.append({'check': 'cycle_time_non_negative', 'status': 'pass' if (cycle.dropna() >= 0).all() else 'fail'})

    variants = _safe_read_csv(output_dir / 'variants.csv')
    if variants.empty:
        checks.append({'check': 'variants_non_empty', 'status': 'fail', 'detail': 'variants.csv is missing/empty'})
    else:
        freq = pd.to_numeric(variants.get('Frequency'), errors='coerce')
        checks.append({'check': 'variant_frequency_positive', 'status': 'pass' if (freq.dropna() > 0).all() else 'warn'})

    workload = _safe_read_csv(output_dir / 'workload_analysis.csv')
    if workload.empty:
        checks.append({'check': 'workload_non_empty', 'status': 'fail'})
    else:
        open_cases = pd.to_numeric(workload.get('Open_Cases'), errors='coerce')
        checks.append({'check': 'workload_non_negative', 'status': 'pass' if (open_cases.dropna() >= 0).all() else 'fail'})

    alignment = output_dir / 'alignment_report.json'
    if alignment.exists():
        try:
            a = json.loads(alignment.read_text(encoding='utf-8'))
            score = float(a.get('alignment_score_pct', 0))
            checks.append({'check': 'alignment_score_exists', 'status': 'pass', 'value': score})
        except Exception:
            checks.append({'check': 'alignment_score_exists', 'status': 'fail'})
    else:
        checks.append({'check': 'alignment_report_exists', 'status': 'fail'})

    has_fail = any(c['status'] == 'fail' for c in checks)
    has_warn = any(c['status'] == 'warn' for c in checks)
    overall = 'fail' if has_fail else ('warn' if has_warn else 'pass')

    report = {'overall_status': overall, 'checks': checks}
    (output_dir / 'results_debug_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    md_lines = ['# Results Debug Report', '', f"Overall: **{overall.upper()}**", '', '## Checks']
    for c in checks:
        extra = ''
        if 'value' in c:
            extra = f" (value={c['value']})"
        if 'detail' in c:
            extra = f" - {c['detail']}"
        md_lines.append(f"- [{c['status']}] {c['check']}{extra}")
    (output_dir / 'results_debug_report.md').write_text('\n'.join(md_lines) + '\n', encoding='utf-8')

    print(f"Results debug report written to {output_dir / 'results_debug_report.json'}")
    return report
