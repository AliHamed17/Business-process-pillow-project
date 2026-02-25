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
