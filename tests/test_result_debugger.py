import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.result_debugger import debug_results


class TestResultDebugger(unittest.TestCase):
    def test_debug_results_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            pd.DataFrame([{'case_id': 1, 'cycle_time_days': 3.0}]).to_csv(out / 'case_performance.csv', index=False)
            pd.DataFrame([{'Variant': 'v1', 'Frequency': 1}]).to_csv(out / 'variants.csv', index=False)
            pd.DataFrame([{'Department': 'HR', 'Open_Cases': 2}]).to_csv(out / 'workload_analysis.csv', index=False)
            (out / 'alignment_report.json').write_text(json.dumps({'alignment_score_pct': 100}), encoding='utf-8')

            report = debug_results(out)
            self.assertEqual(report['overall_status'], 'pass')
            self.assertTrue((out / 'results_debug_report.json').exists())
            self.assertTrue((out / 'results_debug_report.md').exists())


if __name__ == '__main__':
    unittest.main()
