import unittest

from src.process_discovery import _variant_frequency


class TestProcessDiscoveryHelpers(unittest.TestCase):
    def test_variant_frequency_normalization(self):
        self.assertEqual(_variant_frequency(4), 4)
        self.assertEqual(_variant_frequency(['a', 'b']), 2)
        self.assertEqual(_variant_frequency('3'), 3)
        self.assertEqual(_variant_frequency('x'), 0)


if __name__ == '__main__':
    unittest.main()
