"""
Master Execution Script — Haifa Municipality Process Mining
===========================================================
Runs the full analysis pipeline in order.
Skip data_preprocessing.py if cleaned_log.csv already exists (slow step).
"""
import os
import subprocess
import sys
import time


def run_script(script_path, label=None):
    name = label or os.path.basename(script_path)
    print(f"\n{'='*60}")
    print(f">>> {name}")
    print(f"{'='*60}")
    t0 = time.time()
    result = subprocess.run([sys.executable, script_path])
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"[WARNING] {name} exited with code {result.returncode} ({elapsed:.1f}s)")
    else:
        print(f"[OK] {name} completed in {elapsed:.1f}s")
    return result.returncode


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    src  = os.path.join(base, "src")
    out  = os.path.join(base, "outputs")

    cleaned_log = os.path.join(out, "cleaned_log.csv")

    # Phase 1 — Core Pipeline
    # Skip preprocessing if cleaned log already exists (saves ~3 min)
    if not os.path.exists(cleaned_log):
        run_script(os.path.join(src, "data_preprocessing.py"),    "Phase 1.0 — Data Preprocessing")
    else:
        print(f"\n[SKIP] data_preprocessing.py — cleaned_log.csv already exists.")

    run_script(os.path.join(src, "preprocessing_charts.py"),      "Phase 1.0b — Preprocessing Evidence Charts")
    run_script(os.path.join(src, "process_discovery.py"),         "Phase 1.1 — Process Discovery (DFG + Filter)")
    run_script(os.path.join(src, "performance_analysis.py"),      "Phase 1.2 — Performance / Bottleneck Analysis")
    run_script(os.path.join(src, "workload_analysis.py"),         "Phase 1.3 — Workload Analysis")
    run_script(os.path.join(src, "responsible_change_analysis.py"), "Phase 1.4 — Responsible Change / Reassignment")
    run_script(os.path.join(src, "internal_process_analysis.py"), "Phase 1.5 — Internal Process Complexity")

    # Organisational / SNA
    run_script(os.path.join(src, "organizational_analysis.py"),   "Phase 1.6 — SNA / Handover Analysis")
    run_script(os.path.join(src, "interactive_sna.py"),           "Phase 1.7 — Interactive SNA (HTML)")

    # Delay Forecasting
    run_script(os.path.join(src, "delay_forecasting.py"),         "Phase 1.8 — Delay Forecasting (Regression)")

    # Normative conformance (hand-crafted Petri Net against XES)
    run_script(os.path.join(src, "conformance_checking.py"),      "Phase 1.9 — Conformance Checking (Normative Net)")

    # Phase 2 — Advanced Analysis
    run_script(os.path.join(src, "heuristics_miner.py"),          "Phase 2A — Heuristics Miner + Token Replay")
    run_script(os.path.join(src, "predictive_model.py"),          "Phase 2B — Predictive Model (RF + XGBoost)")
    run_script(os.path.join(src, "advanced_visualizations.py"),   "Phase 2C — Advanced Visualization Suite")
    run_script(os.path.join(src, "sla_analysis.py"),              "Phase 2D — SLA Compliance (Target vs. Actual)")

    # Dashboard synthesis
    run_script(os.path.join(src, "generate_dashboard_summary.py"), "Final   — Executive Dashboard")

    print("\n" + "="*60)
    print("FULL ANALYSIS PIPELINE COMPLETE")
    print(f"Executive Dashboard: outputs/EXECUTIVE_DASHBOARD.md")
    print(f"Academic Report    : docs/academic_report.md")
    print("="*60)
