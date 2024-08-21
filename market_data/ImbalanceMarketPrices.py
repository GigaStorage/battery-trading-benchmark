import datetime as dt
from typing import Optional

import pandas as pd
from entsoe import Area, EntsoePandasClient

from market_data.AbstractQueryMarketPrices import AbstractQueryMarketPrices
from model import PriceScheduleDataFrame


class ImbalanceMarketPrices(AbstractQueryMarketPrices):
    DEFAULT_FILE_NAME = "market_data/data/imbalance_data.pkl"

    @classmethod
    def cold_load_data(cls, start_time: dt.datetime, end_time: dt.datetime, client: EntsoePandasClient,
                       store_in_hot_load: bool, entsoe_area: Area = Area['NL']) -> PriceScheduleDataFrame:
        if client is None:
            raise ConnectionError("No entsoe.EntsoePandasClient was passed so no connection could be made.")

        # Verify the timezone of the passed datetimes
        start_pd, end_pd = cls.convert_to_timezoned_pandas_object(start_time, end_time, entsoe_area)

        entsoe_imbalance_prices = client.query_imbalance_prices(
            country_code=entsoe_area.code,
            start=start_pd,
            end=end_pd
        )

        # Convert the EntsoePandasClient result into a PriceScheduleDataFrame
        imbalance_price_schedule = entsoe_imbalance_prices.rename({
            'Short': 'charge_price',
            'Long': 'discharge_price',
        }, axis=1)
        PriceScheduleDataFrame.validate(imbalance_price_schedule)

        if store_in_hot_load:
            cls.update_hot_load(imbalance_price_schedule)

        return imbalance_price_schedule

    @classmethod
    def expected_length_of_data(cls, start_time: dt.datetime, end_time: dt.datetime):
        return int((end_time - start_time).total_seconds() / 60 / 15) + 1
