import datetime as dt

import pandas as pd
from entsoe import EntsoePandasClient, Area

from model import PriceScheduleDataFrame


def cold_load_dayahead_data(start_time: dt.datetime, end_time: dt.datetime, client: EntsoePandasClient,
                            entsoe_area: Area = Area['NL']):
    """
    Load the dayahead_data from entsoe_area from start_time until (and including) end_time using the entsoe.client
    :param start_time: datetime specifying the start_time
    :param end_time: datetime specifying the end_time (inclusive)
    :param client: EntsoePandasClient, the query_day_ahead_prices method is used
    :param entsoe_area: entsoe.Area ENUM, containing a (country)code and a tz
    :return: A PriceScheduleDataFrame from start_time until (and including) end_time

    :raises entsoe.NoMatchingDataError, ConnectionError, HTTPError, if there is an error retrieving data
    """
    # The EntsoePandasClient takes pd.Timestamps
    start = pd.Timestamp(start_time.strftime("%Y%m%d%H%M"), tz=entsoe_area.tz)
    end = pd.Timestamp(end_time.strftime('%Y%m%d%H%M'), tz=entsoe_area.tz)  # end is inclusive

    entsoe_dayahead_prices = client.query_day_ahead_prices(country_code=entsoe_area.code, start=start, end=end)

    # Convert the EntsoePandasClient result into a PriceScheduleDataFrame
    dayahead_price_schedule = pd.DataFrame(entsoe_dayahead_prices.rename('charge_price'))
    dayahead_price_schedule['discharge_price'] = entsoe_dayahead_prices

    PriceScheduleDataFrame.validate(dayahead_price_schedule)
    return dayahead_price_schedule
