import datetime as dt
import os

import pandas as pd
from requests.exceptions import ConnectionError, HTTPError
import streamlit as st
from entsoe import entsoe, EntsoePandasClient
from ortools.linear_solver import pywraplp

from menu import GIGA_HOME_PAGE, REPOSITORY_HOME_PAGE, menu, ENTSOE_GITHUB_HOME_PAGE
from model import PriceScheduleDataFrame, add_power_schedules_to_solver, add_maximize_revenue, \
    add_capacity_and_cycles_to_solver
from visualizer import plot_power_schedule_capacity_and_prices

# Copyright 2024 GIGA Storage B.V.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

ENTSOE_API_KEY = os.environ["ENTSOE_API_KEY"]

st.set_page_config(
    page_title="Battery Trading Benchmark",
    page_icon=':battery:'
)

menu()
st.write(f"""
# Battery Trading Benchmark
The Battery Trading Benchmark is an an open source tool developed to benchmark the value of a
 Energy Storage System (ESS) on the Dutch electricity markets.
It aims to be the market standard in evaluating an ESS system on different energy markets.

Feel free to read additional documentation on the methodology of this benchmark under the
 [description](/description) section.
This version calculates the **mathematical optimum** an ESS can earn on a **single** market.

This tool is maintained by [GIGA Storage]({GIGA_HOME_PAGE}), but we invite every one to collaborate with us in
 our [open-source community]({REPOSITORY_HOME_PAGE}) under the Apache License 2.0.
Market data is retrieved from the [ENTSO-E Transparency Platform]({ENTSOE_GITHUB_HOME_PAGE}).

## Define your BESS
""")

# ---------- USER INPUT ----------
# 1. Define the limits of your BESS
col1, col2, col3, col4 = st.columns(4)
with col1:
    max_power_kw = st.number_input("BESS Power (kW)", min_value=1, value=1000, step=100)
    allowed_cycles = st.number_input("Allowed Cycles", min_value=0.0, value=1.5)
with col2:
    max_battery_capacity_kwh = st.number_input("BESS Capacity (kWh)", min_value=1, value=2000, step=100)
with col3:
    charge_efficiency = st.number_input("Charge Efficiency (%)", 0, 100, value=93)
    charge_efficiency = charge_efficiency / 100
    discharge_efficiency = st.number_input("Discharge Efficiency (%)", 0, 100, value=93)
    discharge_efficiency = discharge_efficiency / 100
with col4:
    initial_battery_capacity_kwh = st.number_input(
        "Initial BESS Capacity (kWh)",
        0,
        max_battery_capacity_kwh,
        value=int(0.5 * max_battery_capacity_kwh),
        step=100,
    )
    final_battery_capacity_kwh = st.number_input(
        "Final BESS Capacity (kWh)",
        0,
        max_battery_capacity_kwh,
        value=initial_battery_capacity_kwh,
        step=100,
    )
min_battery_capacity_kwh = 0

# 2. Define the Entsoe Area
entsoe_area = entsoe.Area['NL']

# 3. Define the pandas Timestamps the prices will be taken of
st.write(f"## Choose your date")
default_date = dt.date.today() - dt.timedelta(days=5)
user_start_date_input = st.date_input("Date", value=default_date)
start = pd.Timestamp(user_start_date_input.strftime("%Y%m%d"), tz=entsoe_area.tz)

user_end_date_input = st.date_input("End date (non-inclusive)", value=default_date + dt.timedelta(days=1))
end_of_day_on_dayahead = dt.datetime.combine(user_end_date_input - dt.timedelta(days=1), dt.time(23, 0))
end = pd.Timestamp(end_of_day_on_dayahead.strftime('%Y%m%d%H%M'), tz=entsoe_area.tz)  # end is inclusive

# ---------- LOAD MARKET DATA ----------
if ENTSOE_API_KEY is None:
    raise RuntimeError("The required environment variable ENTSOE_API_KEY is not set.")
client = EntsoePandasClient(api_key=ENTSOE_API_KEY)

try:
    entsoe_dayahead_prices = client.query_day_ahead_prices(entsoe_area.name, start=start, end=end)
    # Convert the EntsoePandasClient result into a PriceScheduleDataFrame
    dayahead_price_schedule = pd.DataFrame(entsoe_dayahead_prices.rename('charge_price'))
    dayahead_price_schedule['discharge_price'] = entsoe_dayahead_prices
    PriceScheduleDataFrame.validate(dayahead_price_schedule)
    flag_no_dayahead_data = False
except (entsoe.NoMatchingDataError, ConnectionError, HTTPError):
    dayahead_price_schedule = pd.DataFrame()
    flag_no_dayahead_data = True
# The assumed length of the dayahead market is 1 hour
dayahead_length_of_timestep_hour = 1

try:
    imbalance_end_datetime = end_of_day_on_dayahead.replace(minute=45)
    imbalance_end_timestamp = pd.Timestamp(imbalance_end_datetime.strftime('%Y%m%d%H%M'), tz=entsoe_area.tz)
    entsoe_imbalance_prices = client.query_imbalance_prices(entsoe_area.name, start=start, end=end)
    imbalance_price_schedule = entsoe_imbalance_prices.rename({
        'Short': 'charge_price',
        'Long': 'discharge_price',
    }, axis=1)
    PriceScheduleDataFrame.validate(imbalance_price_schedule)
    flag_no_imbalance_data = False
except (entsoe.NoMatchingDataError, ConnectionError, HTTPError):
    imbalance_price_schedule = pd.DataFrame()
    flag_no_imbalance_data = True

# ---------- METADATA OF BENCHMARK ----------
round_trip_efficiency = charge_efficiency * discharge_efficiency * 100
country_name = entsoe_area.meaning.split(',')[0]
if len(dayahead_price_schedule) > 25:
    date_in_title = f"{start.strftime('%d-%m-%Y')} - {user_end_date_input.strftime('%d-%m-%Y')}"
else:
    date_in_title = start.strftime('%d-%m-%Y')
power_text = f"{max_power_kw / 1000:,.1f} MW" if max_power_kw >= 1000 else f"{max_power_kw:,.0f} kW"
if max_battery_capacity_kwh >= 1000:
    capacity_text = f"{max_battery_capacity_kwh / 1000:,.1f} MWh"
else:
    capacity_text = f"{max_battery_capacity_kwh:,.0f} kWh"

# ---------- ADDITIONAL VARIABLES USED IN PLOTS ----------
if not flag_no_dayahead_data:
    dayahead_x_axis = dayahead_price_schedule.index.tolist()
if not flag_no_imbalance_data:
    imbalance_x_axis = imbalance_price_schedule.index.tolist()

# ---------- DAYAHEAD MARKET ----------
if not flag_no_dayahead_data:
    solver = pywraplp.Solver(
        'DAYAHEAD MARKET',
        pywraplp.Solver.GLOP_LINEAR_PROGRAMMING
    )
    charge_power, discharge_power = add_power_schedules_to_solver(
        solver=solver,
        schedule_length=len(dayahead_price_schedule),
        max_power_kw=max_power_kw,
    )
    capacity, cycles = add_capacity_and_cycles_to_solver(
        solver=solver,
        charge_power=charge_power,
        discharge_power=discharge_power,
        min_battery_capacity_kwh=min_battery_capacity_kwh,
        max_battery_capacity_kwh=max_battery_capacity_kwh,
        initial_battery_capacity_kwh=initial_battery_capacity_kwh,
        final_battery_capacity_kwh=final_battery_capacity_kwh,
        length_of_timestep_hour=dayahead_length_of_timestep_hour,
        charge_efficiency=charge_efficiency,
        discharge_efficiency=discharge_efficiency,
        allowed_cycles=allowed_cycles
    )
    add_maximize_revenue(
        solver=solver,
        price_schedule_df=dayahead_price_schedule,
        length_of_timestep_hour=dayahead_length_of_timestep_hour,
        charge_schedule=charge_power,
        discharge_schedule=discharge_power,
    )

    # Solve problem
    status = solver.Solve()

    # If an optimal solution has been found, print results
    if status == pywraplp.Solver.OPTIMAL:
        # Retrieve metadata from the optimisation
        dayahead_revenue = solver.Objective().Value()
        optimiser_time = solver.wall_time()
        optimiser_iterations = solver.iterations()

        # Parse the results into lists
        dayahead_revenue = solver.Objective().Value()
        dayahead_revenue = f"{dayahead_revenue:,.2f}"
        optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
        optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
        optimal_capacity = [capacity[i].solution_value() for i in range(0, len(capacity))]
        optimal_cycles = [cycles[i].solution_value() for i in range(0, len(cycles))]
        average_state_of_charge = sum(optimal_capacity) / len(optimal_capacity)
        average_state_of_charge_perc = average_state_of_charge / max_battery_capacity_kwh * 100

        title = f"Battery Trading Benchmark - Dayahead {date_in_title} {country_name}\n" \
                f"{power_text}|{capacity_text}, {optimal_cycles[-1]:.2f} Cycles\n" \
                f"Revenue: €{dayahead_revenue}\n" \
                f"Solved in {optimiser_time:.0f} ms in {optimiser_iterations} iterations"
        dayahead_figure = plot_power_schedule_capacity_and_prices(
            price_schedule_df=dayahead_price_schedule,
            x_axis=dayahead_x_axis,
            charge_schedule=optimal_charge_power,
            discharge_schedule=optimal_discharge_power,
            capacity=optimal_capacity,
            title=title
        )
    else:
        print('The solver could not find an optimal solution.')
else:
    dayahead_revenue = "Error during dayahead market data processing"


# ---------- IMBALANCE MARKET ----------
if not flag_no_imbalance_data:
    solver = pywraplp.Solver(
        'IMBALANCE MARKET',
        pywraplp.Solver.GLOP_LINEAR_PROGRAMMING
    )
    charge_power, discharge_power = add_power_schedules_to_solver(
        solver=solver,
        schedule_length=len(imbalance_price_schedule),
        max_power_kw=max_power_kw,
    )
    capacity, cycles = add_capacity_and_cycles_to_solver(
        solver=solver,
        charge_power=charge_power,
        discharge_power=discharge_power,
        min_battery_capacity_kwh=min_battery_capacity_kwh,
        max_battery_capacity_kwh=max_battery_capacity_kwh,
        initial_battery_capacity_kwh=initial_battery_capacity_kwh,
        final_battery_capacity_kwh=final_battery_capacity_kwh,
        length_of_timestep_hour=0.25,
        charge_efficiency=charge_efficiency,
        discharge_efficiency=discharge_efficiency,
        allowed_cycles=allowed_cycles
    )
    add_maximize_revenue(
        solver=solver,
        price_schedule_df=imbalance_price_schedule,
        length_of_timestep_hour=0.25,
        charge_schedule=charge_power,
        discharge_schedule=discharge_power,
    )

    # Solve problem
    status = solver.Solve()

    # If an optimal solution has been found, print results
    if status == pywraplp.Solver.OPTIMAL:
        # Retrieve metadata from the optimisation
        imbalance_revenue = solver.Objective().Value()
        optimiser_time = solver.wall_time()
        optimiser_iterations = solver.iterations()

        # Parse the results into lists
        imbalance_revenue = solver.Objective().Value()
        imbalance_revenue = f"{imbalance_revenue:,.2f}"
        optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
        optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
        optimal_capacity = [capacity[i].solution_value() for i in range(0, len(capacity))]
        optimal_cycles = [cycles[i].solution_value() for i in range(0, len(cycles))]
        average_state_of_charge = sum(optimal_capacity) / len(optimal_capacity)
        average_state_of_charge_perc = average_state_of_charge / max_battery_capacity_kwh * 100

        title = f"Battery Trading Benchmark - Imbalance {date_in_title} {country_name}\n" \
                f"{power_text}|{capacity_text}, {optimal_cycles[-1]:.2f} Cycles\n" \
                f"Revenue: €{imbalance_revenue}\n" \
                f"Solved in {optimiser_time:.0f} ms in {optimiser_iterations} iterations"
        imbalance_figure = plot_power_schedule_capacity_and_prices(
            price_schedule_df=imbalance_price_schedule,
            x_axis=imbalance_x_axis,
            charge_schedule=optimal_charge_power,
            discharge_schedule=optimal_discharge_power,
            capacity=optimal_capacity,
            title=title
        )
    else:
        print('The solver could not find an optimal solution.')
else:
    imbalance_revenue = "No Imbalance Market Data"

st.write(f"""
## Battery Trading Benchmark {date_in_title}
The Battery Trading Benchmark calculates the **mathematical optimum** of a
 {power_text}|{capacity_text} system dispatched on a **single** energy market.
These results are theoretical calculations and are not based on real battery trading.

| Energy Market | Revenue                	|
|---	        |---	                    |
| Dayahead 	    | {dayahead_revenue} 	    |
| Imbalance     | {imbalance_revenue} 	    |
| ... 	        |  	                        |
""")

st.write(f"""
## Parameters
| **Parameter**                	| **Unit** 	| **Description**                                                          |
|------------------------------	|----------	|------------------------------------------------------------------------- |
| max_power_kw                 	| kW       	| The maximum power output of your BESS, in kW                             |
| max_battery_capacity_kwh     	| kWh      	| The maximum stored capacity in your BESS, in kWh                         |
| allowed_cycles 	| # 	| The number of times your BESS is allowed to charge and discharge between 0% and 100% SoC |
| charge_efficiency            	| %        	| The percentage of capacity that is stored when charging                  |
| discharge_efficiency         	| %        	| The percentage of capacity that is released when discharging             |
| initial_battery_capacity_kwh 	| kWh      	| The initial capacity of the BESS at the start of the simulation          |
| final_battery_capacity_kwh   	| kWh      	| The final capacity of the BESS at the end of the simulation              |
""")

st.write(f"""
## Dayahead
""")
if flag_no_dayahead_data:
    st.write(dayahead_revenue)
else:
    st.pyplot(dayahead_figure)

st.write(f"""
## Imbalance
""")
if flag_no_imbalance_data:
    st.write(imbalance_revenue)
else:
    st.pyplot(imbalance_figure)
