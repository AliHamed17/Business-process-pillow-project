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
- אישור נוסח מכרז ע"י מנהל היחידה המבקשת (מינהל): rework ratio 0.11

## Workload Hotspots
- מוסדות-ניהול עצמי: avg open cases 15.73
- רשות הספורט: avg open cases 7.38
- המח. לשירותי נקיון: avg open cases 6.90
- העצמה חינוכית וטיפול בפרט: avg open cases 6.67
- המחלקה לנוער: avg open cases 6.19

## Reassignment Impact
- Mean cycle time (no reassignment): 0.03
- Mean cycle time (with reassignment): 14.29
- Delta days: 14.26
- Relative increase (%): 45230.13

## Priority Recommendations
- אישור קביעת מועד ועדה עבור הליך גיוס - מכרז (score=0.826, wait=32.67, rework=0.09)
- החלטת ועדת מכרזים (מכרז חיצוני + פנימי) (score=0.659, wait=31.56, rework=0.05)
- חוזה נחתם ע"י כל הגורמים (score=0.615, wait=36.60, rework=0.00)
- מכרז פנימי לפרסום (score=0.583, wait=11.14, rework=0.13)
- החלטת ועדת מכרזים - התאמת מועמדים (מכרז פנימי) - מלבד רמ"ד (score=0.564, wait=33.49, rework=0.00)

## Risk Signals
- long_tail_cycle_time: NO
- high_stage_wait: YES
- department_load_concentration: NO

## Result Quality
- Source completeness: 1.00
- Present sources: case_performance, bottleneck_analysis, variants, workload_analysis, responsible_change_analysis, internal_process_analysis
- Missing sources: None

## Key Messages
- Long-tail performance remains material (P90 cycle time: 0.00 days).
- Highest waiting stage is 'חוזה נחתם ע"י כל הגורמים' with 36.60 mean days.
- Reassignment is associated with a 45230.1% increase in cycle time.
