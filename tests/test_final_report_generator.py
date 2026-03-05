import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.final_report_generator import generate_final_project_report


class TestFinalReportGenerator(unittest.TestCase):
    def test_generate_final_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            pd.DataFrame([{'Variant': 'A>B', 'Frequency': 3}]).to_csv(out / 'variants.csv', index=False)
            pd.DataFrame([{'activity': 'A', 'mean_wait_days': 2.0}]).to_csv(out / 'bottleneck_by_stage.csv', index=False)
            pd.DataFrame([{'department': 'HR', 'mean_cycle_time_days': 5.0}]).to_csv(out / 'cycle_time_by_department.csv', index=False)
            pd.DataFrame([{'request_status': 'Approved', 'mean_cycle_time_days': 4.0}]).to_csv(out / 'cycle_time_by_request_status.csv', index=False)
            pd.DataFrame([{'has_reassignment': True, 'mean': 6.0}]).to_csv(out / 'responsible_change_analysis.csv', index=False)
            pd.DataFrame([{'activity': 'A', 'rework_ratio': 0.2, 'avg_duration_days': 2.0}]).to_csv(out / 'internal_process_analysis.csv', index=False)
            pd.DataFrame([{'Department': 'HR', 'Open_Cases': 10}]).to_csv(out / 'workload_analysis.csv', index=False)
            pd.DataFrame([{'activity': 'Committee', 'mean_wait_days': 20, 'regulated_window_14_45_ratio': 0.6}]).to_csv(out / 'legal_interval_analysis.csv', index=False)
            pd.DataFrame([{'is_junior_proxy': True, 'mean': 3.0}]).to_csv(out / 'junior_position_path_analysis.csv', index=False)
            pd.DataFrame([{'station': 'Selection', 'covered': True, 'matched_activity_count': 2}]).to_csv(out / 'station_mapping_coverage.csv', index=False)
            (out / 'executive_summary.md').write_text('# Executive\n', encoding='utf-8')

            report_path = generate_final_project_report(out)
            self.assertTrue(report_path.exists())
            content = report_path.read_text(encoding='utf-8')
            self.assertIn('## Executive Summary', content)
            self.assertIn('## Process Pathing (Variants)', content)


if __name__ == '__main__':
    unittest.main()
