import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import pandas as pd


class TestPipelineSanityResults(unittest.TestCase):
    def test_end_to_end_pipeline_outputs_and_alignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cols = [
                'מזהה רשומה', 'תאריך שינוי', 'מבצע שינוי', 'אירוע', 'יישות בשינוי',
                'מזהה שלב', 'שם שלב', 'תאריך יעד לשלב', 'תאריך סיום שלב', 'אחראי שלב',
                'סטטוס בקשה ', 'תקן', 'מזהה בקשה', 'מחלקה', 'מספר מחלקה',
                'שדה שהשתנה', 'ערכים שהשתנו (גולמי)'
            ]

            rows1 = [
                [1, '2024-01-01 08:00', 'u1', 'create', 'x', 1, 'Open', '2024-01-05', None, 'r1', 'Approved', 'Junior Help Wanted', 100, 'HR', 10, '', ''],
                [1, '2024-01-03 09:00', 'u2', 'update', 'x', 2, 'Screening', '2024-01-06', None, 'r2', 'In Progress', 'Junior Help Wanted', 100, 'HR', 10, 'אחראי שלב', ''],
                [2, '2024-01-02 10:00', 'u3', 'create', 'x', 1, 'Open', '2024-01-05', None, 'r3', 'Canceled', 'Existing Position', 200, 'Finance', 20, '', ''],
            ]
            rows2 = [
                [1, '2024-01-20 11:00', 'u2', 'complete', 'x', 2, 'Committee', '2024-01-06', '2024-01-20', 'r2', 'Approved', 'Junior Help Wanted', 100, 'HR', 10, '', ''],
                [2, '2024-01-05 12:00', 'u4', 'update', 'x', 3, 'Approve', '2024-01-07', None, 'r4', 'In Progress', 'Existing Position', 200, 'Finance', 20, 'אחראי שלב', ''],
                [2, '2024-01-06 13:00', 'u4', 'complete', 'x', 3, 'Approve', '2024-01-07', '2024-01-06', 'r4', 'Canceled', 'Existing Position', 200, 'Finance', 20, '', ''],
            ]

            file1 = base / 'part1.xlsx'
            file2 = base / 'part2.xlsx'
            out = base / 'outputs'
            pd.DataFrame(rows1, columns=cols).to_excel(file1, index=False)
            pd.DataFrame(rows2, columns=cols).to_excel(file2, index=False)

            subprocess.run(
                ['python', 'src/run_pipeline.py', str(file1), str(file2), '--output-dir', str(out)],
                check=True,
            )

            expected = [
                'cleaned_log.csv',
                'variants.csv',
                'bottleneck_by_stage.csv',
                'executive_summary.md',
                'final_project_report.md',
                'alignment_report.json',
                'pipeline_manifest.json',
            ]
            for artifact in expected:
                self.assertTrue((out / artifact).exists(), f'Missing artifact: {artifact}')

            alignment = json.loads((out / 'alignment_report.json').read_text(encoding='utf-8'))
            self.assertEqual(alignment['alignment_score_pct'], 100.0)

            manifest = json.loads((out / 'pipeline_manifest.json').read_text(encoding='utf-8'))
            artifacts = {item['file']: item['exists'] for item in manifest['artifacts']}
            self.assertTrue(artifacts.get('final_project_report.md', False))
            self.assertTrue(artifacts.get('station_mapping_coverage.csv', False))


if __name__ == '__main__':
    unittest.main()
