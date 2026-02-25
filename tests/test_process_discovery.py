import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.process_discovery import _variant_frequency, generate_process_models


class TestProcessDiscoveryHelpers(unittest.TestCase):
    def test_variant_frequency_normalization(self):
        self.assertEqual(_variant_frequency(4), 4)
        self.assertEqual(_variant_frequency(['a', 'b']), 2)
        self.assertEqual(_variant_frequency('3'), 3)
        self.assertEqual(_variant_frequency('x'), 0)

    def test_top_variants_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log = pd.DataFrame([
                {'case_id': 1, 'activity': 'A', 'timestamp': '2024-01-01'},
                {'case_id': 1, 'activity': 'B', 'timestamp': '2024-01-02'},
            ])
            log_path = tmp_path / 'cleaned_log.csv'
            log.to_csv(log_path, index=False)

            with self.assertRaises(ValueError):
                generate_process_models(log_path, tmp_path, top_variants=0)


if __name__ == '__main__':
    unittest.main()
