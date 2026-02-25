import argparse
import json
from pathlib import Path

import pandas as pd

from cli_utils import ensure_exists, ensure_output_dir
from data_preprocessing import preprocess_logs
from internal_process_analysis import analyze_internal_process
from performance_analysis import analyze_performance
from process_discovery import generate_process_models
from responsible_change_analysis import analyze_responsible_change
from workload_analysis import analyze_workload


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


def _write_pipeline_manifest(output_dir: Path) -> None:
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
    ]

    manifest = []
    for name in tracked_files:
        file_path = output_dir / name
        manifest.append(
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

    print("Step 1/6: Data preprocessing")
    preprocess_logs(file1, file2, output_dir)

    cleaned_log = output_dir / "cleaned_log.csv"

    print("Step 2/6: Process discovery")
    generate_process_models(cleaned_log, output_dir, top_variants=args.top_variants)

    print("Step 3/6: Performance analysis")
    analyze_performance(cleaned_log, output_dir)

    print("Step 4/6: Workload analysis")
    analyze_workload(cleaned_log, output_dir)

    print("Step 5/6: Responsible change analysis")
    analyze_responsible_change(cleaned_log, output_dir)

    print("Step 6/6: Internal process analysis")
    analyze_internal_process(cleaned_log, output_dir)

    _write_pipeline_manifest(output_dir)
    print(f"Pipeline completed successfully. Outputs available in: {output_dir}")


if __name__ == "__main__":
    main()
