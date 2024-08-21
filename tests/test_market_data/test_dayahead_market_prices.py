import datetime as dt
import unittest
from unittest.mock import Mock, patch

import entsoe
import pandas as pd
import pytz

from market_data.DayaheadMarketPrices import DayaheadMarketPrices
from model import PriceScheduleDataFrame


class TestDayaheadMarketPrices(unittest.TestCase):

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

        self.timezone = pytz.timezone("Europe/Amsterdam")

    def test_cold_load_dayahead_data_tz_unaware(self):
        start_time = dt.datetime(2024, 7, 10)
        end_time = dt.datetime(2024, 7, 10, 23)
        mock_client = Mock()
        mock_client.query_day_ahead_prices.return_value = self.example_series

        res = DayaheadMarketPrices.cold_load_data(
            start_time=start_time,
            end_time=end_time,
            client=mock_client,
            store_in_hot_load=False
        )

        mock_client.query_day_ahead_prices.assert_called_with(
            country_code='10YNL----------L',
            start=pd.Timestamp('2024-07-10 00:00:00+0200', tz='Europe/Amsterdam'),
            end=pd.Timestamp('2024-07-10 23:00:00+0200', tz='Europe/Amsterdam')
        )
        PriceScheduleDataFrame.validate(res)

    def test_cold_load_dayahead_data_tz_unaware_other_area(self):
        start_time = dt.datetime(2024, 7, 10)
        end_time = dt.datetime(2024, 7, 10, 23)
        mock_client = Mock()
        mock_client.query_day_ahead_prices.return_value = self.example_series

        res = DayaheadMarketPrices.cold_load_data(
            start_time=start_time,
            end_time=end_time,
            client=mock_client,
            store_in_hot_load=False,
            entsoe_area=entsoe.Area['BE'],
        )

        mock_client.query_day_ahead_prices.assert_called_with(
            country_code='10YBE----------2',
            start=pd.Timestamp('2024-07-10 00:00:00+0200', tz='Europe/Brussels'),
            end=pd.Timestamp('2024-07-10 23:00:00+0200', tz='Europe/Brussels')
        )
        PriceScheduleDataFrame.validate(res)

    def test_cold_load_dayahead_data_tz_aware(self):
        start_time = dt.datetime(2024, 7, 9, 22, tzinfo=pytz.utc)
        end_time = dt.datetime(2024, 7, 10, 21, tzinfo=pytz.utc)
        mock_client = Mock()
        mock_client.query_day_ahead_prices.return_value = self.example_series

        res = DayaheadMarketPrices.cold_load_data(
            start_time=start_time,
            end_time=end_time,
            client=mock_client,
            store_in_hot_load=False
        )

        mock_client.query_day_ahead_prices.assert_called_with(
            country_code='10YNL----------L',
            start=pd.Timestamp('2024-07-10 00:00:00+0200', tz='Europe/Amsterdam'),
            end=pd.Timestamp('2024-07-10 23:00:00+0200', tz='Europe/Amsterdam')
        )
        PriceScheduleDataFrame.validate(res)

    @patch('market_data.DayaheadMarketPrices.DayaheadMarketPrices.update_hot_load')
    def test_cold_load_dayahead_data_tz_aware_other_area_and_hot_load_store(self, mock_update_hot_load):
        start_time = dt.datetime(2024, 7, 9, 22, tzinfo=pytz.utc)
        end_time = dt.datetime(2024, 7, 10, 21, tzinfo=pytz.utc)
        mock_client = Mock()
        mock_client.query_day_ahead_prices.return_value = self.example_series

        res = DayaheadMarketPrices.cold_load_data(
            start_time=start_time,
            end_time=end_time,
            client=mock_client,
            store_in_hot_load=True,
            entsoe_area=entsoe.Area["PL"]
        )

        mock_client.query_day_ahead_prices.assert_called_with(
            country_code='10YPL-AREA-----S',
            start=pd.Timestamp('2024-07-10 00:00:00+0200', tz='Europe/Warsaw'),
            end=pd.Timestamp('2024-07-10 23:00:00+0200', tz='Europe/Warsaw')
        )
        PriceScheduleDataFrame.validate(res)
        mock_update_hot_load.assert_called_with(res)

    def test_no_dst_transition(self):
        # Simple case: 3 hours between start and end, no DST transition
        start_time = self.timezone.localize(dt.datetime(2024, 10, 10, 1, 0, 0))
        end_time = self.timezone.localize(dt.datetime(2024, 10, 10, 4, 0, 0))

        expected_hours = 4  # 3 hours, but +1 as end_time is inclusive
        result = DayaheadMarketPrices.expected_length_of_data(start_time, end_time)
        self.assertEqual(result, expected_hours)

    def test_within_dst(self):
        # Case: 2 hours within DST period
        start_time = self.timezone.localize(dt.datetime(2024, 6, 15, 12, 0, 0))
        end_time = self.timezone.localize(dt.datetime(2024, 6, 15, 14, 0, 0))

        expected_hours = 3  # 2 hours, but +1 as end_time is inclusive
        result = DayaheadMarketPrices.expected_length_of_data(start_time, end_time)
        self.assertEqual(result, expected_hours)

    def test_fall_dst_transition(self):
        # Fall DST Transition: Clocks go back 1 hour at 03:00 on October 27, 2024
        # This makes the 2 AM to 3 AM period "repeat" an extra hour.
        start_time = self.timezone.localize(dt.datetime(2024, 10, 27, 0, 0, 0))
        end_time = self.timezone.localize(dt.datetime(2024, 10, 27, 4, 0, 0))

        expected_hours = 6  # 4 real hours + 1 additional hour due to DST ending and +1 as end_time is inclusive
        result = DayaheadMarketPrices.expected_length_of_data(start_time, end_time)
        self.assertEqual(result, expected_hours)

    def test_spring_dst_transition(self):
        # Spring DST Transition: Clocks skip forward 1 hour at 02:00 on March 31, 2024
        # This means the hour from 2 AM to 3 AM doesn't "exist".
        start_time = self.timezone.localize(dt.datetime(2024, 3, 31, 0, 0, 0))
        end_time = self.timezone.localize(dt.datetime(2024, 3, 31, 4, 0, 0))

        expected_hours = 4  # Only 3 real hours exist, but +1 as end_time is inclusive
        result = DayaheadMarketPrices.expected_length_of_data(start_time, end_time)
        self.assertEqual(result, expected_hours)

    def test_same_time(self):
        # Edge case: Start and end time are the same
        start_time = self.timezone.localize(dt.datetime(2024, 10, 10, 1, 0, 0))
        end_time = self.timezone.localize(dt.datetime(2024, 10, 10, 1, 0, 0))

        expected_hours = 1  # 0 hours, but +1 as end_time is inclusive
        result = DayaheadMarketPrices.expected_length_of_data(start_time, end_time)
        self.assertEqual(result, expected_hours)

    def test_across_days(self):
        # Case: Across two days with no DST involved
        start_time = self.timezone.localize(dt.datetime(2024, 10, 10, 23, 0, 0))
        end_time = self.timezone.localize(dt.datetime(2024, 10, 11, 3, 0, 0))

        expected_hours = 5  # 4 hours, but +1 as end_time is inclusive
        result = DayaheadMarketPrices.expected_length_of_data(start_time, end_time)
        self.assertEqual(result, expected_hours)


if __name__ == '__main__':
    unittest.main()
