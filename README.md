# Haifa Municipality Recruitment Process Mining

This repository contains the full source code and analysis for the business process mining project of the Haifa Municipality recruitment process ("איוש משרה").

## Structure
- `data/` - Contains the raw Excel log files (not tracked in Git due to size)
- `docs/` - Requirements and final report (Word formatting)
- `notebooks/` - Contains Jupyter notebook representation
- `src/` - Modular Python scripts for specific analytical components
- `outputs/` - Generated event logs, XES files, DFGs, CSV metrics and models

## Usage
1. Install dependencies: `pip install -r requirements.txt`
2. Run the full pipeline:
   - `python src/run_pipeline.py <excel_part_1.xlsx> <excel_part_2.xlsx> --output-dir outputs`

### Run scripts individually
- `python src/data_preprocessing.py <excel_part_1.xlsx> <excel_part_2.xlsx> --output-dir outputs`
- `python src/process_discovery.py outputs/cleaned_log.csv --output-dir outputs --top-variants 20`
- `python src/performance_analysis.py outputs/cleaned_log.csv --output-dir outputs`
- `python src/workload_analysis.py outputs/cleaned_log.csv --output-dir outputs`
- `python src/responsible_change_analysis.py outputs/cleaned_log.csv --output-dir outputs`
- `python src/internal_process_analysis.py outputs/cleaned_log.csv --output-dir outputs`

## Features
- End-to-end Process Mining using `pandas` and `pm4py`.
- Generates DFG frequency and performance graphs.
- Computes stage sojourn times and bottleneck ratios.
- Variant frequencies.
- Workload vs Delay correlations.
- Tracks assignment transitions.

### New robustness features
- Automatic required-column validation with clear error messages.
- Data-quality report after preprocessing: `outputs/preprocessing_quality_report.json`.
- End-to-end output manifest: `outputs/pipeline_manifest.json`.


## Development checks
- Run static import/bytecode check: `python -m compileall src`
- Run unit tests: `python -m unittest discover -s tests -p "test_*.py"`


### Visualization outputs
- All charts now use a consistent style, improved label readability, and value annotations for easier human interpretation.
- `outputs/activity_frequency_top15.png`: most frequent activities in the event log.
- `outputs/activity_transition_heatmap_top12.png`: transition intensity between top activities.
- `outputs/variant_frequency_top15.png`: top process variant frequencies.
- `outputs/case_cycle_time_distribution.png`: case cycle time distribution.
- `outputs/bottleneck_top10_mean_wait.png`: top bottleneck activities by mean wait time.
- `outputs/bottleneck_wait_distribution_boxplot.png`: wait-time spread for top bottleneck activities.
- `outputs/workload_trend_by_department.png`: department open-case trend with moving average.
- `outputs/workload_heatmap_department_week.png`: workload heatmap by department and week.
- `outputs/responsible_change_cycle_time_comparison.png`, `outputs/responsible_change_cycle_time_boxplot.png`, and `outputs/responsible_change_count_distribution.png`: reassignment impact and frequency.
- `outputs/internal_rework_ratio_top10.png` and `outputs/internal_rework_duration_scatter.png`: rework hotspots and duration relationship.
- `outputs/executive_summary.json`, `outputs/executive_summary.md`, and `outputs/executive_dashboard.png`: KPI summary, prioritized recommendations, and executive visual dashboard.
- `outputs/alignment_report.json` and `outputs/alignment_report.md`: explicit business-question coverage checklist and overall alignment score.

### How to review and analyze the plots
1. Start with `activity_frequency_top15.png` and `variant_frequency_top15.png` to understand dominant flow patterns.
2. Use `case_cycle_time_distribution.png` to spot long-tail cases and overall spread.
3. Check `bottleneck_top10_mean_wait.png` to identify stages likely causing delays.
4. Compare departments in `workload_trend_by_department.png` to detect load spikes and imbalance.
5. Validate whether reassignments are associated with slower outcomes using responsible-change plots.
6. Use `internal_rework_ratio_top10.png` to prioritize stages for SOP refinement and automation.
7. Inspect `executive_dashboard.png` for a high-level bottleneck and priority overview.
8. Read `executive_summary.md` for a concise KPI snapshot and ranked improvement list.


## Alignment to final project goals
- Run the full pipeline and then review `outputs/alignment_report.md`.
- The report checks coverage for all requested business questions (delays by stage/role/user/department/outcome, variants, workload-speed, ownership changes, internal subprocesses, screening/committee hotspots, and operational proposals).
