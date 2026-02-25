import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.cli_utils import load_clean_log, validate_columns


class TestCliUtils(unittest.TestCase):
    def test_validate_columns_missing(self):
        df = pd.DataFrame({'a': [1]})
        with self.assertRaises(ValueError):
            validate_columns(df, ['a', 'b'], context='unit-test')

    def test_load_clean_log_drops_invalid_core_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / 'cleaned.csv'
            pd.DataFrame(
                [
                    {'case_id': 1, 'activity': 'A', 'timestamp': '2024-01-01'},
                    {'case_id': None, 'activity': 'A', 'timestamp': '2024-01-02'},
                    {'case_id': 2, 'activity': 'B', 'timestamp': 'not-a-date'},
                ]
            ).to_csv(csv_path, index=False)

            df = load_clean_log(csv_path, ['case_id', 'activity', 'timestamp'], context='unit-test')
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]['activity'], 'A')


if __name__ == '__main__':
    unittest.main()
