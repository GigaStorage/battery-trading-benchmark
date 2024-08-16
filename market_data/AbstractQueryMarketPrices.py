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
                                  entsoe_area: entsoe.Area,
                                  assume_naive_timezones: bool = True) -> tuple[dt.datetime, dt.datetime]:
        """
        This method will verify and align the timezone of the start_time and end_time with the entsoe_area

        :param start_time: datetime specifying the start_time
        :param end_time: datetime specifying the end_time
        :param entsoe_area: entsoe.Area ENUM, containing a (country)code and a tz
        :param assume_naive_timezones: boolean specifying if the method is allowed to assume_naive_timezones

        :return: timezone aware tuple (start_time, end_time)

        :raises TypeError: If naive datetime objects are passed and assume_naive_timezones is False
        """
        area_tz = pytz.timezone(entsoe_area.tz)

        if start_time.tzinfo is None:
            if not assume_naive_timezones:
                raise TypeError("start_time must be timezone aware")
            start_time = area_tz.localize(start_time)
        start_time = start_time.astimezone(area_tz)

        if end_time.tzinfo is None:
            if not assume_naive_timezones:
                raise TypeError("end_time must be timezone aware")
            end_time = area_tz.localize(end_time)
        end_time = end_time.astimezone(area_tz)

        return start_time, end_time

    @classmethod
    def convert_to_timezoned_pandas_object(cls, start_time: dt.datetime, end_time: dt.datetime,
                                           entsoe_area: entsoe.Area,
                                           assume_naive_timezones: bool = True) -> tuple[pd.Timestamp, pd.Timestamp]:
        """
        This method will verify and align the timezone of the start_time and end_time with the entsoe_area, and then
          convert the Python datetime objects to a timezoned pandas object for entsoe

        :param start_time: datetime specifying the start_time
        :param end_time: datetime specifying the end_time
        :param entsoe_area: entsoe.Area ENUM, containing a (country)code and a tz
        :param assume_naive_timezones: boolean specifying if the method is allowed to assume_naive_timezones

        :return: timezone aware tuple (start_time, end_time)
        """
        start_time, end_time = cls.verify_start_and_end_time(
            start_time=start_time,
            end_time=end_time,
            entsoe_area=entsoe_area,
            assume_naive_timezones=assume_naive_timezones,
        )

        start_pd = pd.Timestamp(start_time.strftime("%Y%m%d%H%M"), tz=entsoe_area.tz)
        end_pd = pd.Timestamp(end_time.strftime('%Y%m%d%H%M'), tz=entsoe_area.tz)

        return start_pd, end_pd

    @classmethod
    @abc.abstractmethod
    def expected_length_of_data(cls, start_time: dt.datetime, end_time: dt.datetime):
        pass

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
                      client: Optional[EntsoePandasClient] = None,
                      assume_naive_timezones: bool = True) -> PriceScheduleDataFrame:
        """
        Load the market_data from entsoe_area from start_time until (and including) end_time using a stored pkl file

        :param start_time: datetime specifying the start_time
        :param end_time: datetime specifying the end_time (inclusive)
        :param allow_cold_load: boolean specifying if the cold_load is allowed to be used
        :param entsoe_area: entsoe.Area ENUM, containing a (country)code and a tz
        :param file_name: string specifying the filename of the pkl file which has stored the hot load
        :param client: EntsoePandasClient that can be used if the cold_load is allowed
        :param assume_naive_timezones: boolean specifying if the method is allowed to assume_naive_timezones

        :return: A PriceScheduleDataFrame from start_time until (and including) end_time

        :raises entsoe.NoMatchingDataError, ConnectionError, HTTPError, if there is an error retrieving data
        :raises TypeError: If naive datetime objects are passed and assume_naive_timezones is False
        """
        # Verify the timezone of the passed datetimes
        start_time, end_time = cls.verify_start_and_end_time(start_time, end_time, entsoe_area, assume_naive_timezones)

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
                    entsoe_area=entsoe_area,
                )
            else:
                raise ValueError("Data that you requested has not been cold_loaded.")

        res_schedule = total_schedule[start_time:end_time]

        expected_length_of_data = cls.expected_length_of_data(start_time, end_time)
        # Happy flow, the data is found, return it
        if len(res_schedule) == expected_length_of_data:
            return res_schedule

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
        raise ValueError("Data that you requested has not been cold_loaded.")
