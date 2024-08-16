import datetime as dt

import unittest
from unittest.mock import Mock, patch, MagicMock

import pandas as pd
import pytz
from entsoe import entsoe

import market_data.AbstractQueryMarketPrices
from market_data.AbstractQueryMarketPrices import AbstractQueryMarketPrices


class TestAbstractQueryMarketPrices(unittest.TestCase):

    def setUp(self) -> None:
        # Data from ENTSOE comes as a series
        data = [10.5, 15.2, 7.8, 22.3]
        datetime_index = pd.to_datetime([
            "2024-07-05 00:00:00+02:00",
            "2024-07-05 01:00:00+02:00",
            "2024-07-05 02:00:00+02:00",
            "2024-07-05 03:00:00+02:00"
        ])
        # Create the Series
        self.example_series = pd.Series(data, index=datetime_index)

        # We convert it to a PriceScheduleDataFrame
        data = {
            'charge_price': [13.54, 6.37, 4.00, 2.67],
            'discharge_price': [13.54, 6.37, 4.00, 2.67]
        }
        # Index (timestamps)
        index = pd.date_range(start="2024-07-05 00:00:00", periods=4, freq="h", tz="Europe/Berlin")
        # Create DataFrame
        self.example_df = pd.DataFrame(data, index=index)

        # Set up timezone-aware and timezone-unaware start and end times
        self.tz_aware_start = dt.datetime(2023, 8, 16, 12, 0, tzinfo=pytz.timezone("Europe/Amsterdam"))
        self.tz_aware_end = dt.datetime(2023, 8, 16, 14, 0, tzinfo=pytz.timezone("Europe/Amsterdam"))
        self.tz_unaware_start = dt.datetime(2023, 8, 16, 12, 0)
        self.tz_unaware_end = dt.datetime(2023, 8, 16, 14, 0)

        # Setup areas with matching and non-matching timezones
        self.matching_area = entsoe.Area["NL"]
        self.non_matching_area = entsoe.Area["GB_IFA"]

    @patch('pandas.read_pickle')
    def test_very_first_update_hot_load(self, mock_read_pickle):
        mock_read_pickle.side_effect = FileNotFoundError()
        mock_to_pickle = Mock()
        self.example_df.to_pickle = mock_to_pickle()
        AbstractQueryMarketPrices.update_hot_load(self.example_df, file_name="test_market_data/dayahead_data.pkl")
        self.example_df.to_pickle.assert_called_with("test_market_data/dayahead_data.pkl")

    @patch('pandas.read_pickle')
    def test_update_hot_load(self, mock_read_pickle):
        # The existing_df is the example_df
        mocked_res_df = Mock()
        self.example_df.combine_first = MagicMock(return_value=mocked_res_df)
        mock_read_pickle.return_value = self.example_df

        # This overwrite_df contains new information before and after the existing_df
        data = {
            'charge_price': [4.57, 13.54, 6.37, 4.00, 2.67, 3.87],
            'discharge_price': [4.57, 13.54, 6.37, 4.00, 2.67, 3.87]
        }
        index = pd.date_range(start="2024-07-04 23:00:00", periods=6, freq="h", tz="Europe/Berlin")
        overwrite_df = pd.DataFrame(data, index=index)

        AbstractQueryMarketPrices.update_hot_load(overwrite_df, file_name="test_market_data/dayahead_data.pkl")

        mocked_res_df.to_pickle.assert_called_with("test_market_data/dayahead_data.pkl")

    def test_tz_aware_matching_area(self):
        # tz_aware, tz_aware, matching_area.tz
        start, end = AbstractQueryMarketPrices.verify_start_and_end_time(
            self.tz_aware_start,
            self.tz_aware_end,
            self.matching_area
        )

        expected_start = self.tz_aware_start.astimezone(pytz.timezone('Europe/Amsterdam'))
        expected_end = self.tz_aware_end.astimezone(pytz.timezone('Europe/Amsterdam'))

        self.assertEqual(expected_start, start)
        self.assertEqual(expected_end, end)

    def test_tz_aware_non_matching_area(self):
        # tz_aware, tz_aware, non_matching_area.tz
        start, end = AbstractQueryMarketPrices.verify_start_and_end_time(
            self.tz_aware_start,
            self.tz_aware_end,
            self.non_matching_area
        )

        expected_start = self.tz_aware_start.astimezone(pytz.timezone('Europe/London'))
        expected_end = self.tz_aware_end.astimezone(pytz.timezone('Europe/London'))

        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)

    def test_tz_unaware_non_matching_assume_naive_true(self):
        # tz_unaware, tz_aware, non_matching_area.tz, True
        start, end = AbstractQueryMarketPrices.verify_start_and_end_time(
            self.tz_unaware_start,
            self.tz_aware_end,
            self.non_matching_area,
            assume_naive_timezones=True
        )

        expected_start = pytz.timezone('Europe/London').localize(self.tz_unaware_start)
        expected_end = self.tz_aware_end.astimezone(pytz.timezone('Europe/London'))

        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)

    def test_tz_aware_tz_unaware_assume_naive_true(self):
        # tz_aware, tz_unaware, non_matching_area.tz, True
        start, end = AbstractQueryMarketPrices.verify_start_and_end_time(
            self.tz_aware_start,
            self.tz_unaware_end,
            self.non_matching_area,
            assume_naive_timezones=True
        )

        expected_start = self.tz_aware_start.astimezone(pytz.timezone('Europe/London'))
        expected_end = pytz.timezone('Europe/London').localize(self.tz_unaware_end)

        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)

    def test_tz_aware_tz_unaware_assume_naive_false(self):
        # tz_aware, tz_unaware, non_matching_area.tz, False
        with self.assertRaises(TypeError):
            AbstractQueryMarketPrices.verify_start_and_end_time(
                self.tz_aware_start,
                self.tz_unaware_end,
                self.non_matching_area,
                assume_naive_timezones=False
            )
            AbstractQueryMarketPrices.verify_start_and_end_time(
                self.tz_unaware_start,
                self.tz_aware_end,
                self.non_matching_area,
                assume_naive_timezones=False
            )

    @patch('market_data.AbstractQueryMarketPrices.AbstractQueryMarketPrices.verify_start_and_end_time')
    def test_convert_to_timezoned_pandas_object(self, mocked_verify_start_and_end_time):
        expected_start_pd = pd.Timestamp(self.tz_aware_start.strftime("%Y%m%d%H%M"), tz=self.matching_area.tz)
        expected_end_pd = pd.Timestamp(self.tz_aware_end.strftime('%Y%m%d%H%M'), tz=self.matching_area.tz)
        mocked_verify_start_and_end_time.return_value = (self.tz_aware_start, self.tz_aware_end)

        start_pd, end_pd = AbstractQueryMarketPrices.convert_to_timezoned_pandas_object(
            start_time=self.tz_unaware_start,
            end_time=self.tz_aware_end,
            entsoe_area=self.matching_area,
            assume_naive_timezones=False,
        )

        mocked_verify_start_and_end_time.assert_called_with(
            start_time=self.tz_unaware_start,
            end_time=self.tz_aware_end,
            entsoe_area=self.matching_area,
            assume_naive_timezones=False,
        )
        self.assertEqual(expected_start_pd, start_pd)
        self.assertEqual(expected_end_pd, end_pd)


if __name__ == "__main__":
    unittest.main()
