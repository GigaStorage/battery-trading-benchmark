import datetime as dt
from typing import Optional

import pandas as pd
import pytz
from entsoe import EntsoePandasClient, Area

from model import PriceScheduleDataFrame

DAYAHEAD_PRICE_SCHEDULE_FILE = "market_data/data/dayahead_data.pkl"


def update_hot_load(dayahead_price_schedule: PriceScheduleDataFrame, file_name: Optional[str] = None):
    # TODO read the existing hot load and add it, for now just overwrite
    if file_name is None:
        file_name = DAYAHEAD_PRICE_SCHEDULE_FILE
    dayahead_price_schedule.to_pickle(file_name)


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
    local_tz = pytz.timezone(entsoe_area.tz)
    if start_time.tzinfo is None:
        start_time = local_tz.localize(start_time)
    if end_time.tzinfo is None:
        end_time = local_tz.localize(end_time)
    start_time = start_time.astimezone(local_tz)
    end_time = end_time.astimezone(local_tz)

    # The EntsoePandasClient takes pd.Timestamps
    start = pd.Timestamp(start_time.strftime("%Y%m%d%H%M"), tz=entsoe_area.tz)
    end = pd.Timestamp(end_time.strftime('%Y%m%d%H%M'), tz=entsoe_area.tz)  # end is inclusive

    entsoe_dayahead_prices = client.query_day_ahead_prices(country_code=entsoe_area.code, start=start, end=end)

    # Convert the EntsoePandasClient result into a PriceScheduleDataFrame
    dayahead_price_schedule = pd.DataFrame(entsoe_dayahead_prices.rename('charge_price'))
    dayahead_price_schedule['discharge_price'] = entsoe_dayahead_prices

    PriceScheduleDataFrame.validate(dayahead_price_schedule)

    if store_in_hot_load:
        update_hot_load(dayahead_price_schedule)

    return dayahead_price_schedule
