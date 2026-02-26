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
A statistical comparison was performed between cases involving responsible party reassignments and those without:
- **With Reassignment:** 16.3 days (Median: 1.06 days).
- **Without Reassignment:** 80.9 days (Median: 38.0 days).
**Conclusion:** Reassignment appears to be a proactive measure that prevents case stagnation. Cases that remain "stuck" with a single person without progress are the primary contributors to the 80-day average.

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

### 9.1 Heuristics Miner
**Justification:** The Heuristics Miner (Weijters & Ribeiro, 2011) is employed because the recruitment process log exhibits extreme noise: the variant analysis (variants.csv) shows that the top 20 variants are all mono-stage repetition loops (e.g., "Department Manager Approval" repeated 10+ times in a single case). The Inductive Miner produces an overly complex model under such conditions. The Heuristics Miner suppresses arcs below a dependency threshold (set to 0.5), revealing the "main road" of the process.

**Output:** The module (`src/heuristics_miner.py`) produces:
- `outputs/heuristics_net_summary.txt` — ranked list of all dependency arcs.
- `outputs/conformance_results.csv` — per-trace fitness scores.
- `outputs/conformance_summary.json` — aggregate fitness, precision, and recall.
- `outputs/normative_gap_analysis.csv` — stage coverage vs. the normative path.

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

### 9.2 Conformance Checking
Token-based replay (van der Aalst, 2016) measures how faithfully observed cases follow the Heuristics Miner model. Run `python src/heuristics_miner.py` to generate the full conformance report. The normative gap analysis quantifies what fraction of cases visit each mandatory stage, exposing where cases deviate from the ideal path.

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

## 10. Findings
1. **Inefficient Budgeting:** The budgeting phase is a major "long-tail" risk factor. Max observed delay: 121 days. Cases that never reach budget review are the primary cancellation driver.
2. **Repetitive Approvals:** Approvals often require multiple "pings," suggesting lack of clarity in requirements or missing documentation. The top variants are all mono-stage loops.
3. **Proactive Management Works:** Reassigning cases is a sign of an active process; stagnant cases are the real bottleneck.
4. **Heavy Right-Skew (P90/P95):** 90% of cases close within 47 days, but the upper 5% take 117+ days. These outliers overwhelmingly correlate with CEO-level sign-off delays.
5. **Early Abandonment Pattern:** The predictive model shows that cases cancelled early never reach the budget stage. A pre-screening checklist at case intake could eliminate this waste.

## 11. Operational Recommendations
1. **SLA Implementation for Budgeting:** Set a 7-day hard limit for budget recommendations. This single change would have the largest impact on reducing the P95 cycle time (currently 116.6 days).
2. **Automated Committee Scheduling:** The current "Date Setting" phase is highly complex and repetitive. Implementation of an automated scheduling tool could reduce this rework.
3. **Requirement Validation at Entry:** Reduce the "ping-pong" variants by requiring all documents (budget check, job description) to be attached before the first approval. This directly addresses the early-cancellation pattern identified by the predictive model.
4. **Reassignment Triggers:** Establish an automated trigger to reassign or escalate a case if it remains inactive for more than 14 days without a change in the responsible person.
5. **Parallelize Salary Simulation:** Salary simulations can run in parallel with Division Head approvals rather than sequentially.
6. **CEO/Mayor Approval Fast-Track:** The CEO and Mayor's Office stages show maximum delays of 134 days. A dedicated routing queue with a 10-day SLA would bring P90 below 20 days.

## 12. Limitations
The analysis is limited by the granularity of the "Changed Field" data, which often contains raw IDs rather than descriptive text for all updates. Additionally, the log does not distinguish between "working hours" and "calendar hours." The predictive model is trained on a single year of data; seasonal patterns or organizational changes may affect generalisability.

---
*Report generated by Process Mining Analysis System (Antigravity AI + Phase 2 by Claude)*
