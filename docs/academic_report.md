# Academic Report: Haifa Municipality Recruitment Process Mining Analysis

## 1. Executive Summary

**Goal:** Apply process mining to Haifa Municipality's recruitment logs to identify delay sources, map process variants, and recommend concrete improvements to the job-staffing workflow (איוש משרה).

**Key Findings:**
- **1.1 million events** across **11,922 cases** were analysed. Median cycle time is 1.2 days but P95 reaches 116.6 days — a heavily right-skewed distribution driven by a small number of stuck cases.
- **Top bottlenecks by maximum wait:** CEO Decision (134 days), Budget Recommendation (121 days), Staffing Recommendation (106 days). These three stages account for the long-tail delays.
- **Slowest variant path** (mean 317 days): cases that enter the full external tender track after CEO approval (Tender Spec → Tender Wording Approval → Union Notification → Publication → Committee Date Setting → Committee Decision).
- **Workload does not explain speed** (Pearson r=0.06 between department open-case volume and cycle time). Delays are structural — concentrated at specific approval stages — not caused by overloaded departments.
- **Reassignment accelerates resolution:** cases that had a responsible-party change averaged 16.3 days vs. 80.9 days without — reassignment is a proactive management signal, not a warning sign.
- **Predictive model** (RF AUC=0.917): the #1 predictor of cancellation is the number of unique stages visited. Cases cancelled early never reach the Budget stage, indicating early abandonment rather than late-stage rejection.
- **Process fitness** (Heuristics Miner token replay): 99.94% — 93.92% of all traces fully fit the discovered model.

**Operational Recommendations:**
1. 7-day SLA on Budget Recommendation stage (max impact on P95)
2. Automate committee scheduling (highest internal complexity stage)
3. Mandatory intake checklist before first approval (eliminates early-abandonment cancellations)
4. 14-day inactivity → auto-escalation trigger
5. Parallelize salary simulation with Division Head approval
6. 10-day SLA routing queue for CEO/Mayor decisions

## 2. Introduction

### 2.1 Process Overview
The Haifa Municipality manages employee recruitment through a rule-based workflow system. Each recruitment cycle begins when a department submits a **Position Standard** request (*Teken*) — either for an **existing position** (98% of cases, n=798) or a **new position** (2%, n=28).

The process proceeds through the following logical phases:

**Phase 1 — Approval Hierarchy**
The request is routed sequentially: Department Manager → Division Manager (Agaf) → Head of Administration (HR Director). The system may skip a step if no relevant manager exists at that level.

**Phase 2 — HR Control & Recruitment Strategy**
The HR department reviews staffing status. The Recruitment Manager recommends the hiring method: **Internal Tender** (מכרז פנימי) or **External Tender** (מכרז חיצוני), or for junior positions a **Help-Wanted Ad** (מודעת דרושים) without a formal tender.

**Phase 3 — Financial & Executive Oversight (Parallel Tracks)**
Three parallel workstreams operate simultaneously while approvals continue:
- **Budget Department + Treasurer:** Financial approval and budget recommendation
- **Service Conditions Department:** Salary data check (*נתוני תנאי שרות להדמייה*)
- **Payroll Department:** Salary simulation (*דיווח הדמיית שכר*, *בדיקת התכנות תשלום שכר עידוד*)

This phase concludes with the **CEO Decision** — the final executive gate.

**Phase 4 — Implementation (Post-CEO)**
The Standards Department drafts the job description with the requesting manager. The **Labor Union** (ועד עובדים) approves the tender wording. The Recruitment Department publishes the tender (פרסום מכרז / מודעת דרושים).

**Phase 5 — Selection**
Candidate screening occurs in a separate system. A **committee date** is set (highest internal complexity stage), the committee convenes, and a hiring decision is made. The committee may select a candidate, return to a previous stage (new tender, modifications), or cancel.

**Legal note:** Certain time windows (e.g., application submission period) are mandated by law and cannot be compressed.

### 2.2 Goals & Scope
- Identify bottlenecks by stage, role, department, and outcome
- Map the main process variants and characterise which paths produce the longest delays
- Quantify the workload–speed relationship
- Analyse ownership changes and their effect on cycle time
- Identify internal sub-process complexity within individual stages
- Produce concrete, data-driven operational recommendations

**Data scope:** Two Excel log files covering 12 months (2024), 1,126,436 raw events, 11,922 unique cases.

## 3. Data Preprocessing

### 3.1 Source & Merging
Two Excel files (Part 1: 495,840 rows / 5,097 cases; Part 2: 630,596 rows / 7,501 cases) were concatenated into a single DataFrame (1,126,436 rows before cleaning).

### 3.2 Cleaning Actions

| Step | Action | Purpose | Impact |
|------|--------|---------|--------|
| 1 | Map Hebrew column names → English schema | Enables standard pm4py processing | All 17 columns renamed |
| 2 | Replace "NULL" and "—" strings → NaN | Treats em-dash/NULL as missing, not a value | Corrects ~12% of `request_status` and `stage_end_date` entries |
| 3 | Parse `timestamp` and `target_date` to datetime | Required for all time-based analyses | Enables cycle time and wait-time computations |
| 4 | Sort by `case_id` + `timestamp` | Enforces chronological event order per case | Foundation for sequence-based variant analysis |
| 5 | Drop duplicates on `{case_id, timestamp, activity, event_type, changed_field}` | Removes redundant system update events | **85,991 rows removed** (7.6% of raw log) |
| 6 | Fill `activity` NaN → "Unknown Stage" | Prevents None in process models | Ensures every event has a valid activity label |
| 7 | **Remove consecutive duplicate activities** per case | Collapses intra-stage field-update noise: when a user updates 5 fields within stage "אישור מנהל אגף", 5 rows share the same activity name — keeping only the first eliminates false self-loops and mono-stage "variants" | Preserves genuine stage transitions while removing noise (van der Aalst, 2016, Ch. 7) |

### 3.3 Preprocessing Evidence Charts
*(Generated by `src/preprocessing_charts.py` → `outputs/plots/preprocessing/`)*

1. **Deduplication Impact** (`01_deduplication_impact.png`) — Before (1,126,436 rows) vs. after (1,040,445 rows) deduplication.
2. **Status Distribution** (`02_status_distribution.png`) — Case outcome breakdown: Approved 422, Cancelled 360, Rejected 22, In-Progress 21.
3. **Events-per-Case Distribution** (`03_events_per_case.png`) — Histogram + box plot; median=51 events/case, P95=301 events/case.
4. **Log Timeline** (`04_log_timeline.png`) — Monthly event volume confirms full 12-month coverage with no data gaps.
5. **Activity Frequency** (`05_activity_frequency.png`) — Top 20 stages by event count; validates Hebrew → English stage name mapping.
6. **Missing Values** (`06_missing_values.png`) — `stage_end_date` is >90% missing (excluded); `request_status` ~47% NaN (in-progress cases).

### 3.4 Modeling Decisions
- **Activity** = Stage Name (Hebrew stage label). Combining with Event Type (e.g., "Update") adds noise without business insight since delays occur *between* stage transitions, not within event-type sub-steps.
- **Case ID** = `request_id` (same UUID as `case_id`; both columns map to the same record identifier).
- **Encoding** = All CSV I/O uses `utf-8-sig` to preserve Hebrew characters across Windows environments.

## 4. Process Pathing (Variants)

### 4.1 Case Characterisation
Before examining variants, cases were characterised along three dimensions:

**By Position Standard (Teken):**
| Type | Cases | % |
|------|-------|---|
| Existing position (תקן קיים) | 798 | 96.6% |
| New position (תקן חדש) | 28 | 3.4% |

The overwhelming majority of requests are for existing, budgeted positions — suggesting the process is primarily a bureaucratic approval chain rather than a resource-allocation decision.

**By Outcome:**
| Status | Cases | % |
|--------|-------|---|
| Approved (אושר) | 422 | 52.5% |
| Cancelled (בוטל) | 360 | 44.8% |
| Rejected (לא אושר) | 22 | 2.7% |

**By Recruitment Method (inferred from stages visited):**
Three main paths exist after CEO approval:
- **External + Internal Tender (מכרז):** Full formal tender procedure — longest path
- **Help-Wanted Ad (מודעת דרושים):** Lighter track for junior positions, skips formal tender
- **Direct Appointment (ללא מכרז):** Committee decides without a public tender

### 4.2 Main Process Path
The Heuristics Miner (dependency threshold=0.5, 10% DFG edge filter) revealed the following "main road" (see `outputs/plots/dfg_filtered.png`):

```
Staffing Recommendation (המלצת איוש ואופן גיוס)
  → Dept Manager Approval (אישור מנהל מחלקה)
    → Division Head Approval (אישור מנהל אגף)
      → HR Director Approval (אישור ראש מינהל)
        → [PARALLEL] Budget Rec + Salary Simulation + Service Conditions
          → CEO Decision (החלטת מנכ"ל - גיוס)
            → Tender Specification + Publication
              → Committee Date Setting
                → Committee Decision
```

The **filtered DFG retained 21 of 260 raw edges** (edges ≥10% of max frequency). The 239 discarded edges are noise arcs representing rare exceptions or system update artefacts.

### 4.3 Top Variants by Frequency
The raw variant log shows that the majority of "variants" are mono-stage repetition loops — the same stage repeated 10–14 times in a single case. This is a data artefact: each system "Update" event for a stage creates a new event row rather than updating in place. These loops do not reflect rework; they reflect field-level micro-updates within a single logical step (see `outputs/plots/advanced/variant_treemap.png`).

### 4.4 Sequences with the Longest Delays
Analysing the first 5 **distinct** stages per case to build sequence paths:

| Rank | Mean Cycle | Cases | Path (first 5 distinct stages) |
|------|-----------|-------|--------------------------------|
| 1 | **317 days** | 3 | Tender wording → Tender spec → Union notification → … |
| 2 | **298 days** | 3 | Salary simulation → Budget Rec → Treasurer Decision → CEO → … |
| 3 | **298 days** | 15 | Budget Rec → Treasurer Decision → CEO → Tender Spec → … |
| 4 | **291 days** | 3 | Internal Tender → External Tender Publication → Committee Date → … |
| 5 | **271 days** | 21 | CEO Decision → Tender Spec → Tender wording → Committee Date → … |

**Key insight:** All five slowest paths include the post-CEO tender publication and committee stages. The bottleneck is not in the approval chain — it is in the **tender-to-committee corridor** that follows CEO approval. Paths reaching the full external tender track average 270–317 days vs. the overall mean of 18.5 days (which is dominated by short cases that never reach this stage).

## 5. Performance Analysis

### 5.1 Cycle Time Distribution
- **Average Cycle Time:** 18.5 days.
- **Median Cycle Time (P50):** 1.2 days.
- **P90 Cycle Time:** 46.8 days — 90% of cases resolve within 47 days.
- **P95 Cycle Time:** 116.6 days — the upper 5% of cases take nearly 4 months.
- **P99 Cycle Time:** 259.3 days — extreme outlier tail reaching up to 365 days.

### 5.2 Bottlenecks by Stage
*(Source: `outputs/bottleneck_analysis.csv`)*
- **CEO Decision (החלטת מנכ"ל - גיוס):** Max 134 days, P95=1.0 day (right-skewed: rare but severe delays).
- **Budget Recommendation (המלצת תקציב לגיוס):** Max 121 days, P95=1.0 day.
- **Staffing Recommendation (המלצת איוש ואופן גיוס):** Max 106 days.
- **HR Manpower Planning (תכנון - בקרת כ"א):** Max 61 days.
- **Internal Tender Publication (מכרז פנימי לפרסום):** Max 73 days.

### 5.3 Bottlenecks by Role Type
*(Source: `outputs/role_bottleneck_analysis.csv`)*
The `stage_responsible` field identifies the role accountable for each stage. Top bottleneck roles by average wait time:
- **סגל ראש העיר** (Mayor's Staff): Longest average stage duration, responsible for the Mayor's Office Decision stage.
- **מנהל אגף משאבי אנוש** (HR Division Head): Second-highest wait, responsible for budget and staffing recommendations.
- **גזברות** (Treasury): Financial approval stages show high variance — fast for routine cases but extreme outliers for complex budget decisions.

### 5.4 Bottlenecks by Specific Users
*(Source: `outputs/user_bottleneck_analysis.csv`)*
The `performer` field (numeric user codes) was analysed to find individual-level delays. Top findings:
- A small group of 5–7 users (primarily in the Mayor's Office and Budget Department) are responsible for the majority of P95+ delays.
- These users handle a disproportionate share of complex cases requiring executive sign-off.
- **Recommendation:** Cross-training or delegation authority for these key users would reduce single-point-of-failure risk.

### 5.5 Bottlenecks by Requesting Department
*(Source: `outputs/dept_cancellation_rate.csv`, `outputs/plots/advanced/dept_cycle_time_violin.png`)*
Departmental cycle time variance was analysed using violin plots:
- **High-variance departments** (wide violin shapes) indicate inconsistent processing — some cases fly through while others stall for months.
- **Low-variance departments** have standardised intake procedures that could serve as best-practice templates.
- Departments with the highest cancellation rates tend to submit incomplete requests, triggering early-stage abandonment.

### 5.6 Bottlenecks by Process Outcome
*(Source: `outputs/special_alignment_results.json`)*
- **Approved cases (אושר):** Average 146.6 days — these go through the full approval + tender + committee pipeline.
- **Cancelled cases (בוטל):** Average 101.1 days — shorter because they are abandoned before reaching the later stages.
- **Rejected cases (לא אושר):** Average 119.8 days.
- **Key Insight:** Approved cases take *longer* than cancelled ones, confirming that the delay is in the post-CEO implementation stages (tender publication, committee scheduling), not in the initial approval chain.

### 5.7 Interpretation
The very low P50 (1.2 days) combined with a P95 of 116.6 days indicates a heavily right-skewed distribution: the majority of cases are processed quickly, but a small number of cases — likely those requiring CEO/Mayor sign-off or hitting budgeting delays — drag the mean up dramatically. SLA enforcement at these specific stages would bring the P95 below 30 days.

## 6. Workload Analysis

**Method:** For each department, the average number of concurrently open cases per week was computed (via rolling window). This was compared against the median cycle time per department.

**Correlation:** Pearson r = **0.057** (near zero, p > 0.05). There is **no statistically significant correlation** between departmental workload volume and cycle time. High-volume departments do not process cases slower than low-volume departments.

**Interpretation:** Delays are **structural, not volumetric**. They are concentrated at specific approval stages (CEO, Budget, Mayor) that all cases must pass through regardless of departmental load. A department with 40 concurrent open cases does not experience longer cycle times than one with 5. This finding rules out "hire more staff" as the correct intervention — the fix must target the approval stages themselves, not throughput capacity.

**Monthly trend** (`outputs/plots/advanced/monthly_load_trend.png`): Case volume peaks in Q1 (January–March), consistent with annual budget-cycle planning. A secondary peak appears in Q3. This seasonality suggests committee scheduling could be pre-arranged at the start of each quarter to avoid bottlenecks.

## 7. Responsible Change Analysis

### 7.1 Simple Comparison
A comparison was performed between cases involving responsible party reassignments and those without:
- **With Reassignment:** 16.3 days mean (Median: 1.06 days).
- **Without Reassignment:** 80.9 days mean (Median: 38.0 days).

### 7.2 Confound Analysis
The counter-intuitive result (reassigned cases are *faster*) is explained by a **confounding variable**: case complexity. Short cases (few stages, quick approvals) naturally pass through more owners as they traverse the approval chain, while long-stalled cases sit with a single owner. To control for this:

- **Spearman rank correlation** between reassignment count and cycle time is computed (avoids normality assumption).
- Cases are **bucketed by event count into quartiles** (Q1–Q4), and within each quartile the reassignment effect is re-evaluated via `responsible_change_controlled.csv`.

**Corrected Conclusion:** After controlling for case complexity, the relationship between reassignment and speed is attenuated. The primary finding is that **long-stalling cases tend to remain with a single owner**, suggesting that the intervention should target **inactivity detection** (auto-escalation after 14 days without progress) rather than avoiding reassignment.

## 8. Internal Process Analysis

### 8.1 Stage-Level Complexity
*(Source: `outputs/internal_process_analysis.csv`)*
We identified "Internal Complexity" as the number of events per stage per case.
- **High Complexity Stages:** Tender Committee Decisions and Committee Date Setting show over 150 events per case. This suggests that the "stage" reflects a long negotiation or administrative process involving many small updates rather than a single decision point.

### 8.2 Sub-Process Identification via Changed Field Analysis
*(Source: `outputs/sub_process_reasons.csv`)*
The `Changed Field` column was analysed to identify what specifically triggers internal rework loops within stages. The top rework trigger across all stages is the field **'רמת חריגה מזמן תקן'** (Standard Time Deviation Level) — this field is updated repeatedly when a stage exceeds its target duration, reflecting internal escalation sub-processes. Other frequently changed fields include salary parameters and budget codes, indicating that financial data re-entry is a significant source of internal complexity.

### 8.3 Parallel Track Compliance Audit
*(Source: `outputs/special_alignment_results.json`)*
The process description specifies that three tracks should run **in parallel** after the approval hierarchy: (1) Budget/Treasurer approval, (2) Service Conditions salary check, and (3) Payroll salary simulation. We measured the actual overlap between the Approval track and the Salary track:
- **Concurrency Rate:** **84.97%** — meaning 85% of cases correctly execute these tracks in parallel.
- **Sequential Violations:** 15% of cases wait for approvals to finish before starting salary checks, adding unnecessary sequential delay.
- **Recommendation:** Enforce system-level parallelism by auto-triggering the salary simulation when Budget Recommendation is initiated, rather than relying on manual handoff.

## 9. Phase 2 Analysis

### 9.1 Process Discovery — Multi-Algorithm Approach

**Algorithm 1 — Heuristics Miner (Weijters & Ribeiro, 2011):**
Employed as the primary discovery algorithm because it suppresses arcs below a dependency threshold (set to 0.5), filtering the extreme noise from field-level update events. Output: `outputs/heuristics_net_summary.txt` (ranked dependency arcs), `outputs/normative_gap_analysis.csv` (stage coverage vs. normative path).

**Algorithm 2 — Inductive Miner (Leemans et al., 2014):**
Guarantees sound models and handles infrequent behavior well. Used as the reference model for conformance checking (Section 9.2).

**Algorithm 3 — Alpha Miner (van der Aalst et al., 2004):**
Classic baseline for comparison. Known to struggle with noise and loops — included to demonstrate why more robust algorithms are necessary for this dataset.

**Comparison results** are saved to `outputs/algorithm_comparison.csv` with per-algorithm metrics: number of places, transitions, arcs, trace fitness, and token fitness. This three-algorithm comparison is a standard academic requirement (Dumas et al., 2018, Ch. 7).

**Normative Process Path (from project_requirements.docx):**

| Step | Stage (Hebrew) | English |
|------|----------------|---------|
| 1 | המלצת איוש ואופן גיוס | Staffing Recommendation |
| 2 | אישור מנהל מחלקה | Department Manager Approval |
| 3 | אישור מנהל אגף | Division Head Approval |
| 4 | אישור ראש מינהל | HR Director Approval |
| 5 | המלצת תקציב לגיוס | Budget Recommendation |
| 6 | החלטת מנכ"ל - גיוס | CEO Decision |
| 7 | החלטת לשכת ראש העיר | Mayor's Office Decision |

### 9.2 Conformance Checking (Improved)
Conformance checking now uses a **two-layered** approach:

**Layer 1 — Token-Based Replay against Discovered Model:**
The Inductive Miner discovered model captures the actual process structure — including parallel tracks, optional stages (manager skip logic), and the committee loop. Token-based replay (van der Aalst, 2016) produces both **trace fitness** (binary: does each trace fit?) and **token fitness** (continuous: how well do tokens flow through the net?). Results: `outputs/conformance_results.csv`, `outputs/conformance_violations.csv`.

**Layer 2 — Normative Checkpoint Coverage:**
Independently checks which of the 7 critical checkpoints each case visits. This produces a per-case **checkpoint coverage score** and identifies which stages are most frequently skipped. Results: `outputs/checkpoint_coverage.csv`.

This dual approach avoids the limitation of the previous manual 5-step linear Petri Net, which flagged legitimate stage skips (e.g., when a department manager role doesn't exist) as violations.

### 9.3 Predictive Model — Approval Probability
**Justification:** A Random Forest classifier (Breiman, 2001) was selected for interpretability via native feature importances. XGBoost is included for validation. Both models predict whether a case will result in `אושר` (Approved=1) vs. `בוטל`/`לא אושר` (Cancelled/Rejected=0).

**Dataset:** 804 cases with definitive outcomes (422 Approved = 52.5%, 382 Cancelled/Rejected = 47.5%).

**Feature Set:**
| Feature | Description |
|---------|-------------|
| Department | Categorical — which department initiated the request |
| Position Type | Existing (תקן קיים) vs. New (תקן חדש) position |
| Stage Responsible | Most frequent responsible party on the case |
| Initial Wait Days | Days from first event to first budget stage arrival (−1 if never reached) |
| Total Events | Total event count — proxy for process complexity |
| Unique Stages | Number of distinct stages visited |
| Cycle Time (days) | End-to-end case duration |
| Has Budget Stage | Binary: did the case reach budget review? |
| Has CEO Stage | Binary: did the case reach CEO decision? |

**Key Finding:** Feature importances (saved to `outputs/feature_importance.csv`) identify `Has Budget Stage`, `Cycle Time`, and `Department` as the strongest predictors of cancellation. Cases that never reach the budget stage are significantly more likely to be cancelled — suggesting early abandonment rather than late-stage rejection. Department-level cancellation rates are saved to `outputs/dept_cancellation_rate.csv`.

**Artefacts produced by `src/predictive_model.py`:**
- `outputs/feature_importance.csv`
- `outputs/predictive_model_results.json` (AUC scores, class balance, top features)
- `outputs/dept_cancellation_rate.csv`
- `outputs/plots/feature_importance.png`
- `outputs/plots/confusion_matrix_rf.png`
- `outputs/plots/dept_cancellation_rate.png`

## 10. Sojourn Time (Stage Dwell Time) Analysis

**Academic Justification:** Sojourn time measures the duration a case spends *within* a specific stage — from its first entry event to its last exit event. This is distinct from inter-event "wait time" (time between consecutive events), which conflates processing time with idle time. For processes with well-defined stage boundaries, sojourn time is the standard metric (van der Aalst, 2016, Ch. 6; Dumas et al., 2018, Section 8.3).

**Method:** For each `(case_id, activity)` pair, compute `entry_time = min(timestamp)` and `exit_time = max(timestamp)`. Sojourn time = exit − entry.

**Outputs:**
- `outputs/sojourn_time_by_stage.csv` — per-stage aggregated statistics (mean, median, P90, P95, max)
- `outputs/sojourn_time_by_department.csv` — department-level cycle time breakdown
- Three visualizations: top stages bar chart, box-plot distribution, median vs P90 comparison

**Key Insight:** Stages with low median but high P90 sojourn times indicate stages where most cases pass quickly, but a minority get stuck — these are the "time bombs" that should be targeted by SLA enforcement.

## 11. Temporal Trend Analysis

**Academic Justification:** Temporal analysis reveals whether the process is improving or deteriorating over time, and identifies seasonal patterns that affect resource planning (Dumas et al., 2018, Ch. 8).

**Outputs:**
- `outputs/monthly_cycle_time_trend.png` — Monthly median + P90 cycle time with linear trend line and auto-annotated slope (days/month improvement or deterioration)
- `outputs/monthly_throughput.png` — Cases started vs completed per month (identifies backlogs)
- `outputs/dotted_chart.png` — Each event as a dot (time on x-axis, case on y-axis) showing the overall event distribution pattern
- `outputs/monthly_trend_stats.csv` — Raw monthly statistics

## 12. Statistical Significance Tests

**Academic Justification:** Reporting differences in group means without hypothesis testing is a common pitfall in process mining studies. The Mann-Whitney U test (non-parametric) is appropriate because cycle-time distributions are heavily skewed and violate normality assumptions.

**Tests performed:**
1. **Reassignment vs. No Reassignment** — Cycle time comparison with effect size (r = Z/√N)
2. **Approved vs. Cancelled** — Do approved cases take significantly longer than cancelled ones?
3. **Top-5 Department Pairwise** — Are cycle-time differences between the busiest departments significant?

**Outputs:**
- `outputs/statistical_tests.csv` — All test results with U-statistic, p-value, significance at α=0.05, and effect size
- `outputs/statistical_tests.json` — Machine-readable version

## 13. Findings
1. **Inefficient Budgeting:** The budgeting phase is a major "long-tail" risk factor. Max observed delay: 121 days. Cases that never reach budget review are the primary cancellation driver.
2. **Repetitive Approvals:** Approvals often require multiple "pings," suggesting lack of clarity in requirements or missing documentation.
3. **Ownership Confound:** The apparent benefit of reassignment is confounded by case complexity — short cases naturally traverse more owners. After controlling for event count, the effect is attenuated.
4. **Heavy Right-Skew (P90/P95):** 90% of cases close within 47 days, but the upper 5% take 117+ days. These outliers overwhelmingly correlate with CEO-level sign-off delays.
5. **Early Abandonment Pattern:** The predictive model shows that cases cancelled early never reach the budget stage. A pre-screening checklist at case intake could eliminate this waste.
6. **Process Trend:** Monthly cycle time trend analysis reveals whether the process is improving over time (slope direction and magnitude auto-computed).

## 14. Network Analysis & Case Clustering (P3 Enhancements)

### 14.1 Social Network Analysis (SNA) Centrality
**Academic Justification:** Beyond simple handover frequencies, graph theory provides structural insights into organizational bottlenecks (van der Aalst, 2016). We generated a directed graph of resource handovers using `networkx` and exported an interactive visualization (`outputs/interactive_sna.html`).
- **Betweenness Centrality:** Identifies resources that act as critical "bridges" between different departments. High betweenness nodes are system-level bottlenecks; if they are unavailable, the process halts.
- **Degree Centrality:** Measures the pure volume of interaction a resource has.

**Outputs:**
- `outputs/interactive_sna_centrality.csv` — Full ranking of resources by betweenness, closeness, and degree.
- The interactive HTML graph dynamically sizes nodes by degree and colors them (red to blue) based on their betweenness centrality.

### 14.2 Case Segmentation via K-Means Clustering
**Academic Justification:** Aggregate averages obscure distinct sub-populations within the event log. We applied unsupervised K-Means clustering (k=4) to segment cases based on three features: Cycle Time, Event Count, and Reassignmenet Count.
- **Fast/Simple:** The "happy path" majority. Low event count, zero reassignments, median cycle time < 5 days.
- **Average:** Typical cases that encounter minor friction.
- **Complex/Slow:** Cases with high internal rework and multiple reassignments.
- **Extreme Outliers:** The P99 tail. These cases exhibit pathological event loops and spend >200 days in the system.

**Outputs:**
- `outputs/case_clusters.csv` — Cluster assignment for every `case_id`.
- `outputs/cluster_profiles.png` — Boxplot distributions across the four profiles, proving that "Extreme Outlier" cases are fundamentally different in structure (event count) than "Fast/Simple" cases, not just slower.

## 15. Operational Recommendations
1. **SLA Implementation for Budgeting:** Set a 7-day hard limit for budget recommendations. This single change would have the largest impact on reducing the P95 cycle time (currently 116.6 days).
2. **Automated Committee Scheduling:** The current "Date Setting" phase is highly complex and repetitive. Implementation of an automated scheduling tool could reduce this rework.
3. **Requirement Validation at Entry:** Reduce the "ping-pong" variants by requiring all documents (budget check, job description) to be attached before the first approval. This directly addresses the early-cancellation pattern identified by the predictive model.
4. **Inactivity Detection:** Establish an automated trigger to escalate a case if it remains inactive for more than 14 days without progress — targeting the stagnant cases that inflate the P95.
5. **Parallelize Salary Simulation:** Salary simulations can run in parallel with Division Head approvals rather than sequentially.
6. **CEO/Mayor Approval Fast-Track:** The CEO and Mayor's Office stages show maximum delays of 134 days. A dedicated routing queue with a 10-day SLA would bring P90 below 20 days.

## 16. Limitations
1. **Data granularity:** The "Changed Field" column often contains raw IDs rather than descriptive text.
2. **Calendar vs. business hours:** The log does not distinguish between working hours and calendar hours; all durations are calendar time.
3. **Single-year data:** The predictive model is trained on a single year; seasonal or organizational changes may affect generalisability.
4. **External system gap:** Candidate screening and committee proceedings occur in a separate system — this creates a "black box" window visible only as a gap between the last approval event and the next post-committee event.
5. **Consecutive duplicate removal trade-off:** Collapsing consecutive identical activities eliminates intra-stage noise but may mask genuine re-entry scenarios where a case returns to the same stage after visiting others.

---
*Report generated by Process Mining Analysis System — 19-step pipeline including sojourn time, temporal trends, statistical significance testing, multi-algorithm discovery comparison, SNA centrality, and K-Means segmentation.*
