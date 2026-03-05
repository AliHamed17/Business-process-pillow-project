"""
Statistical Significance Tests
================================
Academic Justification:
  Reporting differences in means without statistical testing is a common
  pitfall in process mining studies.  Mann-Whitney U tests (non-parametric)
  are appropriate because cycle-time distributions are typically skewed
  and non-normal (Dumas et al., 2018).

  This module adds rigorous hypothesis testing to key comparisons:
  1. Cycle time: reassigned vs non-reassigned cases
  2. Cycle time: by request status (Approved vs Cancelled)
  3. Cycle time: top-5 departments pairwise comparison

Outputs:
  - statistical_tests.csv   : test results with effect sizes
  - statistical_tests.json  : machine-readable version
"""

import argparse
import json
from pathlib import Path

import pandas as pd
import numpy as np

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
except ModuleNotFoundError:
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log


REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']


def _mann_whitney(group_a, group_b, label_a, label_b, test_name):
    """Run Mann-Whitney U test and return result dict."""
    from scipy.stats import mannwhitneyu
    a = group_a.dropna()
    b = group_b.dropna()
    if len(a) < 2 or len(b) < 2:
        return {
            'test': test_name,
            'group_a': label_a, 'group_b': label_b,
            'n_a': len(a), 'n_b': len(b),
            'median_a': float(a.median()) if len(a) else None,
            'median_b': float(b.median()) if len(b) else None,
            'U_statistic': None, 'p_value': None,
            'significant_005': None,
            'effect_size_r': None,
        }
    stat, pval = mannwhitneyu(a, b, alternative='two-sided')
    # Effect size r = Z / sqrt(N)
    n = len(a) + len(b)
    z = abs((stat - (len(a) * len(b) / 2)) / np.sqrt(len(a) * len(b) * (n + 1) / 12))
    r = z / np.sqrt(n)
    return {
        'test': test_name,
        'group_a': label_a, 'group_b': label_b,
        'n_a': len(a), 'n_b': len(b),
        'median_a': round(float(a.median()), 2),
        'median_b': round(float(b.median()), 2),
        'U_statistic': round(float(stat), 2),
        'p_value': round(float(pval), 6),
        'significant_005': bool(pval < 0.05),
        'effect_size_r': round(float(r), 4),
    }


def run_statistical_tests(logfile_path, output_dir):
    """Run Mann-Whitney U tests on key process comparisons."""
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='statistical tests')
    df.sort_values(['case_id', 'timestamp'], inplace=True)

    # Build case-level features
    case_perf = df.groupby('case_id').agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max'),
    ).reset_index()
    case_perf['cycle_time_days'] = (
        case_perf['end_time'] - case_perf['start_time']
    ).dt.total_seconds() / (24 * 3600)

    # Merge optional columns
    if 'stage_responsible' in df.columns:
        reassignment = df.groupby('case_id').apply(
            lambda g: (g['stage_responsible'] != g['stage_responsible'].shift(1)).sum() - 1
        ).reset_index(name='reassignment_count')
        case_perf = case_perf.merge(reassignment, on='case_id', how='left')
        case_perf['has_reassignment'] = case_perf['reassignment_count'] > 0

    if 'request_status' in df.columns:
        status = df.groupby('case_id')['request_status'].last().reset_index()
        case_perf = case_perf.merge(status, on='case_id', how='left')

    if 'department' in df.columns:
        dept = df.groupby('case_id')['department'].last().reset_index()
        case_perf = case_perf.merge(dept, on='case_id', how='left')

    results = []

    # ── Test 1: Reassignment vs No Reassignment ──────────────────────
    if 'has_reassignment' in case_perf.columns:
        res = _mann_whitney(
            case_perf.loc[case_perf['has_reassignment'], 'cycle_time_days'],
            case_perf.loc[~case_perf['has_reassignment'], 'cycle_time_days'],
            'Has Reassignment', 'No Reassignment',
            'Cycle Time: Reassigned vs Non-Reassigned'
        )
        results.append(res)

    # ── Test 2: Approved vs Cancelled ─────────────────────────────────
    if 'request_status' in case_perf.columns:
        approved = case_perf.loc[
            case_perf['request_status'].astype(str).str.contains('אושר', na=False),
            'cycle_time_days'
        ]
        cancelled = case_perf.loc[
            case_perf['request_status'].astype(str).str.contains('בוטל', na=False),
            'cycle_time_days'
        ]
        if len(approved) >= 2 and len(cancelled) >= 2:
            res = _mann_whitney(
                approved, cancelled,
                'Approved', 'Cancelled',
                'Cycle Time: Approved vs Cancelled'
            )
            results.append(res)

    # ── Test 3: Top 5 departments pairwise ────────────────────────────
    if 'department' in case_perf.columns:
        top_depts = case_perf['department'].value_counts().head(5).index.tolist()
        for i in range(len(top_depts)):
            for j in range(i + 1, len(top_depts)):
                d1, d2 = top_depts[i], top_depts[j]
                g1 = case_perf.loc[case_perf['department'] == d1, 'cycle_time_days']
                g2 = case_perf.loc[case_perf['department'] == d2, 'cycle_time_days']
                res = _mann_whitney(
                    g1, g2, str(d1), str(d2),
                    f'Cycle Time: {str(d1)[:30]} vs {str(d2)[:30]}'
                )
                results.append(res)

    # ── Save results ──────────────────────────────────────────────────
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_dir / 'statistical_tests.csv', index=False,
                      encoding='utf-8-sig')
    (output_dir / 'statistical_tests.json').write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    sig_count = sum(1 for r in results if r.get('significant_005'))
    print(f"[Statistical Tests] {len(results)} tests performed, "
          f"{sig_count} significant at alpha=0.05")
    print("Statistical significance tests complete.")


def parse_args():
    parser = argparse.ArgumentParser(description="Run Mann-Whitney U significance tests")
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs", help="Output directory")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    output_dir = ensure_output_dir(args.output_dir)
    run_statistical_tests(logfile, output_dir)
