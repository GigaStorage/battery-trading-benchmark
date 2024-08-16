import datetime as dt
from typing import Optional

import pandas as pd
from entsoe import Area, EntsoePandasClient

from market_data.AbstractQueryMarketPrices import AbstractQueryMarketPrices
from model import PriceScheduleDataFrame


class DayaheadMarketPrices(AbstractQueryMarketPrices):
    DEFAULT_FILE_NAME = "market_data/data/dayahead_data.pkl"

    @classmethod
    def cold_load_data(cls, start_time: dt.datetime, end_time: dt.datetime, client: EntsoePandasClient,
                       store_in_hot_load: bool, entsoe_area: Area = Area['NL']) -> PriceScheduleDataFrame:
        if client is None:
            raise ConnectionError("No entsoe.EntsoePandasClient was passed so no connection could be made.")

        # Verify the timezone of the passed datetimes
        start_pd, end_pd = cls.convert_to_timezoned_pandas_object(start_time, end_time, entsoe_area)

        entsoe_dayahead_prices = client.query_day_ahead_prices(
            country_code=entsoe_area.code,
            start=start_pd,
            end=end_pd
        )

        # Convert the EntsoePandasClient result into a PriceScheduleDataFrame
        dayahead_price_schedule = pd.DataFrame(entsoe_dayahead_prices.rename('charge_price'))
        dayahead_price_schedule['discharge_price'] = entsoe_dayahead_prices

        PriceScheduleDataFrame.validate(dayahead_price_schedule)

        if store_in_hot_load:
            cls.update_hot_load(dayahead_price_schedule)

        return dayahead_price_schedule

    @classmethod
    def hot_load_data(cls, start_time: dt.datetime, end_time: dt.datetime, allow_cold_load: bool,
                      entsoe_area: Area = Area['NL'], file_name: Optional[str] = None,
                      client: Optional[EntsoePandasClient] = None) -> PriceScheduleDataFrame:
        # Verify the timezone of the passed datetimes
        start_time, end_time = cls.verify_start_and_end_time(start_time, end_time, entsoe_area)

        try:
            if file_name is None:
                file_name = cls.DEFAULT_FILE_NAME
            total_schedule = pd.read_pickle(file_name)
        except FileNotFoundError:
            if allow_cold_load:
                return cls.cold_load_data(
                    start_time=start_time,
                    end_time=end_time,
                    client=client,
                    store_in_hot_load=True,
                    entsoe_area=entsoe_area
                )
            else:
                raise ValueError("You requested too much data that is not cached yet. "
                                 "Please request smaller intervals, "
                                 "each call will be cached individually, then try again later.")

        dayahead_price_schedule = total_schedule[start_time:end_time]

        expected_length_of_data = int((end_time - start_time).total_seconds() / 60 / 60) + 1
        # Happy flow, the data is found, return it
        if len(dayahead_price_schedule) == expected_length_of_data:
            return dayahead_price_schedule

        # Unhappy flow, no (or insufficient) data was found, check if we can cold_load
        if allow_cold_load:
            return cls.cold_load_data(
                start_time=start_time,
                end_time=end_time,
                client=client,
                store_in_hot_load=True,
                entsoe_area=entsoe_area
            )
        # If no cold_load is allowed, we raise a ValueError
        raise ValueError("You requested too much data that is not cached yet. Please request smaller intervals, "
                         "each call will be cached individually, then try again later.")
