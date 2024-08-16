import unittest
from unittest.mock import Mock, patch, MagicMock

import pandas as pd

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


if __name__ == '__main__':
    unittest.main()
