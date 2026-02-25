import os
os.environ["PATH"] += os.pathsep + r'C:\Program Files\Graphviz\bin'
import pandas as pd
import pm4py
import matplotlib.pyplot as plt

def generate_process_models(logfile_path, output_dir):
    """
    Generates process discovery models (DFG, Inductive tree)
    """
    print(f"Reading cleaned log from {logfile_path}")
    df = pd.read_csv(logfile_path)
    # Ensure datetime parsing
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # pm4py requires standard format
    log = pm4py.format_dataframe(df, case_id='case_id', activity_key='activity', timestamp_key='timestamp')
    
    # 1) DFG
    print("Generating DFG...")
    dfg, start_activities, end_activities = pm4py.discover_dfg(log)
    
    # pm4py.save_vis_dfg(dfg, start_activities, end_activities, os.path.join(output_dir, 'dfg_frequency.svg'))
    # pm4py.save_vis_performance_dfg(dfg, start_activities, end_activities, pm4py.discover_performance_dfg(log), os.path.join(output_dir, 'dfg_performance.svg'))
    print("Skipping DFG visualization export due to Graphviz plugin limitations.")
    
    # 2) Inductive Miner
    print("Generating Inductive Miner model...")
    tree = pm4py.discover_process_tree_inductive(log)
    # pm4py.save_vis_process_tree(tree, os.path.join(output_dir, 'inductive_model.svg'))
    print("Skipping process tree export due to Graphviz plugin limitations.")
    
    # 4) Variant Analysis
    print("Extracting variants...")
    variants = pm4py.get_variants(log)
    var_list = []
    for var, count in variants.items():
        var_list.append({
            'Variant': str(var),
            'Frequency': count
        })
    df_var = pd.DataFrame(var_list).sort_values(by='Frequency', ascending=False)
    
    df_var.head(20).to_csv(os.path.join(output_dir, 'variants.csv'), index=False)
    print("Process discovery complete.")

if __name__ == "__main__":
    out = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining\outputs"
    f = os.path.join(out, "cleaned_log.csv")
    generate_process_models(f, out)
