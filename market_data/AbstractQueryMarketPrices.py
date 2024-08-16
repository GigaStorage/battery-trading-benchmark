import datetime as dt

import abc
from abc import ABC
from typing import Optional

import pandas as pd
import pytz
from entsoe import entsoe, Area, EntsoePandasClient

from model import PriceScheduleDataFrame


class AbstractQueryMarketPrices(ABC):
    DEFAULT_FILE_NAME = None

    @classmethod
    def update_hot_load(cls, market_data: PriceScheduleDataFrame, file_name: Optional[str] = None):
        """
        update_hot_load will take the dayahead_price_schedule and use it to update the current information in the pkl
        :param market_data: A PriceScheduleDataFrame with new information
        :param file_name: A string file_name where the pkl is stored
        """
        if file_name is None and cls.DEFAULT_FILE_NAME is not None:
            file_name = cls.DEFAULT_FILE_NAME

        try:
            total_schedule = pd.read_pickle(file_name)
        except FileNotFoundError:
            market_data.to_pickle(file_name)
            return

        res = total_schedule.combine_first(market_data)
        res.to_pickle(file_name)

    @classmethod
    def verify_start_and_end_time(cls, start_time: dt.datetime, end_time: dt.datetime,
                                  entsoe_area: entsoe.Area) -> tuple[dt.datetime, dt.datetime]:
        """
        This method will verify and align the timezone of the start_time and end_time with the entsoe_area
        :param start_time: datetime specifying the start_time
        :param end_time: datetime specifying the end_time
        :param entsoe_area: entsoe.Area ENUM, containing a (country)code and a tz
        :return: timezone aware tuple (start_time, end_time)
        """
        area_tz = pytz.timezone(entsoe_area.tz)

        if start_time.tzinfo is None:
            start_time = area_tz.localize(start_time)
        start_time = start_time.astimezone(area_tz)

        if end_time.tzinfo is None:
            end_time = area_tz.localize(end_time)
        end_time = end_time.astimezone(area_tz)

        return start_time, end_time

    @classmethod
    @abc.abstractmethod
    def cold_load_data(cls, start_time: dt.datetime, end_time: dt.datetime, client: EntsoePandasClient,
                       store_in_hot_load: bool, entsoe_area: Area = Area['NL']) -> PriceScheduleDataFrame:
        """
        Load the market_data from entsoe_area from start_time until (and including) end_time using the entsoe.client
        :param start_time: datetime specifying the start_time
        :param end_time: datetime specifying the end_time (inclusive)
        :param client: EntsoePandasClient, the query_day_ahead_prices method is used
        :param store_in_hot_load: bool, specifying if the created DataFrame should be stored in a hot_load
        :param entsoe_area: entsoe.Area ENUM, containing a (country)code and a tz
        :return: A PriceScheduleDataFrame from start_time until (and including) end_time

        :raises entsoe.NoMatchingDataError, ConnectionError, HTTPError, if there is an error retrieving data
        """
        pass

    @classmethod
    @abc.abstractmethod
    def hot_load_data(cls, start_time: dt.datetime, end_time: dt.datetime,
                      allow_cold_load: bool, entsoe_area: Area = Area['NL'],
                      file_name: Optional[str] = None,
                      client: Optional[EntsoePandasClient] = None) -> PriceScheduleDataFrame:
        """
        Load the market_data from entsoe_area from start_time until (and including) end_time using a stored pkl file

        :param start_time: datetime specifying the start_time
        :param end_time: datetime specifying the end_time (inclusive)
        :param allow_cold_load: boolean specifying if the cold_load is allowed to be used
        :param entsoe_area: entsoe.Area ENUM, containing a (country)code and a tz
        :param file_name: string specifying the filename of the pkl file which has stored the hot load
        :param client: EntsoePandasClient that can be used if the cold_load is allowed
        :return: A PriceScheduleDataFrame from start_time until (and including) end_time

        :raises entsoe.NoMatchingDataError, ConnectionError, HTTPError, if there is an error retrieving data
        """
        pass
