import datetime as dt
from typing import Optional

import entsoe
import pandas as pd
import pytz
from entsoe import EntsoePandasClient, Area

from model import PriceScheduleDataFrame

DAYAHEAD_PRICE_SCHEDULE_FILE = "market_data/data/dayahead_data.pkl"


def update_hot_load(dayahead_price_schedule: PriceScheduleDataFrame, file_name: Optional[str] = None):
    """
    update_hot_load will take the dayahead_price_schedule and use it to update the current information in the pkl
    :param dayahead_price_schedule: A PriceScheduleDataFrame with new information
    :param file_name: A string file_name where the pkl is stored
    """
    if file_name is None:
        file_name = DAYAHEAD_PRICE_SCHEDULE_FILE

    try:
        total_schedule = pd.read_pickle(file_name)
    except FileNotFoundError:
        dayahead_price_schedule.to_pickle(file_name)
        return

    res = total_schedule.combine_first(dayahead_price_schedule)
    res.to_pickle(file_name)


def cold_load_dayahead_data(start_time: dt.datetime, end_time: dt.datetime, client: EntsoePandasClient,
                            store_in_hot_load: bool, entsoe_area: Area = Area['NL']) -> PriceScheduleDataFrame:
    """
    Load the dayahead_data from entsoe_area from start_time until (and including) end_time using the entsoe.client
    :param start_time: datetime specifying the start_time
    :param end_time: datetime specifying the end_time (inclusive)
    :param client: EntsoePandasClient, the query_day_ahead_prices method is used
    :param store_in_hot_load: bool, specifying if the created DataFrame should be stored in a hot_load
    :param entsoe_area: entsoe.Area ENUM, containing a (country)code and a tz
    :return: A PriceScheduleDataFrame from start_time until (and including) end_time

    :raises entsoe.NoMatchingDataError, ConnectionError, HTTPError, if there is an error retrieving data
    """
    # Verify the timezone of the passed datetimes
    start_time, end_time = verify_start_and_end_time(start_time, end_time, entsoe_area)

    # The EntsoePandasClient takes pd.Timestamps
    start = pd.Timestamp(start_time.strftime("%Y%m%d%H%M"), tz=entsoe_area.tz)
    end = pd.Timestamp(end_time.strftime('%Y%m%d%H%M'), tz=entsoe_area.tz)  # end is inclusive

    if client is None:
        raise ConnectionError("No entsoe.EntsoePandasClient was passed so no connection could be made.")
    entsoe_dayahead_prices = client.query_day_ahead_prices(country_code=entsoe_area.code, start=start, end=end)

    # Convert the EntsoePandasClient result into a PriceScheduleDataFrame
    dayahead_price_schedule = pd.DataFrame(entsoe_dayahead_prices.rename('charge_price'))
    dayahead_price_schedule['discharge_price'] = entsoe_dayahead_prices

    PriceScheduleDataFrame.validate(dayahead_price_schedule)

    if store_in_hot_load:
        update_hot_load(dayahead_price_schedule)

    return dayahead_price_schedule


def hot_load_dayahead_data(start_time: dt.datetime, end_time: dt.datetime,
                           allow_cold_load: bool, entsoe_area: Area = Area['NL'],
                           file_name: Optional[str] = None,
                           client: Optional[EntsoePandasClient] = None) -> PriceScheduleDataFrame:
    """
    Load the dayahead_data from entsoe_area from start_time until (and including) end_time using a stored pkl file

    :param start_time: datetime specifying the start_time
    :param end_time: datetime specifying the end_time (inclusive)
    :param entsoe_area: entsoe.Area ENUM, containing a (country)code and a tz
    :return: A PriceScheduleDataFrame from start_time until (and including) end_time

    :raises entsoe.NoMatchingDataError, ConnectionError, HTTPError, if there is an error retrieving data
    """
    # Verify the timezone of the passed datetimes
    start_time, end_time = verify_start_and_end_time(start_time, end_time, entsoe_area)

    try:
        if file_name is None:
            file_name = DAYAHEAD_PRICE_SCHEDULE_FILE
        total_schedule = pd.read_pickle(file_name)
    except FileNotFoundError:
        if allow_cold_load:
            return cold_load_dayahead_data(
                start_time=start_time,
                end_time=end_time,
                client=client,
                store_in_hot_load=True,
                entsoe_area=entsoe_area
            )
        else:
            raise ValueError("No data was found for the requested timestamps.")

    dayahead_price_schedule = total_schedule[start_time:end_time]

    expected_length_of_data = int((start_time - end_time).total_seconds() / 60 / 60)
    # Happy flow, the data is found, return it
    if len(dayahead_price_schedule) == expected_length_of_data:
        return dayahead_price_schedule

    # Unhappy flow, no (or insufficient) data was found, check if we can cold_load
    if allow_cold_load:
        return cold_load_dayahead_data(
            start_time=start_time,
            end_time=end_time,
            client=client,
            store_in_hot_load=True,
            entsoe_area=entsoe_area
        )
    # If no cold_load is allowed, we raise a ValueError
    raise ValueError("No data was found for the requested timestamps.")


def verify_start_and_end_time(start_time: dt.datetime, end_time: dt.datetime,
                              entsoe_area: entsoe.Area) -> tuple[dt.datetime, dt.datetime]:
    """
    This method will verify the timezone of the start_time and end_time object and that they align with the entsoe_area
    :param start_time: datetime specifying the start_time
    :param end_time: datetime specifying the end_time (inclusive)
    :param entsoe_area: entsoe.Area ENUM, containing a (country)code and a tz
    :return: timezone aware tuple (start_time, end_time)
    """
    local_tz = pytz.timezone(entsoe_area.tz)

    if start_time.tzinfo is None:
        start_time = local_tz.localize(start_time)
    start_time = start_time.astimezone(local_tz)

    if end_time.tzinfo is None:
        end_time = local_tz.localize(end_time)
    end_time = end_time.astimezone(local_tz)

    return start_time, end_time
