import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    from cli_utils import ensure_exists, ensure_output_dir
    from bottleneck_segmentation_analysis import analyze_bottleneck_segmentation
    from data_preprocessing import preprocess_logs
    from internal_process_analysis import analyze_internal_process
    from performance_analysis import analyze_performance
    from policy_path_analysis import analyze_policy_and_path_alignment
    from process_discovery import generate_process_models
    from responsible_change_analysis import analyze_responsible_change
    from result_insights import generate_result_insights
    from final_report_generator import generate_final_project_report
    from alignment_report import generate_alignment_report
    from workload_analysis import analyze_workload
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir
    from .bottleneck_segmentation_analysis import analyze_bottleneck_segmentation
    from .data_preprocessing import preprocess_logs
    from .internal_process_analysis import analyze_internal_process
    from .performance_analysis import analyze_performance
    from .policy_path_analysis import analyze_policy_and_path_alignment
    from .process_discovery import generate_process_models
    from .responsible_change_analysis import analyze_responsible_change
    from .result_insights import generate_result_insights
    from .final_report_generator import generate_final_project_report
    from .alignment_report import generate_alignment_report
    from .workload_analysis import analyze_workload


def parse_args():
    parser = argparse.ArgumentParser(description="Run the full process mining pipeline end-to-end")
    parser.add_argument("file1", help="Path to first Excel log file")
    parser.add_argument("file2", help="Path to second Excel log file")
    parser.add_argument("--output-dir", default="outputs", help="Directory for all generated artifacts")
    parser.add_argument("--top-variants", type=int, default=20, help="Number of variants to export")
    return parser.parse_args()


def _safe_row_count(path: Path) -> int | None:
    if not path.exists() or path.suffix.lower() != '.csv':
        return None
    try:
        return int(len(pd.read_csv(path)))
    except Exception:
        return None


def _write_pipeline_manifest(output_dir: Path, top_variants: int) -> None:
    tracked_files = [
        'cleaned_log.csv',
        'event_log.xes',
        'preprocessing_quality_report.json',
        'variants.csv',
        'case_performance.csv',
        'bottleneck_analysis.csv',
        'workload_analysis.csv',
        'responsible_change_analysis.csv',
        'internal_process_analysis.csv',
        'bottleneck_by_stage.csv',
        'bottleneck_by_stage_owner.csv',
        'bottleneck_by_performer.csv',
        'cycle_time_by_department.csv',
        'cycle_time_by_request_status.csv',
        'keyword_bottleneck_analysis.csv',
        'activity_frequency_top15.png',
        'activity_transition_heatmap_top12.png',
        'variant_frequency_top15.png',
        'case_cycle_time_distribution.png',
        'bottleneck_top10_mean_wait.png',
        'bottleneck_wait_distribution_boxplot.png',
        'workload_trend_by_department.png',
        'workload_heatmap_department_week.png',
        'responsible_change_cycle_time_comparison.png',
        'responsible_change_cycle_time_boxplot.png',
        'responsible_change_count_distribution.png',
        'internal_rework_ratio_top10.png',
        'internal_rework_duration_scatter.png',
        'bottleneck_by_stage_owner_top10.png',
        'bottleneck_by_performer_top10.png',
        'cycle_time_by_request_status.png',
        'keyword_bottleneck_waits.png',
        'executive_summary.json',
        'executive_summary.md',
        'executive_dashboard.png',
        'alignment_report.json',
        'alignment_report.md',
        'final_project_report.md',
        'legal_interval_analysis.csv',
        'junior_position_path_analysis.csv',
        'station_mapping_coverage.csv',
    ]



    manifest = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'top_variants': top_variants,
        'artifacts': [],
    }
    for name in tracked_files:
        file_path = output_dir / name
        manifest['artifacts'].append(
            {
                'file': name,
                'exists': file_path.exists(),
                'size_bytes': file_path.stat().st_size if file_path.exists() else None,
                'row_count': _safe_row_count(file_path),
            }
        )

    manifest_path = output_dir / 'pipeline_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f"Pipeline manifest written to {manifest_path}")


def main():
    args = parse_args()
    file1 = ensure_exists(args.file1, "Excel file 1")
    file2 = ensure_exists(args.file2, "Excel file 2")
    output_dir = ensure_output_dir(args.output_dir)

    print("Step 1/11: Data preprocessing")
    preprocess_logs(file1, file2, output_dir)

    cleaned_log = output_dir / "cleaned_log.csv"

    print("Step 2/11: Process discovery")
    generate_process_models(cleaned_log, output_dir, top_variants=args.top_variants)

    print("Step 3/11: Performance analysis")
    analyze_performance(cleaned_log, output_dir)

    print("Step 4/11: Workload analysis")
    analyze_workload(cleaned_log, output_dir)

    print("Step 5/11: Responsible change analysis")
    analyze_responsible_change(cleaned_log, output_dir)

    print("Step 6/11: Internal process analysis")
    analyze_internal_process(cleaned_log, output_dir)

    print("Step 7/11: Bottleneck segmentation analysis")
    analyze_bottleneck_segmentation(cleaned_log, output_dir)

    print("Step 8/11: Executive summary")
    generate_result_insights(output_dir)

    print("Step 9/11: Policy and path-specific analysis")
    analyze_policy_and_path_alignment(cleaned_log, output_dir)

    print("Step 10/11: Final structured report generation")
    generate_final_project_report(output_dir)

    print("Step 11/11: Alignment checklist report")
    generate_alignment_report(output_dir)

    _write_pipeline_manifest(output_dir, top_variants=args.top_variants)
    print(f"Pipeline completed successfully. Outputs available in: {output_dir}")


if __name__ == "__main__":
    main()
