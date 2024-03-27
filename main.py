import os

import entsoe
import pandas as pd
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
from ortools.linear_solver import pywraplp

from benchmark import add_power_schedules_to_solver, add_capacity_and_cycles_to_solver, add_maximize_revenue, \
    PriceScheduleDataFrame

# Copyright 2023 GIGA Storage B.V.
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

load_dotenv()  # take environment variables from .env.
ENTSOE_API_KEY = os.getenv("ENTSOE_API_KEY")

if __name__ == '__main__':
    # ---------- USER INPUT ----------
    # 1. Define the limits of your ESS
    max_power_kw = 1000
    max_battery_capacity_kwh = 2000
    allowed_cycles = 1.5
    charge_efficiency = 0.93
    discharge_efficiency = 0.93
    initial_battery_capacity_kwh = 1000
    final_battery_capacity_kwh = 1000
    min_battery_capacity_kwh = 0
    # 2. Define the Entsoe Area
    entsoe_area = entsoe.Area['NL']
    # 3. Define the pandas Timestamps the prices will be taken of
    start = pd.Timestamp('20230808', tz=entsoe_area.tz)
    end = pd.Timestamp('202308082300', tz=entsoe_area.tz)  # end is inclusive

    # ---------- LOAD MARKET DATA ----------
    if ENTSOE_API_KEY is None:
        raise RuntimeError("The required environment variable ENTSOE_API_KEY is not set.")
    client = EntsoePandasClient(api_key=ENTSOE_API_KEY)
    entsoe_dayahead_prices = client.query_day_ahead_prices(entsoe_area.name, start=start, end=end)
    # Convert the EntsoePandasClient result into a PriceScheduleDataFrame
    price_schedule_df = pd.DataFrame(entsoe_dayahead_prices.rename('charge_price'))
    price_schedule_df['discharge_price'] = entsoe_dayahead_prices
    PriceScheduleDataFrame.validate(price_schedule_df)
    # The assumed length of the dayahead market is 1 hour
    length_of_timestep_hour = 1

    # ---------- METADATA OF BENCHMARK ----------
    round_trip_efficiency = charge_efficiency * discharge_efficiency * 100
    country_name = entsoe_area.meaning.split(',')[0]
    if len(price_schedule_df) > 25:
        date_in_title = f"{start.strftime('%d-%m-%Y')} - {end.strftime('%d-%m-%Y')}"
    else:
        date_in_title = start.strftime('%d-%m-%Y')

    # ---------- DEFINE SOLVER AND EXECUTE THE BATTERY TRADING BENCHMARK ----------
    solver = pywraplp.Solver('BATTERY TRADING BENCHMARK', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
    charge_power, discharge_power = add_power_schedules_to_solver(
        solver=solver,
        schedule_length=len(price_schedule_df),
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
        length_of_timestep_hour=length_of_timestep_hour,
        charge_efficiency=charge_efficiency,
        discharge_efficiency=discharge_efficiency,
        allowed_cycles=allowed_cycles
    )
    add_maximize_revenue(
        solver=solver,
        price_schedule_df=price_schedule_df,
        length_of_timestep_hour=length_of_timestep_hour,
        charge_schedule=charge_power,
        discharge_schedule=discharge_power,
    )

    # Solve problem
    status = solver.Solve()

    # If an optimal solution has been found, print results
    if status == pywraplp.Solver.OPTIMAL:
        # Retrieve metadata from the optimisation
        optimiser_time = solver.wall_time()
        optimiser_iterations = solver.iterations()

        # Parse the results into lists or values
        optimal_revenue = solver.Objective().Value()
        optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
        optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
        optimal_capacity = [capacity[i].solution_value() for i in range(0, len(capacity))]
        optimal_cycles = [cycles[i].solution_value() for i in range(0, len(cycles))]
        average_state_of_charge = sum(optimal_capacity) / len(optimal_capacity)
        average_state_of_charge_perc = average_state_of_charge / max_battery_capacity_kwh * 100

        title = f"Battery Trading Benchmark - Dayahead {date_in_title} {country_name}\n" \
                f"Maximize revenue\n" \
                f"Average State of Charge:\t{average_state_of_charge_perc:,.2f}%\n" \
                f"Cycles:\t{optimal_cycles[-1]:.2f}\n" \
                f"Round Trip Efficiency:\t{round_trip_efficiency:.0f}%\n" \
                f"Revenue: €{optimal_revenue:,.2f}\n" \
                f"Solved in {optimiser_time:.0f} ms in {optimiser_iterations} iterations"
        print(title)
    else:
        print('The solver could not find an optimal solution.')
