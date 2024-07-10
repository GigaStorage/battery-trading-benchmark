import datetime as dt
import json
import unittest
from unittest.mock import Mock, patch

import entsoe
import pandas as pd
import pytz

import market_data.read_dayahead_data
from market_data.read_dayahead_data import cold_load_dayahead_data
from model import PriceScheduleDataFrame


class TestReadDayaheadData(unittest.TestCase):

    def setUp(self) -> None:
        # Define the data and datetime index
        data = [10.5, 15.2, 7.8, 22.3]
        datetime_index = pd.to_datetime([
            "2024-07-05 00:00:00+02:00",
            "2024-07-05 01:00:00+02:00",
            "2024-07-05 02:00:00+02:00",
            "2024-07-05 03:00:00+02:00"
        ])
        # Create the Series
        self.example_series = pd.Series(data, index=datetime_index)

    def test_cold_load_dayahead_data_tz_unaware(self):
        start_time = dt.datetime(2024, 7, 10)
        end_time = dt.datetime(2024, 7, 10, 23)
        mock_client = Mock()
        mock_client.query_day_ahead_prices.return_value = self.example_series

        res = cold_load_dayahead_data(
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

        res = cold_load_dayahead_data(
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

        res = cold_load_dayahead_data(
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

    @patch('market_data.read_dayahead_data.update_hot_load')
    def test_cold_load_dayahead_data_tz_aware_other_area_and_hot_load_store(self, mock_update_hot_load):
        start_time = dt.datetime(2024, 7, 9, 22, tzinfo=pytz.utc)
        end_time = dt.datetime(2024, 7, 10, 21, tzinfo=pytz.utc)
        mock_client = Mock()
        mock_client.query_day_ahead_prices.return_value = self.example_series

        res = cold_load_dayahead_data(
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


if __name__ == '__main__':
    unittest.main()
