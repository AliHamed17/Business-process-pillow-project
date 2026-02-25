import pm4py
import pandas as pd
import os
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.objects.petri_net.importer import importer as pn_importer
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.petri_net.utils import petri_utils

def perform_conformance(xes_path, output_dir):
    """
    Performs conformance checking against a simplified normative model.
    """
    print("[Conformance] Loading event log...")
    log = xes_importer.apply(xes_path)

    # 1. Define the Normative Model (Simplified Petri Net for the "Happy Path")
    # Steps: Manager Approvals -> HR -> Budget -> CEO -> Post-Decision -> Committee
    print("[Conformance] Constructing normative model...")
    # Using a simple heuristic: We'll create a model of the top variants or a manual sequence.
    # For this script, we'll manually define a linear sequence of 5 critical checkpoints.
    net, initial_marking, final_marking = pm4py.objects.petri_net.obj.PetriNet(), pm4py.objects.petri_net.obj.Marking(), pm4py.objects.petri_net.obj.Marking()
    
    # Places
    p_start = pm4py.objects.petri_net.obj.PetriNet.Place("p_start")
    p1 = pm4py.objects.petri_net.obj.PetriNet.Place("p1")
    p2 = pm4py.objects.petri_net.obj.PetriNet.Place("p2")
    p3 = pm4py.objects.petri_net.obj.PetriNet.Place("p3")
    p4 = pm4py.objects.petri_net.obj.PetriNet.Place("p4")
    p_end = pm4py.objects.petri_net.obj.PetriNet.Place("p_end")
    
    for p in [p_start, p1, p2, p3, p4, p_end]: net.places.add(p)
    initial_marking[p_start] = 1
    final_marking[p_end] = 1

    # Transitions (mapping to actual activity names)
    t1 = pm4py.objects.petri_net.obj.PetriNet.Transition("t1", "אישור מנהל מחלקה")
    t2 = pm4py.objects.petri_net.obj.PetriNet.Transition("t2", "אישור גיוס - החלטת הועדה") # HR/Commitee
    t3 = pm4py.objects.petri_net.obj.PetriNet.Transition("t3", "המלצת תקציב לגיוס")
    t4 = pm4py.objects.petri_net.obj.PetriNet.Transition("t4", 'החלטת מנכ"ל - גיוס')
    t5 = pm4py.objects.petri_net.obj.PetriNet.Transition("t5", 'חוזה נחתם ע"י כל הגורמים')

    for t in [t1, t2, t3, t4, t5]: net.transitions.add(t)

    # Arcs
    petri_utils.add_arc_from_to(p_start, t1, net)
    petri_utils.add_arc_from_to(t1, p1, net)
    petri_utils.add_arc_from_to(p1, t2, net)
    petri_utils.add_arc_from_to(t2, p2, net)
    petri_utils.add_arc_from_to(p2, t3, net)
    petri_utils.add_arc_from_to(t3, p3, net)
    petri_utils.add_arc_from_to(p3, t4, net)
    petri_utils.add_arc_from_to(t4, p4, net)
    petri_utils.add_arc_from_to(p4, t5, net)
    petri_utils.add_arc_from_to(t5, p_end, net)

    # 2. Token Replay
    print("[Conformance] Performing token replay...")
    replayed_traces = token_replay.apply(log, net, initial_marking, final_marking)
    
    # 3. Analyze results
    results = []
    for i, res in enumerate(replayed_traces):
        case_id = log[i].attributes['concept:name']
        results.append({
            'case_id': case_id,
            'trace_is_fit': res['trace_is_fit'],
            'activated_transitions_pct': len(res['activated_transitions']) / 5.0,
            'missing_tokens': res['missing_tokens'],
            'consumed_tokens': res['consumed_tokens'],
            'remaining_tokens': res['remaining_tokens']
        })

    df_conf = pd.DataFrame(results)
    avg_fitness = df_conf['trace_is_fit'].mean()
    print(f"[Conformance] Global Fitness: {avg_fitness:.4f}")

    # Save violations
    violations = df_conf[df_conf['trace_is_fit'] == False].sort_values('activated_transitions_pct')
    conf_path = os.path.join(output_dir, "conformance_violations.csv")
    violations.to_csv(conf_path, index=False)
    print(f"[Conformance] Violations saved to {conf_path}")

    # 4. Global Stats
    summary = {
        "global_fitness": round(float(avg_fitness), 4),
        "total_cases": len(df_conf),
        "fit_cases": int(df_conf['trace_is_fit'].sum()),
        "violation_count": len(violations)
    }
    
    summary_path = os.path.join(output_dir, "conformance_summary.json")
    import json
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    return summary

if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    xes = os.path.join(base, "outputs", "event_log.xes")
    out = os.path.join(base, "outputs")
    
    perform_conformance(xes, out)
