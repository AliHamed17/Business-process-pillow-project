import json
import tempfile
import unittest
from pathlib import Path

from src.run_pipeline import _write_pipeline_manifest


class TestPipelineHelpers(unittest.TestCase):
    def test_write_pipeline_manifest_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / 'cleaned_log.csv').write_text('a,b\n1,2\n', encoding='utf-8')
            _write_pipeline_manifest(out, top_variants=15)

            payload = json.loads((out / 'pipeline_manifest.json').read_text(encoding='utf-8'))
            self.assertIn('generated_at_utc', payload)
            self.assertEqual(payload['top_variants'], 15)
            self.assertIn('artifacts', payload)
            self.assertTrue(any(item['file'] == 'cleaned_log.csv' for item in payload['artifacts']))
            self.assertTrue(any(item['file'] == 'activity_frequency_top15.png' for item in payload['artifacts']))
            self.assertTrue(any(item['file'] == 'executive_summary.json' for item in payload['artifacts']))
            self.assertTrue(any(item['file'] == 'workload_heatmap_department_week.png' for item in payload['artifacts']))
            self.assertTrue(any(item['file'] == 'alignment_report.json' for item in payload['artifacts']))


if __name__ == '__main__':
    unittest.main()
