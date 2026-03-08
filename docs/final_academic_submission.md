# Process Mining the Haifa Municipality Recruitment Process

**Final Academic Submission**

---

## 1. Executive Summary

This study applies process mining techniques to the Haifa Municipality's job-staffing workflow (*Teken* ג€” ׳׳™׳•׳© ׳׳©׳¨׳”) with the objective of identifying delay sources, mapping process variants, and formulating concrete operational recommendations to improve recruitment cycle times.

**Dataset:** Two event logs totalling 1,126,436 raw events across 11,922 unique cases, covering a full 12-month period (2024). After preprocessing ג€” including deduplication, consecutive duplicate removal, and schema normalisation ג€” the cleaned log retained 22,299 events across 42 unique activities. Of the 11,922 cases, 804 reached a definitive outcome (approved, cancelled, or rejected); the remaining 11,118 cases comprise 11,097 single-event submissions (including one still in an active approval round) and 21 multi-event cases still in progress or draft status.

**Key Findings:**

- Among the 804 completed cases, the mean cycle time is 98.1 days and the median is 62.8 days. Approved cases average 126.1 days while cancelled cases average 66.5 days, confirming that cases surviving the full pipeline accumulate more processing time in post-approval stages.
- The stages with the highest mean inter-event wait times are Contract Signing (36.6 days), Internal Tender Committee Decision (33.5 days), and Committee Date Approval (32.7 days). Budget Recommendation and CEO Decision exhibit a distinctive right-skewed profile: their medians are near zero but their maximums exceed 340 days.
- The slowest variant path (mean 317 days) involves the full external-tender track following CEO approval (Tender Specification ג†’ Union Notification ג†’ Publication ג†’ Committee Decision).
- In the aggregate analysis, departmental workload showed no meaningful linear association with cycle time (Pearson r ג‰ˆ 0.0), suggesting that overall volume alone is unlikely to be the main driver of delays, although localised congestion effects cannot be ruled out.
- A Random Forest predictive model (AUC = 0.940) identifies the number of unique stages visited as the strongest predictor of case outcome. Cases cancelled early never reach the Budget stage, indicating early abandonment.
- Process fitness via token-based replay on the Inductive Miner model is 100% (all 523 distinct trace variants conform to the discovered model).

**Operational Recommendations:** (1) Pilot a 7-day SLA on Budget Recommendation; (2) automate committee scheduling; (3) introduce a mandatory intake checklist to prevent early-stage abandonment; (4) implement a 14-day inactivity auto-escalation trigger; (5) parallelise salary simulation with Division Head approval; (6) pilot a 10-day escalation threshold for CEO/Mayor decisions.

---

## 2. Introduction

### 2.1 Process Description

The Haifa Municipality manages employee recruitment through a rule-based workflow system. Each recruitment cycle is initiated when a department submits a Position Standard request (*Teken*) ג€” either for an existing budgeted position (96.6% of cases) or a new position (3.4%). The process proceeds through five logical phases:

**Phase 1 ג€” Hierarchical Approval.** The request is routed sequentially through the Department Manager, Division Head (*Agaf*), and Head of Administration (HR Director). The system may skip a level if no relevant manager exists.

**Phase 2 ג€” HR Control and Recruitment Strategy.** The HR department reviews the staffing situation in the requesting unit. The Recruitment Manager then recommends the hiring method: Internal Tender (*׳׳›׳¨׳– ׳₪׳ ׳™׳׳™*), External Tender (*׳׳›׳¨׳– ׳—׳™׳¦׳•׳ ׳™*), or ג€” for junior positions ג€” a Help-Wanted Advertisement (*׳׳•׳“׳¢׳× ׳“׳¨׳•׳©׳™׳*) without a formal tender.

**Phase 3 ג€” Financial and Executive Oversight.** Three parallel workstreams operate concurrently: (a) Budget Department and Treasurer approval, (b) Service Conditions Department salary verification, and (c) Payroll Department salary simulation. This phase culminates in the CEO Decision ג€” the final executive gate.

**Phase 4 ג€” Implementation.** Following CEO approval, the Standards Department drafts the job description jointly with the requesting manager. The Labour Union (*׳•׳¢׳“ ׳¢׳•׳‘׳“׳™׳*) approves the tender wording, and the Recruitment Department publishes the tender.

**Phase 5 ג€” Selection.** Candidate screening occurs in a separate system. A committee date is set, the committee convenes, and a hiring decision is rendered. Possible outcomes include candidate selection, return to a previous stage, or process cancellation. Certain time windows within this phase (e.g., the application submission period) are mandated by law and cannot be compressed.

### 2.2 Study Objectives

This study addresses six business questions posed by the Haifa Municipality:

1. Where do delays occur in the process ג€” by stage, role, user, department, and outcome?
2. What are the main process variants, and which activity sequences produce the longest delays?
3. What is the relationship between departmental workload volume and process cycle time?
4. Do changes in stage ownership (responsible-party reassignment) correlate with delays?
5. Can internal sub-processes within individual stages be characterised, and do they relate to delays?
6. What concrete operational suggestions can reduce process duration?

**Data Scope:** Two Excel log files covering 12 months (2024), comprising 1,126,436 raw events and 11,922 unique cases. After full preprocessing (including consecutive duplicate removal), 22,299 events were retained for analysis.

---

## 3. Data Preprocessing

### 3.1 Source Data and Merging

Two Excel files were provided by the municipality. Part 1 contained 495,840 rows (5,097 cases) and Part 2 contained 630,596 rows (7,501 cases). These were concatenated into a single DataFrame of 1,126,436 rows prior to cleaning. Since the two files share 676 overlapping cases (appearing in both exports), the merged log contains 11,922 unique cases rather than the arithmetic sum of 12,598. Each row represents a single system event, with 17 fields including case identifier, activity (stage name in Hebrew), timestamp, performer, responsible party, requesting department, and changed field.

### 3.2 Cleaning Pipeline

The following preprocessing actions were applied sequentially. Each action, its purpose, and its impact on the event log are detailed below.

**Step 1 ג€” Column Renaming.** All 17 Hebrew column headers were mapped to an English schema (e.g., *׳׳–׳”׳” ׳‘׳§׳©׳”* ג†’ `case_id`, *׳×׳—׳ ׳”* ג†’ `activity`). This standardisation enables processing by pm4py and ensures reproducibility across environments.

**Step 2 ג€” Null Value Normalisation.** String literals "NULL" and em-dash characters ("ג€”") were replaced with proper NaN values. This corrected approximately 12% of entries in the `request_status` and `stage_end_date` fields that would otherwise be treated as valid categorical values.

**Step 3 ג€” Timestamp Parsing.** The `timestamp` and `target_date` columns were parsed from string to datetime format. This is the foundational step enabling all time-based analyses ג€” cycle time, wait time, sojourn time, and temporal trend computations.

**Step 4 ג€” Chronological Sorting.** Events were sorted by `case_id` and `timestamp` to enforce strict chronological ordering within each case. This is a prerequisite for sequence-based variant analysis, Directly-Follows Graph construction, and conformance checking.

**Step 5 ג€” Duplicate Removal.** Exact duplicate rows (matching on `{case_id, timestamp, activity, event_type, changed_field}`) were removed. This step eliminated **85,991 rows (7.6% of the raw log)**, reducing the dataset from 1,126,436 to 1,040,445 events. These duplicates arose from redundant system-update events recorded when multiple fields were modified simultaneously.

**Step 6 ג€” Missing Activity Imputation.** Events with null activity labels were assigned the value "Unknown Stage" to prevent downstream errors in process model construction. Every event in the cleaned log has a valid activity label.

**Step 7 ג€” Consecutive Duplicate Activity Removal.** When a user updates multiple fields within a single stage (e.g., five separate field edits in "Division Head Approval"), the system generates five rows sharing the same activity name. Only the first event in each consecutive run was retained, eliminating false self-loops and mono-stage "variants" that would distort variant analysis. This step removed **1,018,146 rows**, reducing the log from 1,040,445 to **22,299 events**. This dramatic reduction reflects the administrative nature of the source system, where each field-level edit generates a separate event row. This cleaning approach follows recommended practice for noisy administrative logs (van der Aalst, 2016, Ch. 7). The justification is that these duplicates represent instrumentation noise (multiple field edits within a single logical stage visit) rather than genuine repeated work; the original stage transition structure is preserved. Evidence supporting this interpretation: 99.7% of consecutive duplicates share the same `event_type` ("Update") and differ only in the `changed_field` column, confirming they are sub-events within a single stage visit rather than meaningful loop behaviour.

**[INSERT IMAGE: outputs/plots/preprocessing/01_deduplication_impact.png ג€” Caption: Figure 1. Deduplication impact showing the multi-step reduction from 1,126,436 raw events to 22,299 cleaned events.]**

### 3.3 Preprocessing Quality Assessment

Six diagnostic charts were generated to validate the preprocessing pipeline:

**[INSERT IMAGE: outputs/plots/preprocessing/02_status_distribution.png ג€” Caption: Figure 2. Case outcome distribution for the 826 status-labelled cases (of 11,922 total): Approved (422), Cancelled (360), Rejected (22), In-Progress/Other (22). The remaining 11,096 cases carry no recorded outcome status.]**

**[INSERT IMAGE: outputs/plots/preprocessing/03_events_per_case.png ג€” Caption: Figure 3. Events-per-case distribution computed on the intermediate log after exact-duplicate removal but before consecutive duplicate removal (Step 7). At this stage the log contained 1,040,445 events across 11,922 cases (median = 51, P95 = 301 events/case). After Step 7, the cleaned log retains 22,299 events and 93.9% of cases have exactly one event (median = 1).]**

**[INSERT IMAGE: outputs/plots/preprocessing/04_log_timeline.png ג€” Caption: Figure 4. Monthly event volume across the 12-month log period, confirming full calendar-year coverage with no data gaps.]**

**[INSERT IMAGE: outputs/plots/preprocessing/05_activity_frequency.png ג€” Caption: Figure 5. Top 20 stages by event count, validating the Hebrew-to-English stage name mapping.]**

**[INSERT IMAGE: outputs/plots/preprocessing/06_missing_values.png ג€” Caption: Figure 6. Missing-value analysis by column. The `stage_end_date` field is >90% null (excluded from analysis); `request_status` is ~47% null (reflecting in-progress cases).]**

### 3.4 Modelling Decisions

Three key modelling choices were made prior to analysis:

**Activity Definition.** The *activity* attribute was defined as the Hebrew stage name (the `activity` column). An alternative approach ג€” concatenating stage name with event type (e.g., "Division Head Approval ג€” Update") ג€” was evaluated and rejected because it introduces noise without adding business insight. Process delays occur *between* stage transitions, not within event-type sub-steps of a single stage.

**Case Identifier.** The `request_id` field was used as the case identifier. It maps 1:1 to the `case_id` column; both refer to the same recruitment request record.

**Encoding.** All CSV input/output operations use `utf-8-sig` encoding to preserve Hebrew characters across Windows environments.

### 3.5 Data Scope and Reporting Note

The cleaned event log contains 22,299 events across 11,922 unique cases and 42 distinct activities. However, the case population is highly heterogeneous, and different analyses in this report use different subsets depending on the question being addressed. To prevent confusion, the key populations are defined here:

| Population | n | Definition | Used For |
|------------|---|------------|----------|
| All cases | 11,922 | Every unique case_id in the cleaned log | Conformance checking, process discovery, variant extraction |
| Single-event cases | 11,195 (93.9%) | Cases with exactly one event ג€” initial submissions that did not progress | Included in process discovery; excluded from cycle-time and outcome analyses |
| Multi-event cases | 727 (6.1%) | Cases with two or more events ג€” those that underwent meaningful processing | Core population for cycle-time and bottleneck analysis |
| Completed cases | 804 | Cases with a definitive final status: Approved (422), Cancelled (360), or Rejected (22) | Outcome analysis, predictive modelling |
| In-progress / other | 22 | Cases still in an active approval round (21) or in draft status (1) | Excluded from outcome analysis |

**Subset relationships:** The 11,922 total cases partition into 804 completed + 11,118 non-completed. The 11,118 non-completed cases comprise 11,097 single-event cases (11,096 with no recorded outcome plus one still in an active approval round) and 21 multi-event cases still in progress or draft status. Among the 804 completed cases, 98 are single-event (e.g., immediate cancellation without any processing) and 706 are multi-event. When cycle-time statistics are reported, they refer to the 804 completed cases unless otherwise noted.

### 3.6 Time Metric Definitions

Three distinct time metrics are used throughout this report, and care must be taken not to conflate them. All times are measured in **calendar days** (not business days):

**Case cycle time** is defined as the elapsed time from the first event to the last event within a case. For the 804 completed cases, the mean cycle time is 98.1 days and the median is 62.8 days. The overall mean across all 11,922 cases (6.9 days) is dominated by single-event cases with zero duration and is therefore not a meaningful summary of process performance.

**Inter-event wait time** is the elapsed time between two consecutive events within a case. This measures the delay between successive stage transitions and is the primary bottleneck metric used in Section 5.1.

**Sojourn time** (stage dwell time) is the elapsed time from a case's first entry into a stage to its last exit from that stage (van der Aalst, 2016, Ch. 6). This captures the total time a case spends within a single stage, which may include multiple internal sub-events. Sojourn time and inter-event wait time can differ substantially for stages with high internal complexity.

---

## 4. Main Paths and Variants (׳”׳×׳”׳׳™׳ ג€” ׳ ׳×׳™׳‘׳™׳ ׳¢׳™׳§׳¨׳™׳™׳)

### 4.1 Case Characterisation

Prior to variant analysis, cases with definitive outcomes (n = 804; see Section 3.5 for population definitions) were segmented along three dimensions.

**By Position Standard (*Teken*):**

| Type | Cases | Percentage |
|------|-------|------------|
| Existing position (*׳×׳§׳ ׳§׳™׳™׳*) | 776 | 96.5% |
| New position (*׳×׳§׳ ׳—׳“׳©*) | 28 | 3.5% |

The overwhelming majority of requests concern existing, budgeted positions. This confirms that the process functions primarily as a bureaucratic approval chain rather than a resource-allocation decision mechanism.

**By Outcome (804 completed cases):**

| Status | Cases | Percentage | Mean Cycle Time (days) |
|--------|-------|------------|----------------------|
| Approved (*׳׳•׳©׳¨*) | 422 | 52.5% | 126.1 |
| Cancelled (*׳‘׳•׳˜׳*) | 360 | 44.8% | 66.5 |
| Rejected (*׳׳ ׳׳•׳©׳¨*) | 22 | 2.7% | 77.5 |

Note: These 804 cases represent the subset of the 11,922 total cases that reached a definitive final status. The remaining 11,118 cases comprise 11,097 single-event submissions (including one still in an active approval round) and 21 multi-event cases still in progress or draft status (see Section 3.5 for the full population breakdown). The near-parity between approved and cancelled cases (52.5% vs. 44.8%) among completed cases is consistent with substantial inefficiency in the intake process.

**By Recruitment Method (inferred from stages visited):** Three main tracks emerge after CEO approval: (a) External + Internal Tender ג€” the full formal tender procedure and the longest path; (b) Help-Wanted Advertisement ג€” a lighter track for junior positions that bypasses formal tender requirements; and (c) Direct Appointment ג€” committee decision without a public tender.

### 4.2 Process Discovery and the Main Process Path

The Heuristics Miner algorithm (Weijters & Ribeiro, 2011) was applied with a dependency threshold of 0.5 and a 10% DFG edge frequency filter to extract the dominant process path. The filtered Directly-Follows Graph (DFG) retained **21 of 260 raw edges** ג€” the 239 discarded edges represent rare exception paths or system-update artefacts.

The discovered main path is:

> Staffing Recommendation ג†’ Department Manager Approval ג†’ Division Head Approval ג†’ HR Director Approval ג†’ **[PARALLEL]** Budget Recommendation + Salary Simulation + Service Conditions ג†’ CEO Decision ג†’ Tender Specification + Publication ג†’ Committee Date Setting ג†’ Committee Decision

**[INSERT IMAGE: outputs/plots/dfg_filtered.png ג€” Caption: Figure 7. Filtered Directly-Follows Graph showing the main process path (21 edges, ג‰¥10% of maximum frequency). Node labels are Hebrew stage names.]**

**[INSERT IMAGE: outputs/dfg_frequency.png ג€” Caption: Figure 8. Full DFG with frequency-based edge weights showing all stage transitions.]**

### 4.3 Variant Analysis

The raw variant log reveals that the majority of statistically frequent "variants" are mono-stage repetition loops ג€” the same stage name repeated 10ג€“14 times within a single case. This is a data artefact rather than genuine rework: each field-level "Update" event within a stage creates a new event row. These repetition loops do not reflect process rework; they reflect micro-updates within a single logical step. The consecutive duplicate removal step (Section 3.2, Step 7) mitigates this effect, but some residual noise persists in the variant frequency distribution.

**[INSERT IMAGE: outputs/plots/advanced/variant_treemap.png ג€” Caption: Figure 9. Variant treemap showing the distribution of process paths. The largest segments represent mono-stage loops (data artefacts); genuine multi-stage variants are visible in the smaller segments.]**

**[INSERT IMAGE: outputs/variant_frequency_top15.png ג€” Caption: Figure 10. Top 15 variants by frequency.]**

### 4.4 Sequences with the Longest Delays

To identify the activity sequences most strongly associated with delays, the first five distinct stages per case were extracted to construct sequence paths. The five slowest paths are:

| Rank | Mean Cycle Time | Cases | Path (first 5 distinct stages) |
|------|----------------|-------|-------------------------------|
| 1 | **317 days** | 3 | Tender Wording ג†’ Tender Spec ג†’ Union Notification ג†’ ג€¦ |
| 2 | **298 days** | 3 | Salary Simulation ג†’ Budget Rec ג†’ Treasurer Decision ג†’ CEO ג†’ ג€¦ |
| 3 | **298 days** | 15 | Budget Rec ג†’ Treasurer Decision ג†’ CEO ג†’ Tender Spec ג†’ ג€¦ |
| 4 | **291 days** | 3 | Internal Tender ג†’ External Tender Publication ג†’ Committee Date ג†’ ג€¦ |
| 5 | **271 days** | 21 | CEO Decision ג†’ Tender Spec ג†’ Tender Wording ג†’ Committee Date ג†’ ג€¦ |

All five slowest paths include the post-CEO tender-publication and committee stages. The bottleneck is not located in the initial approval chain ג€” it resides in the **tender-to-committee corridor** that follows CEO approval. Paths that reach the full external-tender track average 270ג€“317 days, compared to the overall completed-case mean of 98.1 days (Section 3.6). These outlier paths represent approximately 2ג€“3ֳ— the typical completed-case duration.

---

## 5. Analyses Performed (׳ ׳™׳×׳•׳—׳™׳ ׳©׳‘׳•׳¦׳¢׳•)

This section presents the analyses conducted in direct response to the six business questions posed by the municipality.

### 5.1 Business Question 1: Where Do Delays Occur?

**Goal:** Identify bottleneck locations by stage, role type, specific user, requesting department, and process outcome.

**Methodology:** For each case, inter-event wait times were computed between consecutive activities. These were aggregated by stage, role, performer, department, and outcome status. Sojourn time (the duration a case spends within a single stage from first entry to last exit) was computed as a complementary metric (van der Aalst, 2016, Ch. 6).

#### 5.1.1 Bottlenecks by Stage

The bottleneck analysis reveals that the stages with the highest *mean* wait times are concentrated in the post-approval and committee phases:

| Stage | Mean Wait (days) | Median (days) | Max (days) |
|-------|-----------------|---------------|------------|
| Contract Signed (*׳—׳•׳–׳” ׳ ׳—׳×׳*) | 36.6 | 23.4 | 125.0 |
| Internal Tender Committee Decision | 33.5 | 27.0 | 259.3 |
| Committee Date Approval | 32.7 | 22.3 | 288.5 |
| External+Internal Committee Decision | 31.6 | 28.2 | 130.2 |
| Non-Tender Committee Decision | 21.2 | 18.2 | 152.1 |
| Budget Recommendation | 16.2 | 2.9 | 344.2 |
| CEO Decision | 11.0 | 0.0 | 341.0 |

The Budget Recommendation and CEO Decision stages exhibit a distinctive pattern: their medians are near zero (most cases pass quickly), but their maximums exceed 340 days. This right-skewed profile identifies them as "time bombs" ג€” stages that are fast for the majority but catastrophically slow for a minority of cases.

**[INSERT IMAGE: outputs/bottleneck_top10_mean_wait.png - Caption: Figure 11. Top 10 stages by mean wait time (days).]**

**[INSERT IMAGE: outputs/bottleneck_delay_contribution_pareto.png — Caption: Figure 11b. Delay-contribution Pareto chart showing which stages account for the largest cumulative share of total observed waiting time.]**

**[INSERT IMAGE: outputs/bottleneck_wait_distribution_boxplot.png ג€” Caption: Figure 12. Box-plot distribution of wait times across major stages, showing right-skewed distributions with extreme outliers at CEO Decision and Budget Recommendation.]**

**[INSERT IMAGE: outputs/sojourn_top10_mean.png ג€” Caption: Figure 13. Top 10 stages by mean sojourn time (dwell time within stage).]**

**[INSERT IMAGE: outputs/sojourn_median_vs_p90.png ג€” Caption: Figure 14. Median vs. P90 sojourn time comparison by stage. Stages with low median but high P90 are the "time bomb" stages requiring SLA enforcement.]**

**[INSERT IMAGE: outputs/sojourn_time_distribution.png ג€” Caption: Figure 15. Overall sojourn-time distribution across all stages.]**

#### 5.1.2 Bottlenecks by Role Type

The `stage_responsible` field identifies the organisational role accountable for each stage. Analysis of mean stage duration by role reveals:

- **Mayor's Staff (*׳¡׳’׳ ׳¨׳׳© ׳”׳¢׳™׳¨*):** The longest average stage duration, responsible for the Mayor's Office Decision stage.
- **HR Division Head (*׳׳ ׳”׳ ׳׳’׳£ ׳׳©׳׳‘׳™ ׳׳ ׳•׳©*):** Second-highest wait time, accountable for budget and staffing recommendations.
- **Treasury (*׳’׳–׳‘׳¨׳•׳×*):** Financial approval stages exhibit high variance ג€” fast for routine cases but with extreme outliers for complex budget decisions.

**[INSERT IMAGE: outputs/plots/advanced/stage_bottleneck_heatmap.png — Caption: Figure 16. Stage-by-role bottleneck heatmap showing mean inter-event wait times. Darker cells indicate role-specific delay concentration within high-wait stages.]**

#### 5.1.3 Bottlenecks by Specific Users

Analysis of the `performer` field (numeric user codes) reveals that a small group of 5ג€“7 users ג€” primarily in the Mayor's Office and Budget Department ג€” are responsible for the majority of P95+ delays. These individuals handle a disproportionate share of complex cases requiring executive sign-off, creating single-point-of-failure risk.

#### 5.1.4 Bottlenecks by Requesting Department

Departmental cycle-time variance was analysed using violin plots. High-variance departments (wide violin distributions) indicate inconsistent processing ג€” some cases complete rapidly while others stall for months. Low-variance departments have standardised intake procedures that may serve as best-practice templates. Departments with the highest cancellation rates may reflect incomplete or low-readiness submissions that are abandoned before progressing beyond the initial approval stages.

**[INSERT IMAGE: outputs/plots/advanced/dept_cycle_time_violin.png ג€” Caption: Figure 17. Violin plots of cycle time by requesting department. Wide distributions indicate high processing-time inconsistency.]**

**[INSERT IMAGE: outputs/plots/dept_cancellation_rate.png ג€” Caption: Figure 18. Cancellation rate by requesting department.]**

#### 5.1.5 Bottlenecks by Process Outcome

Cycle times were compared across the 804 cases with definitive outcomes (see Section 3.5):

| Outcome | Cases | Mean Cycle Time (days) | Median (days) |
|---------|-------|----------------------|---------------|
| Approved (*׳׳•׳©׳¨*) | 422 | 126.1 | 112.0 |
| Cancelled (*׳‘׳•׳˜׳*) | 360 | 66.5 | 23.4 |
| Rejected (*׳׳ ׳׳•׳©׳¨*) | 22 | 77.5 | 91.6 |

Approved cases take substantially longer than cancelled or rejected ones (mean 126.1 vs. 66.5 days). This is consistent with the interpretation that delay resides in the post-CEO implementation stages (tender publication, committee scheduling) ג€” cases that survive the full pipeline accumulate more processing time in later stages, while cancelled cases exit early before reaching these stages.

**[INSERT IMAGE: outputs/cycle_time_by_request_status.png ג€” Caption: Figure 19. Cycle time distribution by process outcome.]**

#### 5.1.6 Cycle Time Distribution

The cycle-time statistics for the 804 completed cases underscore the severity of the right-skew:

| Metric | Value |
|--------|-------|
| Mean | 98.1 days |
| Median (P50) | 62.8 days |
| P90 | 240.0 days |
| P95 | 298.9 days |
| P99 | 356.3 days |

The upper 10% of completed cases require over 240 days (eight months), while the upper 5% approach a full calendar year. These outlier cases are predominantly associated with the post-CEO tender-to-committee corridor and executive-level sign-off delays.

**[INSERT IMAGE: outputs/case_cycle_time_distribution.png ג€” Caption: Figure 20. Overall case cycle-time distribution showing the heavily right-skewed profile.]**

#### 5.1.7 Statistical Significance

Mann-Whitney U tests (non-parametric, appropriate given the heavily skewed distributions) were applied to validate key group comparisons:

| Comparison | nג‚ | nג‚‚ | Medianג‚ | Medianג‚‚ | p-value | Significant (־±=0.05) | Effect Size (r) |
|------------|----|----|---------|---------|---------|----------------------|-----------------|
| Approved vs. Cancelled | 444 | 360 | 109.2 | 23.4 | <0.001 | Yes | 0.34 |
| Top-5 Department Pairwise | ג€” | ג€” | ג€” | ג€” | >0.05 | No | <0.11 |

The cycle-time difference between approved and cancelled cases is statistically significant with a medium effect size. Pairwise comparisons among the top-5 departments show no statistically significant differences, indicating that no robust department-level effect was detected in the top-5 pairwise comparisons tested. The reassignment significance result is discussed in Section 5.4, where the confounding role of case complexity is addressed directly.

**Business Answer:** Delays are concentrated in the post-approval tender-to-committee corridor (Contract Signing, Committee Decisions, Committee Date Approval ג€” mean wait 32ג€“37 days) and at executive gates (Budget Recommendation, CEO Decision) that exhibit extreme right-skewed distributions. The Mayor's Office and HR Division Head roles are the primary role-level bottlenecks. No robust department-level effect on cycle time was detected in the top-5 pairwise comparisons tested.

---

### 5.2 Business Question 2: What Are the Main Variants and Delay Sequences?

**Goal:** Map the principal process variants and identify which activity sequences produce the longest delays.

**Methodology:** Three process discovery algorithms were applied to extract and compare process models. A *variant* in this context is defined as the complete ordered sequence of activities (control-flow variant) observed for a case after consecutive duplicate removal (Section 3.2, Step 7). The dataset contains 523 distinct variants. For presentation purposes, full variants were summarised by extracting the first five distinct stages per case; the slow-path table in Section 4.4 therefore illustrates representative trace prefixes rather than full variants. This truncation trades completeness for readability but may group structurally different full traces under the same summary label.

#### 5.2.1 Multi-Algorithm Process Discovery

Three standard discovery algorithms were applied to the cleaned event log:

| Algorithm | Places | Transitions | Arcs | Trace Fitness | Token Fitness | Fit Traces (%) |
|-----------|--------|-------------|------|---------------|---------------|----------------|
| Inductive Miner | 15 | 59 | 120 | 1.000 | 1.000 | 100.0% |
| Heuristics Miner | 85 | 189 | 390 | 0.950 | 0.976 | 95.0% |
| Alpha Miner | 202 | 42 | 1,346 | 0.000 | 0.262 | 0.0% |

The **Inductive Miner** (Leemans et al., 2014) achieves perfect fitness (100% of traces fit) and produces a sound, block-structured model. It was adopted as the reference model for conformance checking.

The **Heuristics Miner** (Weijters & Ribeiro, 2011), with its ability to suppress low-dependency arcs, produces the most interpretable DFG for process communication. It was used for the main process-path visualisation (Section 4.2).

The **Alpha Miner** (van der Aalst et al., 2004) fails entirely on this dataset (0% trace fitness, 0.26 token fitness). This is expected: Alpha Miner cannot handle noise, short loops, or non-free-choice constructs ג€” all of which are prevalent in this administrative event log. Its inclusion serves as a pedagogical baseline demonstrating why more robust algorithms are required for real-world process mining (Dumas et al., 2018, Ch. 7).

#### 5.2.2 Conformance Checking

A two-layered conformance checking approach was applied:

**Layer 1 ג€” Token-Based Replay.** The Inductive Miner model was used as the reference Petri net. Token-based replay (van der Aalst, 2016) yields a trace fitness of **1.000** and a token fitness of **1.000** ג€” all 523 distinct trace variants in the log fully conform to the discovered model. Perfect fitness indicates full replayability on the discovered model, but not necessarily high model precision. The Inductive Miner's block-structured design guarantees soundness and can accommodate all observed behaviour, which may include noise alongside genuine process behaviour; precision analysis would be needed to quantify this trade-off.

**Layer 2 ג€” Normative Checkpoint Coverage.** Each case was independently checked for the presence of seven critical normative checkpoints (Staffing Recommendation through Mayor's Office Decision). Among the 727 multi-event cases, the six operational checkpoints achieve coverage between 57.5% (Department Manager Approval) and 69.5% (CEO Decision), indicating that roughly 30ג€“40% of multi-event cases skip at least one approval stage ג€” typically because the organisational hierarchy is shorter for certain departments (e.g., no Division Head). The seventh checkpoint (Mayor's Office Decision) has near-zero coverage, confirming that it applies only to exceptional cases. When computed over all 11,922 cases, per-checkpoint coverage drops to 8ג€“10% because 93.9% of cases are single-event submissions that never reach any approval stage.

This dual-layer approach avoids the pitfall of flagging legitimate system-level stage skips (e.g., when no Division Head exists) as conformance violations.

#### 5.2.3 Delay-Producing Sequences

As detailed in Section 4.4, all five slowest variant paths share a common structural feature: they traverse the full post-CEO tender-to-committee corridor. The mean cycle time for paths reaching the external-tender track (270ג€“317 days) is approximately 3ֳ— the overall completed-case mean (98.1 days).

**Business Answer:** The dominant process path follows a linear approval chain, but cases that enter the post-CEO external-tender track experience the longest delays (270ג€“317 days). The Inductive Miner achieves perfect trace fitness (full replayability), though fitness alone does not guarantee the model is a high-precision representation of the true process. The Alpha Miner fails entirely on this dataset, confirming the need for noise-robust algorithms. Variant diversity is moderate, with the top 10 variants covering 5,779 of the observed trace patterns.

**[INSERT IMAGE: outputs/activity_transition_heatmap_top12.png ג€” Caption: Figure 23. Activity transition heatmap showing the most frequent stage-to-stage transitions among the top 12 activities.]**

---

### 5.3 Business Question 3: Workload Volume vs. Cycle Time

**Goal:** Determine whether departmental workload correlates with cycle time.

**Methodology:** Workload is operationalised as the count of distinct cases handled by each department during the 12-month observation period. Pearson correlation was computed between this per-department case count and mean cycle time across the 152 departments represented in the cleaned log.

**Result:** Pearson r ג‰ˆ **0.0** (effectively zero), computed across all 152 departments represented in the cleaned log. There is no statistically significant linear cross-sectional correlation between departmental workload volume and cycle time at the aggregate level. This test captures only linear, contemporaneous association; it does not address lagged effects, nonlinear relationships, or stage-level congestion within departments.

**Interpretation:** In the aggregate analysis, departmental workload shows no meaningful linear association with cycle time. This suggests that overall case volume alone is unlikely to be the primary driver of delays, which appear to be concentrated at specific approval gates (CEO, Budget, Mayor) through which all cases must pass regardless of the originating department's workload. However, this analysis has limitations: it tests only linear association at the department level, and it cannot rule out localised congestion effects at specific bottleneck stages, lagged workload impacts, or nonlinear relationships. The finding is consistent with the hypothesis that approval-stage restructuring may be more effective than increasing departmental throughput capacity, but further investigation (e.g., stage-level workload analysis or regression with department fixed effects) would be needed to confirm this interpretation.

**Business Answer:** At the aggregate department level, workload volume does not appear to explain cycle-time variation. Delays are more plausibly associated with specific approval stages than with departmental case volume.

*Note: The figures below complement the aggregate Pearson test with descriptive weekly workload views and a department-level summary scatter. They do not overturn the near-zero aggregate correlation; rather, they help show whether a small set of departments simultaneously combine high open-case load and long cycle times.*

**[INSERT IMAGE: outputs/workload_heatmap_department_week.png ג€” Caption: Figure 24. Workload heatmap: concurrent open cases by department and calendar week (descriptive).]**

**[INSERT IMAGE: outputs/workload_trend_by_department.png — Caption: Figure 25. Four-week moving-average workload trend for the highest-load departments, highlighting whether weekly congestion is persistent or episodic.]**

**[INSERT IMAGE: outputs/department_workload_vs_cycle_time.png — Caption: Figure 26. Department workload-versus-cycle-time scatter plot. Departments in the upper-right quadrant combine above-median open-case load with above-median average cycle time.]**

---

### 5.4 Business Question 4: Responsible-Party Assignment/Change Signals and Delays

**Goal:** Determine whether changes in stage ownership (reassignment of the responsible party) correlate with process delays.

**Methodology:** Cases were divided into two groups ג€” those involving at least one responsible-party reassignment and those without. Cycle times were compared using Mann-Whitney U tests. Spearman rank correlation (ֿ = 0.444, p < 0.001) between reassignment count and cycle time was computed. To control for the confounding effect of case complexity, cases were bucketed by event-count quartiles for within-quartile analysis.

#### 5.4.1 Simple Comparison (All 11,922 Cases)

| Group | Cases | Mean Cycle Time (days) | Median (days) |
|-------|-------|----------------------|---------------|
| With Reassignment | 5,710 | 14.3 | 0.0 |
| Without Reassignment | 6,212 | 0.03 | 0.0 |

This simple comparison is misleading. The reassignment flag is triggered when a case's `changed_field` contains the responsible-party field ("׳׳—׳¨׳׳™ ׳©׳׳‘") or when the `stage_responsible` value changes between consecutive events. Under this definition, 4,996 of the 5,710 "with reassignment" cases are actually single-event cases whose sole event was a responsible-party field assignment ג€” not a genuine inter-stage handover. Similarly, the "without reassignment" group (6,212) comprises 6,199 single-event cases plus only 13 multi-event cases. Because both groups are dominated by single-event cases with near-zero cycle time, the aggregate comparison is uninformative.

#### 5.4.2 Completed Cases (804 Definitive-Outcome Cases)

| Group | Cases | Mean Cycle Time (days) | Median (days) |
|-------|-------|----------------------|---------------|
| With Reassignment | 693 | 113.5 | 96.7 |
| Without Reassignment | 111 | 1.8 | 0.0 |

Among completed cases, those with reassignment are substantially *slower* (mean 113.5 vs. 1.8 days). However, the 111 "without reassignment" completed cases consist of all 98 single-event completed cases (predominantly immediate cancellations) plus 13 multi-event cases with no recorded responsible-party change ג€” too small a sample for reliable comparison.

#### 5.4.3 Interpretation and Limitations

The Spearman correlation (ֿ = 0.444, p < 0.001) indicates a moderate positive association between reassignment count and cycle time. This is consistent with the expectation that longer cases naturally traverse more stages and therefore involve more handovers. However, the direction of causation cannot be established from this observational data alone: it is equally plausible that reassignments cause delays (coordination overhead) or that longer cases simply accumulate more reassignments as a byproduct of their extended duration. The primary practical insight is that **cases stalling at a single stage without any reassignment** tend to represent either immediate cancellations or dormant cases, suggesting that inactivity detection (auto-escalation after 14 days without progress) may be a more productive intervention than restricting handovers.

**Business Answer:** Reassignment count and cycle time are moderately positively correlated (Spearman ֿ = 0.444), but causation cannot be established from observational data. The association appears to be largely driven by the structural relationship between case complexity (more stages = more handovers = longer duration). The intervention implication is that inactivity detection is more promising than handover restriction.

**[INSERT IMAGE: outputs/responsible_change_cycle_time_boxplot.png ג€” Caption: Figure 27. Cycle time box plots comparing cases with and without responsible-party reassignment.]**

**[INSERT IMAGE: outputs/responsible_change_lift_by_complexity.png — Caption: Figure 28. Median cycle time by event-count quartile, comparing cases with and without responsible-party reassignment to control for case complexity.]**

**[INSERT IMAGE: outputs/responsible_change_count_distribution.png ג€” Caption: Figure 29. Distribution of the number of responsible-party changes per case.]**

---

### 5.5 Business Question 5: Internal Sub-Processes within Stages

**Goal:** Characterise the internal complexity of individual stages and determine whether intra-stage sub-processes contribute to delays.

**Methodology:** Internal complexity was measured as the number of events per stage per case. The `changed_field` column was analysed to identify which specific fields trigger repeated updates (rework loops) within stages. Additionally, parallel-track compliance was audited to assess whether the three concurrent workstreams (Budget, Service Conditions, Payroll) execute simultaneously as designed.

#### 5.5.1 Stage-Level Internal Complexity

Tender Committee Decisions and Committee Date Setting exhibit the highest internal complexity, with over 150 events per case in some instances. This indicates that these "stages" reflect extended negotiation or administrative processes involving many incremental updates rather than single decision points.

**[INSERT IMAGE: outputs/internal_rework_ratio_top10.png ג€” Caption: Figure 30. Top 10 stages by internal rework ratio (events per case within stage).]**

**[INSERT IMAGE: outputs/internal_rework_duration_scatter.png ג€” Caption: Figure 31. Scatter plot of internal rework frequency vs. stage duration, showing the correlation between intra-stage complexity and delay.]**

#### 5.5.2 Changed-Field Analysis

The most frequently modified field across all stages is **'׳¨׳׳× ׳—׳¨׳™׳’׳” ׳׳–׳׳ ׳×׳§׳'** (Standard Time Deviation Level). This field is updated repeatedly when a stage exceeds its target duration, reflecting internal escalation sub-processes triggered by SLA breaches. Other frequently changed fields include salary parameters and budget codes, indicating that financial data re-entry is a significant source of intra-stage complexity.

#### 5.5.3 Parallel-Track Compliance

The process design specifies that three tracks should execute in parallel following the approval hierarchy: (1) Budget/Treasurer approval, (2) Service Conditions salary check, and (3) Payroll salary simulation. Measurement of actual overlap between the Approval track and the Salary track reveals:

- **Concurrency Rate:** **84.97%** ג€” 85% of cases correctly execute these tracks in parallel.
- **Sequential Violations:** 15% of cases wait for approvals to finish before initiating salary checks, adding unnecessary sequential delay.

**Recommendation:** Enforce system-level parallelism by auto-triggering the salary simulation when the Budget Recommendation stage is initiated, rather than relying on manual handoff.

**Business Answer:** Committee-related stages exhibit the highest internal complexity (>150 events per case in extreme instances), indicating that these "stages" function as extended administrative sub-processes rather than single decision points. The most frequently modified field (*Standard Time Deviation Level*) reflects internal SLA-breach escalation sub-processes. Parallel-track compliance is 84.97%, with 15% of cases incurring unnecessary sequential delay.

---

### 5.6 Business Question 6: Operational Suggestions

The six operational recommendations in Section 6 are grounded in four empirically identified improvement levers from Questions 1ג€“5: (1) the extreme right-skew at Budget Recommendation and CEO Decision stages, where medians are near zero but maximums exceed 340 days, motivating SLA-based escalation pilots; (2) the finding that cases stalling without any reassignment tend to be dormant or immediately cancelled (Section 5.4.3), motivating automatic 14-day inactivity escalation; (3) the 15% sequential-violation rate in the parallel salary-simulation track, motivating system-level auto-triggering; and (4) the 44.8% early-abandonment cancellation pattern revealed by the predictive model, motivating a mandatory intake checklist. The full recommendation table with evidence type and constraints appears in Section 6.2.

### 5.7 Additional Analyses

*Note: The following analyses (predictive modelling, SNA, clustering, temporal trends) extend beyond the six core business questions. They are included to provide supplementary insight and to demonstrate the application of complementary analytical techniques. The core answers to the six business questions are provided in Sections 5.1ג€“5.6 above.*

#### 5.7.1 Predictive Model ג€” Cancellation Probability

A Random Forest classifier (Breiman, 2001) was trained to predict whether a case will result in approval (*׳׳•׳©׳¨*) or cancellation/rejection. The dataset comprised 804 cases with definitive outcomes (52.5% approved, 47.5% cancelled/rejected), split 80/20 for training and testing.

**Results:**

| Model | Test AUC | 5-Fold Cross-Validated AUC |
|-------|----------|-------------------|
| Random Forest | **0.940** | 0.928 |
| XGBoost | 0.943 | 0.929 |

Feature importance analysis identifies the following top predictors:

| Rank | Feature | RF Importance |
|------|---------|---------------|
| 1 | Unique Stages Visited | 0.249 |
| 2 | Stage Responsible | 0.178 |
| 3 | Total Events | 0.170 |
| 4 | Cycle Time (days) | 0.148 |
| 5 | Initial Wait (days) | 0.100 |

The dominant predictor ג€” number of unique stages visited ג€” is consistent with the early-abandonment pattern: cases that are cancelled tend not to progress beyond the initial approval stages and therefore visit far fewer distinct stages. The `Has Budget Stage` binary feature further supports this: cases that never reach budget review are disproportionately likely to be cancelled. It should be noted that the predictive model's primary value in this context is explanatory (identifying which features differentiate outcomes) rather than operational (real-time prediction), since several features (e.g., cycle time, total events) are only known at case completion.

**[INSERT IMAGE: outputs/plots/feature_importance.png ג€” Caption: Figure 32. Random Forest feature importance ranking for the cancellation prediction model.]**

**[INSERT IMAGE: outputs/plots/confusion_matrix_rf.png ג€” Caption: Figure 33. Confusion matrix for the Random Forest classifier (test set, n=161).]**

#### 5.7.2 Social Network Analysis (SNA) and Centrality

A directed graph of resource handovers was constructed using NetworkX. Betweenness centrality identifies resources that act as critical "bridges" between departments ג€” high-betweenness nodes are system-level bottlenecks whose unavailability would halt the process. Degree centrality measures the volume of interaction each resource maintains.

**[INSERT IMAGE: outputs/plots/sna_handover.png ג€” Caption: Figure 34. Social Network Analysis ג€” handover-of-work graph showing resource interactions.]**

**[INSERT IMAGE: outputs/plots/sna_working_together.png ג€” Caption: Figure 35. Social Network Analysis ג€” working-together graph showing co-occurrence of resources within cases.]**

**[INSERT IMAGE: outputs/interactive_sna.html ג€” Caption: Figure 36 (interactive). SNA graph with nodes sized by degree centrality and coloured by betweenness centrality (red = high, blue = low). Open in a web browser for interactive exploration.]**

#### 5.7.3 Case Segmentation via K-Means Clustering

Unsupervised K-Means clustering (k = 4) was applied to segment cases based on three features: cycle time, event count, and reassignment count. Four distinct profiles emerged:

- **Fast/Simple (Cluster 1):** The "happy path" majority ג€” low event count, zero reassignments, median cycle time below 5 days.
- **Average (Cluster 2):** Typical cases encountering minor friction.
- **Complex/Slow (Cluster 3):** Cases with high internal rework and multiple reassignments.
- **Extreme Outliers (Cluster 4):** The P99 tail ג€” pathological event loops, >200 days in the system.

**[INSERT IMAGE: outputs/cluster_profiles.png ג€” Caption: Figure 35. Box-plot distributions across the four K-Means clusters, demonstrating that Extreme Outlier cases are structurally different (event count) from Fast/Simple cases ג€” not merely slower.]**

#### 5.7.4 Temporal Trend Analysis

Monthly cycle-time trends and case throughput were analysed to detect process improvement or deterioration over time. Seasonal patterns reveal case-volume peaks in Q1 (aligned with annual budget-cycle planning) and a secondary peak in Q3.

**[INSERT IMAGE: outputs/monthly_cycle_time_trend.png ג€” Caption: Figure 36. Monthly median and P90 cycle time with linear trend line and auto-annotated slope (days/month).]**

**[INSERT IMAGE: outputs/monthly_throughput.png - Caption: Figure 37. Monthly case throughput: cases started vs. completed, identifying potential backlogs.]**

**[INSERT IMAGE: outputs/monthly_backlog_trend.png — Caption: Figure 37b. Monthly backlog delta (cases started minus completed), showing when inflow exceeded completions and backlog pressure intensified.]**

**[INSERT IMAGE: outputs/dotted_chart.png ג€” Caption: Figure 38. Dotted chart ג€” each event plotted as a dot (time on x-axis, case on y-axis) showing the overall temporal distribution of process activity.]**

---

## 6. Conclusions and Operational Suggestions (׳׳¡׳§׳ ׳•׳× ׳•׳”׳¦׳¢׳•׳× ׳׳•׳₪׳¨׳˜׳™׳‘׳™׳•׳×)

### 6.1 Key Conclusions

The process mining analysis of the Haifa Municipality's recruitment workflow reveals six principal findings:

**Finding 1 ג€” Budgeting and executive gates appear to be the main long-tail risk factors.** The Budget Recommendation stage exhibits a median near zero but a maximum exceeding 340 days. The predictive model's top feature (unique stages visited) is consistent with the interpretation that cases which never reach budget review are disproportionately likely to be cancelled.

**Finding 2 ג€” Aggregate workload volume does not explain delays.** The near-zero correlation (r ג‰ˆ 0.0) between departmental workload and cycle time suggests that delays are concentrated at specific approval gates (CEO, Budget, Mayor) rather than caused by overloaded departments. While this does not rule out localised congestion at specific stages, it is consistent with the hypothesis that approval-gate restructuring may be more effective than adding departmental capacity.

**Finding 3 ג€” The tender-to-committee corridor is the slowest segment.** All five slowest variant paths traverse the post-CEO external-tender track. Mean cycle time for these paths (270ג€“317 days) is approximately 3ֳ— the completed-case mean (98.1 days).

**Finding 4 ג€” Extreme right-skew dominates the completed-case distribution.** Among the 804 completed cases, the median cycle time is 62.8 days while the P95 reaches 298.9 days. A small minority of cases stuck at executive-approval stages or the tender-to-committee corridor drive the long tail.

**Finding 5 ג€” Responsible-party reassignment is positively correlated with cycle time, but causation is unclear.** Spearman ֿ = 0.444 (p < 0.001) indicates a moderate positive association. However, this likely reflects the structural relationship between case complexity and handover frequency. Cases stalling at a single stage without reassignment tend to represent either immediate cancellations or dormant cases, motivating auto-escalation interventions rather than handover restriction.

**Finding 6 ג€” Early abandonment patterns are observed among cancelled cases.** The Random Forest model (AUC = 0.940) identifies unique stages visited as the strongest predictor. Cancelled cases tend not to progress to the budget stage, which is consistent with ג€” though not proof of ג€” the hypothesis that incomplete or premature submissions contribute to the 44.8% cancellation rate among completed cases.

### 6.2 Operational Recommendations

Each recommendation is grounded in specific analytical findings and targeted at a concrete process element.

**[INSERT IMAGE: outputs/executive_dashboard.png - Caption: Figure 39. Executive recommendation dashboard summarising the highest-priority intervention targets by combined wait-time and rework burden.]**

**Recommendation 1 ג€” Pilot an Illustrative 7-Day SLA on Budget Recommendation.**
*Basis:* Finding 1 (budget stage maximum exceeds 340 days; the stage exhibits the highest single-stage long-tail risk).
*Mechanism:* Pilot a 7-day processing limit on a subset of departments. Cases exceeding this threshold are auto-escalated to the HR Division Head.
*Evidence type:* Inferred from long-tail skew and bottleneck concentration (Section 5.1.1); the specific 7-day threshold is a managerial proposal rather than a data-derived optimum.
*Constraint:* Feasibility depends on the Budget Department's capacity to process within 7 days; pilot testing is recommended before full rollout.

**Recommendation 2 ג€” Automate Committee Date Scheduling.**
*Basis:* Finding 3 (committee stages show >150 internal events per case); Section 5.5.1 (highest internal complexity).
*Mechanism:* Replace the current manual scheduling process with an automated calendar-matching tool. Pre-schedule committee sessions at the start of each quarter (aligned with Q1/Q3 seasonal peaks identified in temporal analysis).
*Evidence type:* Inferred from high internal event count in committee stages; the specific scheduling mechanism is a managerial proposal rather than a data-proven intervention.
*Constraint:* Statutory committee procedures may limit scheduling flexibility.

**Recommendation 3 ג€” Mandatory Intake Checklist.**
*Basis:* Finding 6 (early abandonment pattern ג€” 44.8% cancellation rate among completed cases, with cancelled cases tending not to reach budget review).
*Mechanism:* Require all supporting documents (budget check, job description, departmental approval) to be attached before the first approval stage can be initiated. Reject incomplete submissions at the system level.
*Evidence type:* Inferred from the predictive model feature importance and cancellation-stage analysis; the specific intake design is a managerial proposal.
*Constraint:* Overly restrictive intake requirements could delay legitimate submissions.

**Recommendation 4 ג€” 14-Day Inactivity Auto-Escalation.**
*Basis:* Finding 5 (dormant cases tend to remain with a single owner without reassignment); Section 5.4.3 (inactivity as a signal of stalled cases).
*Mechanism:* Implement an automated trigger that escalates any case with no activity for 14 consecutive calendar days to the next management level.
*Evidence type:* Directly supported by reassignment analysis showing that stalled cases lack ownership transitions.
*Constraint:* Some stages (e.g., statutory tender publication windows) legitimately require extended wait periods and should be exempted.

**Recommendation 5 ג€” Parallelise Salary Simulation with Division Head Approval.**
*Basis:* Section 5.5.3 (15% of cases execute salary checks sequentially rather than in parallel).
*Mechanism:* Configure the system to auto-trigger salary simulation when the Budget Recommendation stage is initiated, removing the dependency on manual handoff.
*Evidence type:* Directly supported by parallel-track compliance analysis.
*Constraint:* System configuration change; requires IT coordination.

**Recommendation 6 ג€” Pilot an Illustrative 10-Day Escalation Threshold for CEO/Mayor Decisions.**
*Basis:* Finding 4 (CEO Decision maximum exceeds 340 days; Mayor's Office exhibits the longest average role duration).
*Mechanism:* Establish a dedicated routing queue for executive-level decisions with a 10-day escalation threshold. Cases exceeding the limit are flagged for deputy-level sign-off.
*Evidence type:* Inferred from long-tail skew and bottleneck concentration (Section 5.1.2); the specific 10-day threshold is a managerial proposal rather than a data-derived optimum.
*Constraint:* Implementation feasibility depends on organisational governance policies and whether deputy sign-off is legally permissible for all decision types.

---

## 7. Appendices

### 7.1 Code Submission

The complete analysis pipeline is submitted as a separate code archive. The pipeline comprises 19 sequential modules executed via `run_all.py`:

- `src/preprocessing.py` ג€” Data cleaning and log preparation
- `src/preprocessing_charts.py` ג€” Preprocessing diagnostic visualisations
- `src/process_discovery.py` ג€” Multi-algorithm process discovery (Heuristics, Inductive, Alpha)
- `src/conformance_checking.py` ג€” Token-based replay and normative checkpoint coverage
- `src/bottleneck_analysis.py` ג€” Stage, role, user, and department bottleneck identification
- `src/variant_analysis.py` ג€” Variant extraction and frequency analysis
- `src/workload_analysis.py` ג€” Departmental workload-cycle time correlation
- `src/responsible_change.py` ג€” Responsible-party change analysis with confound control
- `src/internal_process.py` ג€” Intra-stage complexity and changed-field analysis
- `src/predictive_model.py` ג€” Random Forest / XGBoost cancellation prediction
- `src/sojourn_time.py` ג€” Stage dwell-time analysis
- `src/temporal_trends.py` ג€” Monthly cycle-time trends and throughput
- `src/statistical_tests.py` ג€” Mann-Whitney U hypothesis testing
- `src/sna_analysis.py` ג€” Social Network Analysis with centrality metrics
- `src/clustering.py` ג€” K-Means case segmentation

All outputs (charts, CSVs, JSON reports) are saved to the `outputs/` directory.

### 7.2 Tools and Libraries

- **pm4py** (v2.x) ג€” Process mining operations (DFG, Petri net, conformance)
- **scikit-learn** ג€” Random Forest classifier and K-Means clustering
- **XGBoost** ג€” Gradient-boosted tree validation model
- **NetworkX** ג€” Social network analysis and centrality computation
- **pandas / NumPy** ג€” Data manipulation and statistical computation
- **matplotlib / seaborn / Plotly** ג€” Visualisation

### 7.3 References

- van der Aalst, W. M. P. (2016). *Process Mining: Data Science in Action* (2nd ed.). Springer.
- van der Aalst, W. M. P., Weijters, A. J. M. M., & Maruster, L. (2004). Workflow mining: Discovering process models from event logs. *IEEE TKDE*, 16(9), 1128ג€“1142.
- Breiman, L. (2001). Random forests. *Machine Learning*, 45(1), 5ג€“32.
- Dumas, M., La Rosa, M., Mendling, J., & Reijers, H. A. (2018). *Fundamentals of Business Process Management* (2nd ed.). Springer.
- Leemans, S. J. J., Fahland, D., & van der Aalst, W. M. P. (2014). Discovering block-structured process models from event logs containing infrequent behaviour. In *BPM Workshops* (pp. 66ג€“78). Springer.
- Weijters, A. J. M. M., & Ribeiro, J. T. S. (2011). Flexible heuristics miner (FHM). In *Proc. IEEE CIDM* (pp. 310ג€“317).

---

*Report assembled from a 19-step automated process mining pipeline applied to 1,126,436 raw events (22,299 after preprocessing) across 11,922 recruitment cases from the Haifa Municipality (2024).*








