"""
Conformance Checking Module (Improved)
========================================
Academic Justification:
  Instead of using a manually-constructed 5-transition Petri Net, this
  module uses the Inductive Miner (Leemans et al., 2014) to discover a
  process model from the event log itself, then checks conformance of
  every trace against the discovered model using Token-Based Replay
  (van der Aalst, 2016).

  This approach:
  1. Captures the actual process structure including parallel tracks,
     optional stages (manager skip logic), and the committee loop.
  2. Produces a fitness score that genuinely reflects how well traces
     follow the discovered normative model.
  3. Additionally checks against a NORMATIVE_SEQUENCE of critical
     checkpoints to identify specific stage skips.

Outputs:
  - conformance_results.csv    : per-case fitness metrics
  - conformance_violations.csv : non-fitting traces only
  - conformance_summary.json   : global fitness statistics
"""

import json
import os
from pathlib import Path

import pandas as pd
import pm4py
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.objects.log.importer.xes import importer as xes_importer


# Critical checkpoints in the normative process flow (from project requirements)
NORMATIVE_CHECKPOINTS = [
    "אישור מנהל מחלקה",            # Dept Manager Approval
    "אישור מנהל אגף",              # Division Manager Approval
    "אישור ראש מינהל",             # Head of Administration
    "המלצת איוש ואופן גיוס",       # Staffing Recommendation
    "המלצת תקציב לגיוס",           # Budget Recommendation
    'החלטת מנכ"ל - גיוס',          # CEO Decision
    "החלטת לשכת ראש העיר",         # Mayor's Office Decision
]


def perform_conformance(xes_path, output_dir):
    """
    Performs conformance checking using two approaches:
    1. Discovered model (Inductive Miner) with Token Replay
    2. Normative checkpoint coverage analysis
    """
    output_dir = Path(output_dir)
    print("[Conformance] Loading event log...")
    log = xes_importer.apply(str(xes_path))

    # ── Approach 1: Discovered Model Conformance ──────────────────────
    print("[Conformance] Discovering process model via Inductive Miner...")
    net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(log)
    print(f"[Conformance] Discovered Petri Net: {len(net.places)} places, "
          f"{len(net.transitions)} transitions")

    print("[Conformance] Performing token-based replay...")
    replayed_traces = token_replay.apply(log, net, initial_marking, final_marking)

    # Collect per-case results
    results = []
    for i, res in enumerate(replayed_traces):
        case_id = log[i].attributes.get('concept:name', str(i))
        n_transitions = len(net.transitions) or 1
        results.append({
            'case_id': case_id,
            'trace_is_fit': res.get('trace_is_fit', False),
            'activated_transitions': len(res.get('activated_transitions', [])),
            'total_transitions': n_transitions,
            'activated_pct': len(res.get('activated_transitions', [])) / n_transitions,
            'missing_tokens': res.get('missing_tokens', 0),
            'consumed_tokens': res.get('consumed_tokens', 0),
            'remaining_tokens': res.get('remaining_tokens', 0),
            'produced_tokens': res.get('produced_tokens', 0),
        })

    df_conf = pd.DataFrame(results)

    # Fitness calculation
    if not df_conf.empty:
        fit_count = int(df_conf['trace_is_fit'].sum())
        total = len(df_conf)
        avg_fitness = df_conf['trace_is_fit'].mean()

        # Token-based fitness (more granular)
        total_consumed = df_conf['consumed_tokens'].sum()
        total_missing = df_conf['missing_tokens'].sum()
        total_produced = df_conf['produced_tokens'].sum()
        total_remaining = df_conf['remaining_tokens'].sum()
        token_fitness = 1.0
        if (total_consumed + total_missing) > 0:
            token_fitness = 0.5 * (1 - total_missing / max(total_consumed, 1)) + \
                           0.5 * (1 - total_remaining / max(total_produced, 1))
            token_fitness = max(0.0, min(1.0, token_fitness))
    else:
        fit_count = 0
        total = 0
        avg_fitness = 0.0
        token_fitness = 0.0

    print(f"[Conformance] Trace Fitness: {avg_fitness:.4f} "
          f"({fit_count}/{total} traces fit)")
    print(f"[Conformance] Token Fitness: {token_fitness:.4f}")

    # Save all results
    df_conf.to_csv(output_dir / 'conformance_results.csv', index=False)

    # Save violations only
    violations = df_conf[~df_conf['trace_is_fit']].sort_values('activated_pct')
    violations.to_csv(output_dir / 'conformance_violations.csv', index=False)
    print(f"[Conformance] {len(violations)} non-fitting traces saved")

    # ── Approach 2: Normative Checkpoint Coverage ─────────────────────
    print("[Conformance] Checking normative checkpoint coverage...")
    checkpoint_results = []
    for i, trace in enumerate(log):
        case_id = trace.attributes.get('concept:name', str(i))
        activities = [event['concept:name'] for event in trace]

        row = {'case_id': case_id}
        for checkpoint in NORMATIVE_CHECKPOINTS:
            row[f'has_{checkpoint}'] = checkpoint in activities
        row['checkpoints_hit'] = sum(
            1 for cp in NORMATIVE_CHECKPOINTS if cp in activities
        )
        row['checkpoint_coverage'] = row['checkpoints_hit'] / len(NORMATIVE_CHECKPOINTS)
        checkpoint_results.append(row)

    df_checkpoints = pd.DataFrame(checkpoint_results)
    df_checkpoints.to_csv(output_dir / 'checkpoint_coverage.csv', index=False)

    # Summarize which checkpoints are most frequently skipped
    skip_rates = {}
    for cp in NORMATIVE_CHECKPOINTS:
        col = f'has_{cp}'
        if col in df_checkpoints.columns:
            skip_rates[cp] = round(1.0 - df_checkpoints[col].mean(), 4)

    # ── Summary ──────────────────────────────────────────────────────
    summary = {
        "model_type": "Inductive Miner (discovered)",
        "net_places": len(net.places),
        "net_transitions": len(net.transitions),
        "trace_fitness": round(float(avg_fitness), 4),
        "token_fitness": round(float(token_fitness), 4),
        "total_cases": total,
        "fit_cases": fit_count,
        "violation_count": len(violations),
        "checkpoint_skip_rates": skip_rates,
        "avg_checkpoint_coverage": round(
            float(df_checkpoints['checkpoint_coverage'].mean()), 4
        ) if not df_checkpoints.empty else 0.0,
    }

    summary_path = output_dir / 'conformance_summary.json'
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    print(f"[Conformance] Summary saved to {summary_path}")

    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Conformance checking against discovered model")
    parser.add_argument("xes_path", help="Path to event_log.xes")
    parser.add_argument("--output-dir", default="outputs", help="Output directory")
    args = parser.parse_args()

    perform_conformance(args.xes_path, args.output_dir)
