# Antigravity Review Prompt (Full QA Checklist)

Use the prompt below when asking an external reviewer ("Antigravity") to evaluate this repository.

## Copy/paste prompt

You are reviewing a Python process-mining project end to end. Validate functionality, data quality, reproducibility, and output usefulness.

Repository goal:
- Ingest two Excel files representing event logs.
- Produce a cleaned event log + XES.
- Run process discovery and analysis modules.
- Generate visual outputs, JSON/CSV artifacts, and narrative reports.

What to check:

1) Environment and installation
- Verify dependency installation works from `requirements.txt`.
- Confirm Python version compatibility.

2) CLI ergonomics and input validation
- Run each script with `--help` and verify required arguments are clear.
- Validate behavior for missing files and bad paths.
- Validate behavior when required columns are missing.

3) End-to-end pipeline execution
- Run:
  - `python src/run_pipeline.py <excel_part_1.xlsx> <excel_part_2.xlsx> --output-dir <tmp_output_dir>`
- Confirm pipeline reaches completion and writes the manifest.
- Confirm each module runs in expected sequence (preprocess, discovery, analyses, summary, alignment, debug).

4) Preprocessing quality
- Verify duplicate and missing-row handling is applied and reported.
- Check output files:
  - `cleaned_log.csv`
  - `event_log.xes`
  - `preprocessing_quality_report.json`
- Validate date parsing, event ordering, and case/activity/timestamp integrity.

5) Discovery and analytics outputs
- Confirm major outputs are generated and non-empty when data supports them:
  - variants, performance metrics, workload metrics, reassignment metrics,
    internal/rework metrics, bottleneck segmentation, and policy/path artifacts.
- Spot-check that aggregate numbers are plausible and internally consistent.

6) Visualization quality
- Check charts exist and are readable:
  - axis labels, titles, legends, annotation clarity.
- Confirm consistent styling across plots.

7) Reporting quality
- Validate generated reports:
  - `executive_summary.json` + `.md`
  - `alignment_report.json` + `.md`
  - `results_debug_report.json` + `.md`
  - `final_project_report.md`
- Ensure high-level conclusions are traceable to produced metrics.

8) Debugging and sanity checks
- Confirm the debug report flags missing/invalid artifacts correctly.
- Verify alignment score and checklist content are present and sensible.

9) Automated test coverage
- Run:
  - `python -m unittest discover -s tests -p "test_*.py"`
- Check tests are deterministic and pass from a clean checkout.
- Note any areas missing tests (especially error handling and edge-case inputs).

10) Code quality and maintainability
- Review module boundaries and helper reuse (`cli_utils.py`, `plot_utils.py`).
- Ensure scripts fail loudly with actionable error messages.
- Confirm no dead code, obvious duplication, or brittle assumptions.

Expected reviewer output format:
- PASS/FAIL summary per section (1–10).
- List of blocking issues first.
- Concrete remediation suggestions with file/module references.
- Optional prioritization: Critical / Important / Nice-to-have.

## Maintainer quick-run commands

```bash
python -m compileall src
python -m unittest discover -s tests -p "test_*.py"
```
