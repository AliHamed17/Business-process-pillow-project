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
2. Run data preprocessing: `python src/data_preprocessing.py`
3. Run discovery: `python src/process_discovery.py`
4. Run analyses:
   - `python src/performance_analysis.py`
   - `python src/workload_analysis.py`
   - `python src/responsible_change_analysis.py`
   - `python src/internal_process_analysis.py`

## Features
- End-to-end Process Mining using `pandas` and `pm4py`.
- Generates DFG frequency and performance graphs.
- Computes stage sojourn times and bottleneck ratios.
- Variant frequencies.
- Workload vs Delay correlations.
- Tracks assignment transitions.
