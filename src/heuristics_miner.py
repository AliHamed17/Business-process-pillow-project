"""
Heuristics Miner & Conformance Checking Module
================================================
Academic Justification:
  The Heuristics Miner (Weijters & Ribeiro, 2011) is preferred over the
  basic Alpha Miner for this dataset because the recruitment log exhibits
  high noise and frequent rework loops (evidenced by the mono-stage variants
  in variants.csv). The Heuristics Miner uses frequency thresholds and
  dependency measures to extract the "main road" of the process, suppressing
  infrequent and back-and-forth edges that clutter a raw DFG.

  Conformance Checking (token-based replay) quantifies how well observed
  cases conform to the normative process path defined in project_requirements.docx:
    Request -> Dept Manager Approval -> Division Head -> HR Recruitment ->
    Budget Recommendation -> CEO Decision -> Tender/Committee
"""

import os
import pandas as pd
import pm4py
from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.objects.conversion.process_tree import converter as pt_converter
from pm4py.objects.petri_net.utils import petri_utils
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
import json


# ---------------------------------------------------------------------------
# Normative (ideal) process path from project_requirements.docx
# ---------------------------------------------------------------------------
NORMATIVE_SEQUENCE = [
    "המלצת איוש ואופן גיוס",          # Request / Staffing Recommendation
    "אישור מנהל מחלקה",                 # Dept Manager Approval
    "אישור מנהל אגף",                   # Division Head Approval (Agaf)
    "אישור ראש מינהל",                  # HR / Division Director Approval
    "המלצת תקציב לגיוס",               # Budget Recommendation
    'החלטת מנכ"ל - גיוס',              # CEO Decision
    "החלטת לשכת ראש העיר",             # Mayor's Office Decision
]


def run_heuristics_miner(logfile_path: str, output_dir: str,
                         dependency_threshold: float = 0.5,
                         dfg_threshold: float = 0.1) -> dict:
    """
    Discovers the process model using the Heuristics Miner.

    Parameters
    ----------
    logfile_path      : path to cleaned_log.csv
    output_dir        : directory for output artefacts
    dependency_threshold : minimum dependency measure (0..1) to include an arc
    dfg_threshold     : minimum relative frequency (0..1) to include a DFG edge
                        (implements the "filter edges < 10%" requirement)

    Returns
    -------
    dict with keys: heuristics_net, petri_net, initial_marking, final_marking
    """
    print("[Heuristics Miner] Loading cleaned log...")
    df = pd.read_csv(logfile_path, encoding='utf-8-sig')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df.dropna(subset=['timestamp'], inplace=True)

    log = pm4py.format_dataframe(
        df, case_id='case_id', activity_key='activity', timestamp_key='timestamp'
    )
    event_log = pm4py.convert_to_event_log(log)

    # --- Heuristics Net discovery ---
    print(f"[Heuristics Miner] Running with dependency_threshold={dependency_threshold}...")
    hnet = heuristics_miner.apply_heu(
        event_log,
        parameters={
            heuristics_miner.Variants.CLASSIC.value.Parameters.DEPENDENCY_THRESH: dependency_threshold,
            heuristics_miner.Variants.CLASSIC.value.Parameters.MIN_ACT_COUNT: 10,
            heuristics_miner.Variants.CLASSIC.value.Parameters.MIN_DFG_OCCURRENCES: 10,
        }
    )
    print("[Heuristics Miner] Heuristics Net discovered.")

    # --- Convert to Petri Net for conformance checking ---
    petri_net, im, fm = pm4py.convert_to_petri_net(hnet)
    print("[Heuristics Miner] Converted to Petri Net.")

    # --- Save Heuristics Net visualisation (text summary) ---
    _save_hnet_summary(hnet, output_dir)

    return {
        "heuristics_net": hnet,
        "petri_net": petri_net,
        "initial_marking": im,
        "final_marking": fm,
        "event_log": event_log,
    }


def run_conformance_checking(model_artefacts: dict, output_dir: str) -> pd.DataFrame:
    """
    Token-based replay conformance checking against the Heuristics Miner Petri Net.

    Academic Justification:
      Token-Based Replay (van der Aalst, 2016) is the standard approach for
      measuring fitness in process mining. It produces four metrics:
        - fitness    : fraction of traces that can be fully replayed
        - precision  : how much of the model behaviour is observed
        - recall     : how many observed behaviours fit the model
        - f-measure  : harmonic mean of precision and recall

    Returns a DataFrame with per-trace conformance results.
    """
    petri_net = model_artefacts["petri_net"]
    im = model_artefacts["initial_marking"]
    fm = model_artefacts["final_marking"]
    event_log = model_artefacts["event_log"]

    print("[Conformance] Running token-based replay...")
    replayed = token_replay.apply(
        event_log, petri_net, im, fm,
        parameters={
            token_replay.Variants.TOKEN_REPLAY.value.Parameters.CONSIDER_REMAINING_IN_FITNESS: True
        }
    )

    records = []
    for i, trace_result in enumerate(replayed):
        records.append({
            "trace_index": i,
            "trace_is_fit": trace_result.get("trace_is_fit", False),
            "fitness": trace_result.get("trace_fitness", 0.0),
            "produced_tokens": trace_result.get("produced_tokens", 0),
            "consumed_tokens": trace_result.get("consumed_tokens", 0),
            "missing_tokens": trace_result.get("missing_tokens", 0),
            "remaining_tokens": trace_result.get("remaining_tokens", 0),
        })

    df_conf = pd.DataFrame(records)

    # --- Aggregate fitness score ---
    overall_fitness = df_conf["fitness"].mean()
    fit_traces_pct = df_conf["trace_is_fit"].mean() * 100

    print(f"[Conformance] Overall Fitness Score : {overall_fitness:.4f}")
    print(f"[Conformance] Fully Fitting Traces  : {fit_traces_pct:.1f}%")

    # --- Compare with normative path ---
    conformance_summary = {
        "overall_fitness": round(overall_fitness, 4),
        "fit_traces_pct": round(fit_traces_pct, 2),
        "total_traces": len(df_conf),
        "fit_traces": int(df_conf["trace_is_fit"].sum()),
        "avg_missing_tokens": round(df_conf["missing_tokens"].mean(), 2),
        "normative_sequence": NORMATIVE_SEQUENCE,
    }

    # Save per-trace results
    out_csv = os.path.join(output_dir, "conformance_results.csv")
    df_conf.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f"[Conformance] Per-trace results saved to {out_csv}")

    # Save summary JSON
    out_json = os.path.join(output_dir, "conformance_summary.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(conformance_summary, f, ensure_ascii=False, indent=2)
    print(f"[Conformance] Summary saved to {out_json}")

    return df_conf, conformance_summary


def _save_hnet_summary(hnet, output_dir: str):
    """Saves a human-readable text summary of the Heuristics Net arcs."""
    lines = ["Heuristics Net – Main Process Arcs", "=" * 50]

    # Extract dependency graph from the heuristics net
    try:
        dep_graph = hnet.dependency_graph
        # Sort by dependency value descending
        sorted_arcs = sorted(dep_graph.items(), key=lambda x: x[1], reverse=True)
        lines.append(f"Total arcs discovered: {len(sorted_arcs)}")
        lines.append("")
        lines.append(f"{'Source Activity':<55} {'Target Activity':<55} {'Dependency':>12}")
        lines.append("-" * 125)
        for (src, tgt), dep in sorted_arcs:
            lines.append(f"{src:<55} {tgt:<55} {dep:>12.4f}")
    except Exception as e:
        lines.append(f"Could not extract dependency graph details: {e}")

    out_path = os.path.join(output_dir, "heuristics_net_summary.txt")
    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))
    print(f"[Heuristics Miner] Net summary saved to {out_path}")


def run_normative_gap_analysis(logfile_path: str, output_dir: str) -> pd.DataFrame:
    """
    Checks how many cases visit each stage in the normative sequence,
    and in what order, producing a gap analysis table.
    """
    print("[Gap Analysis] Loading cleaned log for normative path comparison...")
    df = pd.read_csv(logfile_path, encoding='utf-8-sig')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df.sort_values(['case_id', 'timestamp'], inplace=True)

    records = []
    for stage in NORMATIVE_SEQUENCE:
        cases_with_stage = df[df['activity'] == stage]['case_id'].nunique()
        total_cases = df['case_id'].nunique()
        records.append({
            "normative_stage": stage,
            "cases_visiting": cases_with_stage,
            "total_cases": total_cases,
            "coverage_pct": round(cases_with_stage / total_cases * 100, 1),
        })

    df_gap = pd.DataFrame(records)
    df_gap["stage_order"] = range(1, len(df_gap) + 1)

    out_csv = os.path.join(output_dir, "normative_gap_analysis.csv")
    df_gap.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f"[Gap Analysis] Saved to {out_csv}")
    # Use encode/replace to handle Hebrew on Windows console
    summary_str = df_gap[['stage_order','normative_stage','cases_visiting','coverage_pct']].to_string(index=False)
    print(summary_str.encode('utf-8', errors='replace').decode('ascii', errors='replace'))

    return df_gap


if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    logfile = os.path.join(base, "outputs", "cleaned_log.csv")
    outdir = os.path.join(base, "outputs")

    # 1. Heuristics Miner
    artefacts = run_heuristics_miner(logfile, outdir, dependency_threshold=0.5)

    # 2. Conformance Checking
    df_conf, summary = run_conformance_checking(artefacts, outdir)

    # 3. Normative Gap Analysis
    df_gap = run_normative_gap_analysis(logfile, outdir)

    print("\n=== Phase 2A Complete ===")
    print(f"Fitness Score     : {summary['overall_fitness']}")
    print(f"Fitting Traces    : {summary['fit_traces_pct']}%")
    print(f"Total Traces      : {summary['total_traces']}")
