import json
from pathlib import Path


def generate_alignment_report(output_dir: str | Path) -> dict:
    """Create a concrete checklist showing alignment to project business questions."""
    output_dir = Path(output_dir)
    checks = {
        'delays_by_stage': (output_dir / 'bottleneck_by_stage.csv').exists(),
        'delays_by_role_owner': (output_dir / 'bottleneck_by_stage_owner.csv').exists(),
        'delays_by_specific_user': (output_dir / 'bottleneck_by_performer.csv').exists(),
        'delays_by_department': (output_dir / 'cycle_time_by_department.csv').exists(),
        'delays_by_outcome_status': (output_dir / 'cycle_time_by_request_status.csv').exists(),
        'variants_and_sequences': (output_dir / 'variants.csv').exists(),
        'longest_delay_stages': (output_dir / 'bottleneck_analysis.csv').exists(),
        'workload_vs_speed': (output_dir / 'workload_analysis.csv').exists(),
        'ownership_change_impact': (output_dir / 'responsible_change_analysis.csv').exists(),
        'internal_subprocess_impact': (output_dir / 'internal_process_analysis.csv').exists(),
        'committee_screening_hotspots': (output_dir / 'keyword_bottleneck_analysis.csv').exists(),
        'operational_proposals_artifact': (output_dir / 'executive_summary.md').exists(),
    }

    score = int(sum(checks.values()))
    total = int(len(checks))
    report = {
        'alignment_score_pct': round(score / total * 100.0, 2),
        'covered_checks': score,
        'total_checks': total,
        'checks': checks,
    }

    (output_dir / 'alignment_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    md = ['# Alignment Report', '', f"Coverage: **{score}/{total}** ({report['alignment_score_pct']}%)", '', '## Checklist']
    md.extend([f"- [{'x' if v else ' '}] {k}" for k, v in checks.items()])
    (output_dir / 'alignment_report.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f"Alignment report written to {output_dir / 'alignment_report.json'}")
    return report
