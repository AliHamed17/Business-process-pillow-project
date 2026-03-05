import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.result_insights import generate_result_insights


class TestResultInsights(unittest.TestCase):
    def test_generate_result_insights_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            pd.DataFrame([
                {'case_id': 1, 'cycle_time_days': 3.0},
                {'case_id': 2, 'cycle_time_days': 5.0},
            ]).to_csv(out / 'case_performance.csv', index=False)
            pd.DataFrame([
                {'activity': 'A', 'mean': 2.0},
                {'activity': 'B', 'mean': 1.0},
            ]).to_csv(out / 'bottleneck_analysis.csv', index=False)
            pd.DataFrame([
                {'activity': 'A', 'rework_ratio': 0.8},
                {'activity': 'B', 'rework_ratio': 0.2},
            ]).to_csv(out / 'internal_process_analysis.csv', index=False)
            pd.DataFrame([
                {'Variant': 'v1', 'Frequency': 10},
            ]).to_csv(out / 'variants.csv', index=False)
            pd.DataFrame([
                {'Department': 'HR', 'Open_Cases': 5},
            ]).to_csv(out / 'workload_analysis.csv', index=False)
            pd.DataFrame([
                {'has_reassignment': False, 'mean': 4.0},
                {'has_reassignment': True, 'mean': 6.0},
            ]).to_csv(out / 'responsible_change_analysis.csv', index=False)

            summary = generate_result_insights(out)
            self.assertIn('kpis', summary)
            self.assertEqual(summary['kpis']['cases_analyzed'], 2)
            self.assertTrue((out / 'executive_summary.json').exists())
            self.assertTrue((out / 'executive_summary.md').exists())
            self.assertTrue((out / 'executive_dashboard.png').exists())

            payload = json.loads((out / 'executive_summary.json').read_text(encoding='utf-8'))
            self.assertTrue(len(payload['priority_recommendations']) >= 1)
            self.assertIn('risk_signals', payload)
            self.assertIn('result_quality', payload)
            self.assertGreater(payload['result_quality']['completeness_ratio'], 0)

            md = (out / 'executive_summary.md').read_text(encoding='utf-8')
            self.assertIn('## Key Messages', md)
            self.assertIn('## Result Quality', md)


if __name__ == '__main__':
    unittest.main()
