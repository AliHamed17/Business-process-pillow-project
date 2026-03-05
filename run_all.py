"""
Master Execution Script — Haifa Municipality Process Mining
===========================================================
This script has been updated to use the new unified 16-step pipeline
which includes all academic improvements (Sojourn Time, Temporal Trends,
Statistical Tests, Algorithm Comparison).

Usage:
  python run_all.py path/to/data1.xlsx path/to/data2.xlsx [--output-dir outputs]
"""

import sys
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 3:
        print("Usage error. Please provide the paths to the two raw data Excel files.")
        print("Example:")
        print("  python run_all.py data/file1.xlsx data/file2.xlsx")
        sys.exit(1)
        
    base = Path(__file__).resolve().parent
    pipeline_script = base / "src" / "run_pipeline.py"
    
    if not pipeline_script.exists():
        print(f"[ERROR] Pipeline script not found at {pipeline_script}")
        sys.exit(1)
        
    print(f"\n{'='*60}")
    print(">>> Starting Unified 16-Step Pipeline")
    print(f"{'='*60}")
    
    # Auto-detect if a local virtual environment exists to bypass corrupted global installs
    venv_python = base / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        python_exe = str(venv_python)
        print(">> Using local virtual environment (venv) to run pipeline.")
    else:
        python_exe = sys.executable
        
    # Forward all arguments to run_pipeline.py
    cmd = [python_exe, str(pipeline_script)] + sys.argv[1:]
    
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n[WARNING] Pipeline exited with code {result.returncode}")
    else:
        print("\n" + "="*60)
        print("FULL ANALYSIS PIPELINE COMPLETE")
        print(f"Executive Dashboard: outputs/EXECUTIVE_DASHBOARD.md")
        print(f"Academic Report    : docs/academic_report.md")
        print("="*60)
        
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
