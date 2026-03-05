import json
import tempfile
import unittest
from pathlib import Path

from src.alignment_report import generate_alignment_report


class TestAlignmentReport(unittest.TestCase):
    def test_alignment_report_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for name in [
                'bottleneck_by_stage.csv',
                'bottleneck_by_stage_owner.csv',
                'bottleneck_by_performer.csv',
                'cycle_time_by_department.csv',
                'cycle_time_by_request_status.csv',
                'variants.csv',
                'bottleneck_analysis.csv',
                'workload_analysis.csv',
                'responsible_change_analysis.csv',
                'internal_process_analysis.csv',
                'keyword_bottleneck_analysis.csv',
                'legal_interval_analysis.csv',
                'junior_position_path_analysis.csv',
                'station_mapping_coverage.csv',
                'executive_summary.md',
                'final_project_report.md',
            ]:
                (out / name).write_text('x', encoding='utf-8')

            report = generate_alignment_report(out)
            self.assertEqual(report['alignment_score_pct'], 100.0)
            self.assertTrue((out / 'alignment_report.json').exists())
            self.assertTrue((out / 'alignment_report.md').exists())

            payload = json.loads((out / 'alignment_report.json').read_text(encoding='utf-8'))
            self.assertEqual(payload['covered_checks'], payload['total_checks'])


if __name__ == '__main__':
    unittest.main()
