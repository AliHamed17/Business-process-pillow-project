"""
Algorithm Comparison: Inductive Miner vs Heuristics Miner
==========================================================
Academic Justification:
  Comparing multiple discovery algorithms is a standard academic
  requirement in process mining projects.  Each algorithm has different
  strengths:
    - Inductive Miner (Leemans et al., 2014): Guarantees sound models
      and handles infrequent behavior well.
    - Heuristics Miner (Weijters & Ribeiro, 2011): Better at filtering
      noise and captures dependency/frequency relationships.

  This module discovers models with both algorithms, runs token-based
  replay on each, and produces a side-by-side comparison table.

Outputs:
  - algorithm_comparison.csv  : fitness, precision, and model complexity
  - algorithm_comparison.json : machine-readable version
"""

import json
from pathlib import Path

import pandas as pd
import pm4py
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.objects.log.importer.xes import importer as xes_importer


def _evaluate_model(log, net, im, fm, name):
    """Evaluate a Petri net model via token replay and return metrics dict."""
    print(f"  [{name}] Running token-based replay...")
    replayed = token_replay.apply(log, net, im, fm)

    fit_count = sum(1 for r in replayed if r.get('trace_is_fit', False))
    total = len(replayed)
    trace_fitness = fit_count / max(total, 1)

    # Token-level fitness
    total_consumed = sum(r.get('consumed_tokens', 0) for r in replayed)
    total_missing = sum(r.get('missing_tokens', 0) for r in replayed)
    total_produced = sum(r.get('produced_tokens', 0) for r in replayed)
    total_remaining = sum(r.get('remaining_tokens', 0) for r in replayed)

    token_fitness = 1.0
    if (total_consumed + total_missing) > 0:
        token_fitness = 0.5 * (1 - total_missing / max(total_consumed, 1)) + \
                       0.5 * (1 - total_remaining / max(total_produced, 1))
        token_fitness = max(0.0, min(1.0, token_fitness))

    return {
        'algorithm': name,
        'places': len(net.places),
        'transitions': len(net.transitions),
        'arcs': len(net.arcs) if hasattr(net, 'arcs') else 0,
        'trace_fitness': round(trace_fitness, 4),
        'token_fitness': round(token_fitness, 4),
        'fit_traces': fit_count,
        'total_traces': total,
        'fit_pct': round(100 * trace_fitness, 1),
    }


def compare_algorithms(xes_path, output_dir):
    """Discover models with Inductive and Heuristics Miners and compare."""
    output_dir = Path(output_dir)
    print("[Algorithm Comparison] Loading event log...")
    log = xes_importer.apply(str(xes_path))
    print(f"[Algorithm Comparison] Log loaded: {len(log)} traces")

    results = []

    # ── 1. Inductive Miner ────────────────────────────────────────────
    print("[Algorithm Comparison] Discovering with Inductive Miner...")
    try:
        net_ind, im_ind, fm_ind = pm4py.discover_petri_net_inductive(log)
        res_ind = _evaluate_model(log, net_ind, im_ind, fm_ind, 'Inductive Miner')
        results.append(res_ind)
    except Exception as e:
        print(f"  [Inductive Miner] Failed: {e}")

    # ── 2. Heuristics Miner ───────────────────────────────────────────
    print("[Algorithm Comparison] Discovering with Heuristics Miner...")
    try:
        net_heu, im_heu, fm_heu = pm4py.discover_petri_net_heuristics(log)
        res_heu = _evaluate_model(log, net_heu, im_heu, fm_heu, 'Heuristics Miner')
        results.append(res_heu)
    except Exception as e:
        print(f"  [Heuristics Miner] Failed: {e}")

    # ── 3. Alpha Miner (classic baseline) ─────────────────────────────
    print("[Algorithm Comparison] Discovering with Alpha Miner...")
    try:
        net_alpha, im_alpha, fm_alpha = pm4py.discover_petri_net_alpha(log)
        res_alpha = _evaluate_model(log, net_alpha, im_alpha, fm_alpha, 'Alpha Miner')
        results.append(res_alpha)
    except Exception as e:
        print(f"  [Alpha Miner] Failed: {e}")

    # ── Save comparison ───────────────────────────────────────────────
    df = pd.DataFrame(results)
    df.to_csv(output_dir / 'algorithm_comparison.csv', index=False, encoding='utf-8-sig')
    (output_dir / 'algorithm_comparison.json').write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8'
    )

    # Print comparison table
    if not df.empty:
        print("\n[Algorithm Comparison] Results:")
        print(f"{'Algorithm':<25} {'Places':>7} {'Trans':>7} {'Trace Fit':>10} {'Token Fit':>10}")
        print("-" * 65)
        for _, row in df.iterrows():
            print(f"{row['algorithm']:<25} {row['places']:>7} {row['transitions']:>7} "
                  f"{row['trace_fitness']:>10.4f} {row['token_fitness']:>10.4f}")

    print("\nAlgorithm comparison complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compare discovery algorithms")
    parser.add_argument("xes_path", help="Path to event_log.xes")
    parser.add_argument("--output-dir", default="outputs", help="Output directory")
    args = parser.parse_args()

    compare_algorithms(args.xes_path, args.output_dir)
