import argparse
from pathlib import Path

import pandas as pd
import pm4py

from cli_utils import ensure_exists, ensure_output_dir, load_clean_log


REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']


def _variant_frequency(variant_payload):
    """Normalize pm4py variant payload to an integer frequency across pm4py versions."""
    if isinstance(variant_payload, int):
        return variant_payload
    if isinstance(variant_payload, (list, tuple, set)):
        return len(variant_payload)
    return int(variant_payload)


def generate_process_models(logfile_path, output_dir, top_variants=20):
    """Generates process discovery models (DFG, Inductive tree) and variants export."""
    print(f"Reading cleaned log from {logfile_path}")
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='process discovery')

    log = pm4py.format_dataframe(df, case_id='case_id', activity_key='activity', timestamp_key='timestamp')

    print("Generating DFG...")
    _dfg, _start_activities, _end_activities = pm4py.discover_dfg(log)
    print("Skipping DFG visualization export due to Graphviz plugin limitations.")

    print("Generating Inductive Miner model...")
    _tree = pm4py.discover_process_tree_inductive(log)
    print("Skipping process tree export due to Graphviz plugin limitations.")

    print("Extracting variants...")
    variants = pm4py.get_variants(log)
    df_var = pd.DataFrame(
        [{"Variant": str(var), "Frequency": _variant_frequency(payload)} for var, payload in variants.items()]
    ).sort_values(by='Frequency', ascending=False)

    out_path = Path(output_dir) / 'variants.csv'
    df_var.head(top_variants).to_csv(out_path, index=False)
    print(f"Process discovery complete. Saved top {top_variants} variants to {out_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Run process discovery on a cleaned event log")
    parser.add_argument("logfile", help="Path to cleaned_log.csv")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated outputs")
    parser.add_argument("--top-variants", type=int, default=20, help="Number of top variants to export")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logfile = ensure_exists(args.logfile, "Cleaned log")
    output_dir = ensure_output_dir(args.output_dir)
    generate_process_models(logfile, output_dir, top_variants=args.top_variants)
