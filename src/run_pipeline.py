import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import sys

# Ensure the 'src' directory is in the Python path regardless of how the script is run
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from cli_utils import ensure_exists, ensure_output_dir
from bottleneck_segmentation_analysis import analyze_bottleneck_segmentation
from data_preprocessing import preprocess_logs
from internal_process_analysis import analyze_internal_process
from performance_analysis import analyze_performance
from policy_path_analysis import analyze_policy_and_path_alignment
from process_discovery import generate_process_models
from responsible_change_analysis import analyze_responsible_change
from result_insights import generate_result_insights
from result_debugger import debug_results
from final_report_generator import generate_final_project_report
from alignment_report import generate_alignment_report
from workload_analysis import analyze_workload
from sojourn_time_analysis import analyze_sojourn_times
from temporal_trend_analysis import analyze_temporal_trends
from statistical_tests import run_statistical_tests
from algorithm_comparison import compare_algorithms
from case_clustering_analysis import analyze_case_clusters
from interactive_sna import generate_interactive_sna


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
        'results_debug_report.json',
        'results_debug_report.md',
        # P1 outputs
        'sojourn_time_by_stage.csv',
        'sojourn_time_by_department.csv',
        'conformance_results.csv',
        'conformance_violations.csv',
        'conformance_summary.json',
        'checkpoint_coverage.csv',
        'responsible_change_controlled.csv',
        # P2 outputs
        'monthly_trend_stats.csv',
        'monthly_cycle_time_trend.png',
        'monthly_throughput.png',
        'dotted_chart.png',
        'statistical_tests.csv',
        'statistical_tests.json',
        'algorithm_comparison.csv',
        'algorithm_comparison.json',
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

    print("Step 1/19: Data preprocessing")
    preprocess_logs(file1, file2, output_dir)

    cleaned_log = output_dir / "cleaned_log.csv"
    xes_log = output_dir / "event_log.xes"

    print("Step 2/19: Process discovery")
    generate_process_models(cleaned_log, output_dir, top_variants=args.top_variants)

    print("Step 3/19: Performance analysis")
    analyze_performance(cleaned_log, output_dir)

    print("Step 4/19: Workload analysis")
    analyze_workload(cleaned_log, output_dir)

    print("Step 5/19: Responsible change analysis")
    analyze_responsible_change(cleaned_log, output_dir)

    print("Step 6/19: Internal process analysis")
    analyze_internal_process(cleaned_log, output_dir)

    print("Step 7/19: Bottleneck segmentation analysis")
    analyze_bottleneck_segmentation(cleaned_log, output_dir)

    print("Step 8/19: Sojourn time analysis")
    analyze_sojourn_times(cleaned_log, output_dir)

    print("Step 9/19: Temporal trend analysis")
    analyze_temporal_trends(cleaned_log, output_dir)

    print("Step 10/19: Statistical significance tests")
    run_statistical_tests(cleaned_log, output_dir)

    print("Step 11/19: Algorithm comparison")
    if xes_log.exists():
        compare_algorithms(xes_log, output_dir)
    else:
        print("  Skipping — event_log.xes not found")

    print("Step 12/19: Executive summary")
    generate_result_insights(output_dir)

    print("Step 13/19: Policy and path-specific analysis")
    analyze_policy_and_path_alignment(cleaned_log, output_dir)

    print("Step 14/19: Final structured report generation")
    generate_final_project_report(output_dir)

    print("Step 15/19: Alignment checklist report")
    generate_alignment_report(output_dir)

    print("Step 16/19: Case clustering (P3 Enhancement)")
    analyze_case_clusters(cleaned_log, output_dir)

    print("Step 17/19: Interactive SNA with Centrality (P3 Enhancement)")
    generate_interactive_sna(output_dir / "handover_list.csv", output_dir / "interactive_sna.html")

    print("Step 18/19: Results debug sanity checks")
    debug_results(output_dir)

    _write_pipeline_manifest(output_dir, top_variants=args.top_variants)
    print(f"Pipeline completed successfully. Outputs available in: {output_dir}")


if __name__ == "__main__":
    main()
