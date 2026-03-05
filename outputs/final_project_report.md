# Final Project Report: Job Staffing Process at Haifa Municipality

## Executive Summary (≤1 page)
This section synthesizes goals, key findings, and recommendations. For compact KPI wording, see `executive_summary.md`.

# Executive Process Mining Summary

## KPIs
- Cases analyzed: 11922
- Avg cycle time (days): 6.86
- Median cycle time (days): 0.00
- P90 cycle time (days): 0.00

## Top Bottlenecks
- חוזה נחתם ע"י כל הגורמים: 36.60 mean wait days
- החלטת ועדת מכרזים - התאמת מועמדים (מכרז פנימי) - מלבד רמ"ד: 33.49 mean wait days
- אישור קביעת מועד ועדה עבור הליך גיוס - מכרז: 32.67 mean wait days
- החלטת ועדת מכרזים (מכרז חיצוני + פנימי): 31.56 mean wait days
- החלטת הועדה - התאמת מועמדים - ללא מכרז: 21.23 mean wait days

## Top Rework Activities
- מכרז פנימי לפרסום: rework ratio 0.13
- אישור יידוע נוסח המכרז נציג ועד העובדים: rework ratio 0.12
- אישור סיום נוסח מכרז: rework ratio 0.12
- אישור נוסח מכרז ע"י מנהל היחידה המבקשת (אגף): rework ratio 0.12

## Introduction
This report analyzes the staffing/recruitment lifecycle to identify delay drivers and propose concrete operational improvements.
The analysis combines event-log preprocessing, process pathing, performance/workload diagnostics, ownership/rework effects, and alignment checks.

## Preprocessing
Purpose: standardize log schema, parse dates, remove invalid records, and produce analysis-ready event traces.
Artifacts: `cleaned_log.csv`, `event_log.xes`, `preprocessing_quality_report.json`, and preprocessing plots in outputs.
Quality snapshot: rows_after_cleaning=22299, dropped_missing=0, dropped_duplicates=85991
Suggested evidence charts: `activity_frequency_top15.png`, `case_cycle_time_distribution.png`.

## Process Pathing (Variants)
Main variants extracted from the cleaned event log:
- Variant=('תכנון - בקרת כ"א',), Frequency=665
- Variant=('החלטת מנכ"ל - גיוס',), Frequency=653
- Variant=('המלצת גיוס של אגף משאבי אנוש',), Frequency=648
- Variant=('המלצת איוש ואופן גיוס',), Frequency=647
- Variant=('המלצת תקציב לגיוס',), Frequency=644
- Variant=('אישור קביעת מועד ועדה עבור הליך גיוס - מכרז',), Frequency=569
- Variant=('אישור מנהל אגף',), Frequency=493
- Variant=('אישור מנהל מחלקה',), Frequency=491
Interpretation support: `variant_frequency_top15.png`, `activity_transition_heatmap_top12.png`.

## Analyses (Business Questions)
### 1) Where are the delays?
Top bottleneck stages:
- activity=חוזה נחתם ע"י כל הגורמים, mean_wait_days=36.59997608024692
- activity=החלטת ועדת מכרזים - התאמת מועמדים (מכרז פנימי) - מלבד רמ"ד, mean_wait_days=33.492384118112014
- activity=אישור קביעת מועד ועדה עבור הליך גיוס - מכרז, mean_wait_days=32.67451955685109
- activity=החלטת ועדת מכרזים (מכרז חיצוני + פנימי), mean_wait_days=31.555418788580248
- activity=החלטת הועדה - התאמת מועמדים - ללא מכרז, mean_wait_days=21.227091104497354
- activity=אישור טיפול במינוי קרובי משפחה - מלבד רמ"ד, mean_wait_days=19.495270310633217
- activity=מינוי מועמד לפי בחירת ועדת מכרזים, mean_wait_days=16.80004858065302
- activity=המלצת תקציב לגיוס, mean_wait_days=16.15439467216811
Top delaying departments:
- department=סמנכ"ל משאבי אנוש וא, mean_cycle_time_days=345.44782407407405
- department=תיכון עירוני אלמותנב, mean_cycle_time_days=323.10445601851853
- department=טקסים ואירועים רשמיי, mean_cycle_time_days=301.3636458333333
- department=רשות צעירים, mean_cycle_time_days=290.8043634259259
- department=מח" אכיפת גביה ממגור, mean_cycle_time_days=289.90046875
Delays by outcomes/status:
- request_status=טיוטה, mean_cycle_time_days=160.2535300925926
- request_status=סבב אישורים, mean_cycle_time_days=132.5389269179894
- request_status=אושר, mean_cycle_time_days=126.06916556959804
- request_status=לא אושר, mean_cycle_time_days=77.50645096801347
- request_status=בוטל, mean_cycle_time_days=66.4656250321502

### 2) Variants and longest delays
Use `variants.csv` with bottleneck tables to inspect which paths coincide with prolonged waits.

### 3) Workload vs Speed
Average open cases by department:
- Department=מוסדות-ניהול עצמי, Open_Cases=15.73076923076923
- Department=רשות הספורט, Open_Cases=7.384615384615385
- Department=המח. לשירותי נקיון, Open_Cases=6.903846153846154
- Department=העצמה חינוכית וטיפול בפרט, Open_Cases=6.673076923076923
- Department=המחלקה לנוער, Open_Cases=6.1923076923076925

### 4) Ownership changes and delays
- has_reassignment=False, mean=0.0315188102925043
- has_reassignment=True, mean=14.287518555004215

### 5) Internal subprocesses and delays
- activity=דיווח הדמיית שכר, rework_ratio=0.0958164642375168, avg_duration_days=8.479463547133504
- activity=אישור סיום נוסח מכרז, rework_ratio=0.1197691197691197, avg_duration_days=12.91004911883384
- activity=אישור נוסח מכרז ע"י מנהל היחידה המבקשת (אגף), rework_ratio=0.1176470588235294, avg_duration_days=11.863938033912396
- activity=נתוני תנאי שרות להדמייה, rework_ratio=0.0905707196029776, avg_duration_days=7.872151298708759
- activity=מכרז פנימי לפרסום, rework_ratio=0.1297208538587849, avg_duration_days=13.069010654229764
- activity=אישור יידוע נוסח המכרז נציג ועד העובדים, rework_ratio=0.1234375, avg_duration_days=12.061329011140046
- activity=אישור נוסח מכרז ע"י מנהל היחידה המבקשת (מינהל), rework_ratio=0.1134020618556701, avg_duration_days=10.510983676975943
- activity=החלטת גיוס גזבר, rework_ratio=0.1071975497702909, avg_duration_days=11.418775026941184

### 6) Process-specific checks (legal windows, junior path, station mapping)
Legal-interval candidate summary:
- activity=אישור גיוס - החלטת הועדה, mean_wait_days=nan, regulated_window_14_45_ratio=0.0
- activity=אישור מיון וסינון מועמדים, mean_wait_days=0.8547089629120879, regulated_window_14_45_ratio=0.0
- activity=אישור קביעת מועד ועדה עבור הליך גיוס - מכרז, mean_wait_days=32.67451955685109, regulated_window_14_45_ratio=0.3026785714285714
- activity=החלטת הועדה - התאמת מועמדים - ללא מכרז, mean_wait_days=21.227091104497354, regulated_window_14_45_ratio=0.2171052631578947
Junior-position path proxy:
- is_junior_proxy=False, mean=6.85937978515443
Station mapping coverage (municipality narrative):
- station=Initiation, covered=False, matched_activity_count=0
- station=Approval Hierarchy, covered=True, matched_activity_count=20
- station=HR Control, covered=True, matched_activity_count=1
- station=Recruitment Strategy, covered=True, matched_activity_count=12
- station=Financial & Executive Oversight, covered=True, matched_activity_count=3
- station=Parallel Tracks, covered=True, matched_activity_count=2
- station=Implementation, covered=True, matched_activity_count=7
- station=Selection, covered=True, matched_activity_count=4
- station=Outcomes, covered=False, matched_activity_count=0

## Conclusions & Recommendations
Prioritize interventions on stages with both high mean wait and high rework ratio.
Stabilize ownership handoffs for stages where reassignment is associated with longer cycle times.
Use workload heatmaps and department cycle-time tables to balance staffing and SLA commitments.
Track legal-window and committee/screening stages with dedicated KPIs each reporting cycle.

## Appendices
- Code: `src/`
- Artifacts: `outputs/` (CSV, PNG, JSON, MD)
- Alignment checklist: `alignment_report.md`
