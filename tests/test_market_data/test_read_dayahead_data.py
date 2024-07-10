import datetime as dt
import unittest
from unittest.mock import Mock, patch, MagicMock

import entsoe
import pandas
import pandas as pd
import pytz

from market_data.read_dayahead_data import cold_load_dayahead_data, update_hot_load, hot_load_dayahead_data
from model import PriceScheduleDataFrame


class TestReadDayaheadData(unittest.TestCase):

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

    @patch('pandas.read_pickle')
    def test_very_first_update_hot_load(self, mock_read_pickle):
        mock_read_pickle.side_effect = FileNotFoundError()
        mock_to_pickle = Mock()
        self.example_df.to_pickle = mock_to_pickle()
        update_hot_load(self.example_df, file_name="test_market_data/dayahead_data.pkl")
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

        update_hot_load(overwrite_df, file_name="test_market_data/dayahead_data.pkl")

        mocked_res_df.to_pickle.assert_called_with("test_market_data/dayahead_data.pkl")

    def test_update_hot_load(self):
        update_hot_load(self.example_df, file_name="test_market_data/dayahead_data.pkl")

        start_time = dt.datetime(2024, 7, 5)
        end_time = dt.datetime(2024, 7, 5, 2)
        mock_client = Mock()
        mock_client.query_day_ahead_prices.return_value = self.example_series
        res = hot_load_dayahead_data(
            start_time=start_time,
            end_time=end_time,
            client=mock_client,
            allow_cold_load=False,
            file_name="test_market_data/dayahead_data.pkl"
        )
        print(res)


if __name__ == '__main__':
    unittest.main()
