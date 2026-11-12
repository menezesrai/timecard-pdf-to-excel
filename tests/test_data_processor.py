import unittest

from data_processor import DataProcessor


class DataProcessorTest(unittest.TestCase):
    def test_simple_mode_keeps_only_positive_time_bank(self):
        work_data = {"data_row": {"BCRED.": "01:30"}}

        self.assertTrue(DataProcessor.should_include_page(work_data, mode="simple"))

    def test_simple_mode_skips_empty_positive_time_bank(self):
        work_data = {"data_row": {"BCRED.": "00:00"}}

        self.assertFalse(DataProcessor.should_include_page(work_data, mode="simple"))

    def test_complete_mode_keeps_observations_even_without_hours(self):
        work_data = {
            "data_row": {
                "EX100%": "00:00",
                "EXTRA": "00:00",
                "BCRED.": "00:00",
                "BDEB.": "00:00",
                "NOT TOTAL": "00:00",
                "OBS": "Falta abonada",
            }
        }

        self.assertTrue(DataProcessor.should_include_page(work_data, mode="complete"))


if __name__ == "__main__":
    unittest.main()
