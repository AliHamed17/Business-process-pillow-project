# Haifa Municipality Recruitment Process Mining - Final Submission Guide

Welcome to the final submission package for the Haifa Municipality Recruitment Process Mining project. This document serves as a quick-start guide to easily run the code and reproduce the results described in our academic report.

## Project Overview
This project applies process mining to the "איוש משרה" (Job Staffing) workflow to identify bottlenecks, map process variants, and provide data-driven operational recommendations. The pipeline cleans raw event logs, applies process discovery (Heuristics Miner, Inductive Miner), performs statistical bottleneck analysis, and generates a suite of academic-grade visualizations.

## Folder Structure
- `src/` - The core Python modular scripts (preprocessing, discovery, performance analysis, extended visualizations, etc.).
- `docs/` - Contains the Academic Reports, methodology, and requirement rubrics.
- `requirements.txt` - Python package dependencies.
- `README.md` - Technical overview of the repository.

## How to Trigger the Code

To execute the entire project from end-to-end, follow these explicit setup and execution steps:

### 1. Environment Setup

It is highly recommended to use a virtual environment (Python 3.9+).

```bash
# Install all required dependencies
pip install -r requirements.txt
```

*(Note for Windows users: if you encounter a `pm4py` installation error regarding file path lengths, please ensure Windows Long Paths are enabled in your registry).*

### 2. Execution

The entire analytical pipeline is orchestrated by a single command. Point it to the raw Excel logs representing Part 1 and Part 2 of the dataset.

```bash
# Standard execution (replace with your actual data paths)
python src/run_pipeline.py "path_to_excel_1.xlsx" "path_to_excel_2.xlsx" --output-dir outputs
```

### 3. What Happens When You Run It?
The pipeline executes exactly in the order defined in our academic report methodology:

1. **`data_preprocessing.py`**: Merges the excels, renames Hebrew columns to English schema, deduplicates consecutive events to remove false tracking noise, and drops invalid rows. Generates quality logs like `preprocessing_waterfall.png`.
2. **Process Discovery**: Discovers the process schema utilizing Heuristic Miner, identifying the 'Main Road' and dominant approval hierarchy.
3. **Performance & Bottleneck Analysis (`performance_analysis.py`, `bottleneck_segmentation_analysis.py`)**: Computes cycle times and stage-level wait times. Identifies that the CEO Decision and Budget Recommendation stages are the dominant P95 bottlenecks (max 134 days).
4. **Workload Analysis**: Proves that aggregate department workload volume does *not* correlate with delay severity.
5. **Responsible Change Analysis**: Shows reassignment impact on case resolution speeds.
6. **Machine Learning (`predictive_model.py`)**: Trains a Random Forest to predict cancellation probabilities, identifying target features like early abandonment before the Budget phase.
7. **Visualizations**: Outputs 25+ academic-ready charts (Extended, Bonus, and Advanced visual suites) with full Hebrew RTL font correction into the `outputs/plots/` directory.
8. **Report Generation**: Automatically aggregates the statistical artifacts into a markdown report.

## Interpreting the Output
Upon completion, navigate to the `outputs/` folder created by the script:
- Review `outputs/pipeline_manifest.json` for a directory of all created artifacts.
- Check `outputs/plots/` for visual evidence of bottlenecks, variant frequencies, Pareto distributions, and workload heatmaps.
- Read `outputs/final_project_report.md` for a synthesized summary matching the structure of the final submitted `docs/academic_report.md`.
