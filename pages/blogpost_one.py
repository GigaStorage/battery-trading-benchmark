import datetime as dt

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from entsoe import entsoe, EntsoePandasClient
from ortools.linear_solver import pywraplp

from menu import GIGA_HOME_PAGE, REPOSITORY_HOME_PAGE, menu
from model import PriceScheduleDataFrame, add_power_schedules_to_solver, add_maximize_revenue, \
    add_capacity_and_cycles_to_solver
from visualizer import plot_power_schedule_capacity_and_prices
from main import ENTSOE_API_KEY

st.set_page_config(
    page_title="Blog Post One",
    page_icon=':battery:',
    layout="wide",
)

menu()
st.write(f"""
# Calculating the mathematical optimum of (Battery) Energy Storage System on the Dutch Dayahead market

_Author: Jip Rietveld_
[![Linkedin](https://i.stack.imgur.com/gVE0j.png)](https://www.linkedin.com/in/jip-rietveld-9720/)
[![GitHub](https://i.stack.imgur.com/tskMh.png)](https://github.com/Jipje)
\t - \t_IT Director [GIGA Storage]({GIGA_HOME_PAGE})_
[![Linkedin](https://i.stack.imgur.com/gVE0j.png)](https://www.linkedin.com/company/gigastorage/)
[![GitHub](https://i.stack.imgur.com/tskMh.png)](https://github.com/GigaStorage)

Energy storage plays a crucial role in the energy transition towards a more renewable future.
With the growing focus on renewable energy generation like solar power and wind power, system operators are
 faced with the challenge of ensuring supply and demand are in a constant balance.
Energy storage is a solution to store excess energy when production is high and offer this energy back
 to the market when demand increases.
This allows for a more powerful and resilient energy network.

Aside from the crucial role energy storage plays in the energy transition, energy storage can utilize the energy
 markets to generate revenue.
By utilizing powerful algorithms and strategies, energy storage can make trades and sell their capacity to the
 highest bidder.
They can earn revenue through price arbitrage for example.
Utilizing wholesale markets to buy energy when the price is low, and sell it at a later moment when prices spike.
Or energy storage can sell their flexible capabilities directly to system operators in so-called capacity markets.
These markets are responsible for maintaining the balance of the grid,
 for example by stabilizing frequency on the FCR market.

In the competitive and dynamic environment which the energy market is, it is essential for market participants
 to be able to benchmark and optimize their performance.
A lot of optimisation comes from choosing the right energy market at the right time.
Making use of available assets and market fluctuations.
To challenge the energy community, GIGA Storage strives to develop the Battery Trading Benchmark.
This will be an open-source, advanced optimisation model that can determine the mathematical optimum
 of how a BESS could have been deployed in the energy markets.
This supports market participants to maximize their capture rate in the energy market and realize more BESS projects.

This blogpost is written for anybody interested in (Battery) Energy Storage Systems and how they earn revenue on the
 energy market.
It is part of the open-source repository
 [GigaStorage/battery-trading-benchmark]({REPOSITORY_HOME_PAGE})
 that strives to be the hub for benchmarking how a BESS performs in the current state of the energy market.
In this blogpost, we will deep dive into the first version of this benchmarking tool, and the iterative process taken
 to develop it.
By offering insight into the development of this benchmark, GIGA Storage hopes to contribute to a better understanding
 of how BESS can help the energy transition and what this means for market participants.
As such, this blog post will not deep-dive into the technical details of the developed model.
For follow-up information regarding technical details,
 [feel free to join our open-source community]({REPOSITORY_HOME_PAGE}).

[GIGA Storage]({GIGA_HOME_PAGE}) is a company that develops, realizes and operates
 large-scale Battery Energy Storage Systems (BESS).
""")

st.write("""
### Define your own BESS
This blogpost is written using [Streamlit](https://streamlit.io/).
This means there is Python code running and generating these visuals right now.
As such, you are free to define the limits of your own BESS.
By default, a 2 hour system with 1 MW and 87% Round-Trip Efficiency is configured.
If you are unsure what to configure for the other parameters, feel free to skip this part, and read on.
""")

# ---------- USER INPUT ----------
# 1. Define the limits of your BESS
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1:
    max_power_kw = st.number_input("BESS Power (kW)", min_value=1, value=1000, step=100)
with col2:
    max_battery_capacity_kwh = st.number_input("BESS Capacity (kWh)", min_value=1, value=2000, step=100)
with col3:
    allowed_cycles = st.number_input("Allowed Cycles", 0.0, 1000.0, value=1.5)
with col4:
    charge_efficiency = st.number_input("Charge Efficiency (%)", 0, 100, value=93)
    charge_efficiency = charge_efficiency / 100
with col5:
    discharge_efficiency = st.number_input("Discharge Efficiency (%)", 0, 100, value=93)
    discharge_efficiency = discharge_efficiency / 100
with col6:
    initial_battery_capacity_kwh = st.number_input(
        "Initial BESS Capacity (kWh)",
        0,
        max_battery_capacity_kwh,
        value=int(0.5 * max_battery_capacity_kwh),
        step=100,
    )
with col7:
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
st.write("""
This blogpost utilises the open-source energy market data of the
 [ENTSO-E Transparency Platform](https://github.com/EnergieID/entsoe-py).
As such, you can also choose what day to run this benchmark for.
It is most interesting if you choose a day with negative prices and positive prices.
If you choose a day with only positive prices, try and see if the spread on that day is large.
""")
default_date = dt.date(2023, 8, 8)
day_on_dayahead = st.date_input("Date", value=default_date)
start = pd.Timestamp(day_on_dayahead.strftime("%Y%m%d"), tz=entsoe_area.tz)
end_of_day_on_dayahead = dt.datetime.combine(day_on_dayahead, dt.time(23, 0))
end = pd.Timestamp(end_of_day_on_dayahead.strftime('%Y%m%d%H%M'), tz=entsoe_area.tz)  # end is inclusive

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

# ---------- ADDITIONAL VARIABLES USED IN PLOTS ----------
x_axis = price_schedule_df.index.tolist()

# ---------- FIRST PLOT DAYAHEAD PRICES ----------
fig, ax1 = plt.subplots()
ax1.set_title(f'Dayahead Prices {date_in_title}')
ax1.bar(
    x_axis,
    list(price_schedule_df['charge_price']),
    label=f"Dayahead Prices {country_name}",
    width=0.009,
    alpha=0.75,
    color="black",
)
ax1.set_xlabel('Time (AMS)')
ax1.set_ylabel('Dayahead Prices (€/MWh)')
ax1.tick_params(axis='x', rotation=-45)
col1, col2, col3 = st.columns(3)
with col2:
    st.pyplot(fig)

st.write(f"""
## Version 1. Power (MW) Steering
Revenue is generated on the Dayahead market with a BESS by steering their power (MW).
Depending on what hour the BESS charges or discharges, they will pay, or be paid money to deliver power.
In this benchmark we will assume perfect knowledge of the Dayahead prices on {date_in_title}.
In reality, these prices aren't known when making bids on this market, and are determined by supply and demand.

In the first version of our optimisation, we will only allow power to be steered.
Without diving into the details too much, we will define two schedules to optimise.
A schedule when to charge power, and a schedule when to discharge power.

    solver = pywraplp.Solver('VERSION 1 POWER STEERING', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
    charge_power = [solver.IntVar(0, max_power_kw, f'charge_power_period_i') for i in range(0, schedule_length)]
    discharge_power = [solver.IntVar(0, max_power_kw, f'discharge_power_period_i') for i in range(0, schedule_length)]

However, only offering a schedule isn't sufficient information to perform an optimisation, we must give the model
 something to optimise.
This model will benchmark the revenue a BESS can earn on the energy market, so we add the
 rules for earnings and costs to the optimisation.
Costs are generated when charging the BESS or buying energy.
Of course if the energy price is negative then, these costs will be negative, generating revenue.
Earnings are made by discharging the BESS and selling energy.

    costs = sum(charge_schedule[i] / 1000 * length_of_timestep_hour * charge_prices[i]
                for i in range(0, len(charge_schedule)))
    earnings = sum(discharge_schedule[i] / 1000 * length_of_timestep_hour * discharge_prices[i]
                   for i in range(0, len(discharge_schedule)))
    solver.Maximize(earnings - costs)

With no other limitations or considerations, we expect to want to discharge, or generate energy,
 when the prices are positive.
This allows us to generate revenue by selling this energy on the Dayahead market.
Vice-versa, we expect this model charge, or take away energy, when the prices are negative.
This allows us to generate revenue by buying energy at a premium on the Dayahead market.
""")

# ---------- VERSION 1 ONLY ALLOW POWER STEERING ----------
solver = pywraplp.Solver('VERSION 1 POWER STEERING', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
charge_power, discharge_power = add_power_schedules_to_solver(
    solver=solver,
    schedule_length=len(price_schedule_df),
    max_power_kw=max_power_kw,
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
    optimal_revenue = solver.Objective().Value()
    optimiser_time = solver.wall_time()
    optimiser_iterations = solver.iterations()
    # Parse the results into lists
    optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
    optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
    capacity = [initial_battery_capacity_kwh] * (len(x_axis) + 1)

    title = f"Battery Trading Benchmark - Dayahead {date_in_title} {country_name}\n" \
            f"Maximize revenue by steering power\n" \
            f"Revenue: €{optimal_revenue:,.2f}\n" \
            f"Solved in {optimiser_time:.0f} ms in {optimiser_iterations} iterations"
    fig = plot_power_schedule_capacity_and_prices(
        price_schedule_df=price_schedule_df,
        x_axis=x_axis,
        charge_schedule=optimal_charge_power,
        discharge_schedule=optimal_discharge_power,
        capacity=capacity,
        title=title
    )
    col1, col2, col3 = st.columns(3)
    with col2:
        st.pyplot(fig)

else:
    print('The solver could not find an optimal solution.')

hour_of_system = 1 / (max_power_kw / max_battery_capacity_kwh)
st.write(f"""
It looks like the optimum for steering {max_power_kw:,.0f} kW on the Dayahead market would generate
 €{optimal_revenue:,.2f} revenue!
The visulisations above show how the model optimises the power schedules to discharge energy when prices are high,
 and charge energy when prices are negative.

A BESS is a flexible asset, that can charge and discharge its power quickly.
However it isn't **this** flexible.
In the visualisation above,
 your BESS could be charging or discharging for more than {hour_of_system:,.0f} hours after each other.
In reality, the BESS would be full or empty far earlier than that it could be able to do that.
""")

st.write("""
## Version 2. Track Capacity (MWh) while steering power
A BESS is a flexible and powerful asset, able to charge and discharge energy from the electricity grid.
We saw in the previous version of our benchmark what steering this power could result in on the Dayahead market.
However a BESS is limited by the amount of power it has stored.
Energy must be charged into the system, before it can be discharged.
The capacity stored in the system is called State of Charge, or SoC for short.
When a BESS charges, it becomes more full.
When a BESS discharge, it becomes more empty.

Converting power (kW), to capacity (kWh) is done with the following formula:

    capacity = power * hour

`Y` amount of power delivered for an `X` amount of hours, results in `Y * X` amount of capacity.
This benchmark is built for the Dayahead market, with different energy prices each hour.
As such the amount of hours `X` here is `X=1`.
We add this capacity to our benchmark as follows:

    capacity = [solver.IntVar(min_battery_capacity_kwh, max_battery_capacity_kwh, f'capacity_period_{i}')
                for i in range(0, len(charge_power) + 1)]
    # Capacity constraint ensure capacity follows from previous timestep
    capacity_from_charging = charge_power[i - 1] * length_of_timestep_hour
    capacity_from_discharging = discharge_power[i - 1] * length_of_timestep_hour
    solver.Add(capacity[i] == capacity[i - 1] + capacity_from_charging - capacity_from_discharging)

We use the same optimisation function as before, lets see how much money the model generates now:
""")
# ---------- VERSION 2 ALLOW POWER STEERING, TRACK CAPACITY ----------
solver = pywraplp.Solver('VERSION 2 MAXIMIZE REVENUE, ACCOUNT FOR SoC', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
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
    charge_efficiency=1,  # 100% RTE for now
    discharge_efficiency=1,
    allowed_cycles=1000000,  # No cycles limitations for now
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
    optimal_revenue = solver.Objective().Value()
    optimiser_time = solver.wall_time()
    optimiser_iterations = solver.iterations()

    # Parse the results into lists
    optimal_revenue = solver.Objective().Value()
    optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
    optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
    optimal_capacity = [capacity[i].solution_value() for i in range(0, len(capacity))]
    optimal_cycles = [cycles[i].solution_value() for i in range(0, len(cycles))]
    average_state_of_charge = sum(optimal_capacity) / len(optimal_capacity)
    average_state_of_charge_perc = average_state_of_charge / max_battery_capacity_kwh * 100

    title = f"Battery Trading Benchmark - Dayahead {date_in_title} {country_name}\n" \
            f"Maximize revenue account for State of Charge\n" \
            f"Average State of Charge: {average_state_of_charge_perc:,.2f}% " \
            f"Cycles: {optimal_cycles[-1]:.2f}\n" \
            f"Revenue: €{optimal_revenue:,.2f}\n" \
            f"Solved in {optimiser_time:.0f} ms in {optimiser_iterations} iterations"
    fig = plot_power_schedule_capacity_and_prices(
        price_schedule_df=price_schedule_df,
        x_axis=x_axis,
        charge_schedule=optimal_charge_power,
        discharge_schedule=optimal_discharge_power,
        capacity=optimal_capacity,
        title=title
    )
    col1, col2, col3 = st.columns(3)
    with col2:
        st.pyplot(fig)

else:
    print('The solver could not find an optimal solution.')

st.write(f"""
Taking capacity into consideration changes the result a lot!
It looks like the optimum for steering your {max_power_kw:,.0f} kW BESS on the Dayahead market would generate
 €{optimal_revenue:,.2f} revenue!

The visulisations above show how the model chooses the best hours to charge and discharge,
 all while acting within the SoC limits of {min_battery_capacity_kwh}-{max_battery_capacity_kwh} kWh.
In the previous version, the schedules were free to enjoy any price it could.
This version has to be smarter, and choose just the right moments to maximize its revenue,
 it will let high or negative prices go to earn even more at a later timestep.
This is where the perfect knowledge of the model is at its most powerful.
High prices can be let go for even higher prices at a later moment.

This model is already quite powerful.
However it still has its limitations.
Battery Energy Storage Systems have usage guarantees.
Just like the battery in your phone becomes worse over time, so will an installed BESS.
To track how much you use a BESS, we can calculate the cycles a system has made.
""")

st.write("""
## Version 3. Track Cycles, while steering power and tracking capacity
One cycle is defined as charging the battery from empty, to full, to empty again.
It is important to note that these cycles do not have to be made from 0% SoC to 100% and back again.
Any action in the battery can be calculated as a cycle.
These are calculated using the following formula:

    cycle_in_timestep = abs(capacity_diff_in_timestep) / max_power_kwh

We will add it to our solver as follows:

    battery_cycles = [solver.NumVar(0, allowed_cycles, f'battery_cycles_period_{i}') for i in range(0, len(capacity))]
    cycle_from_charging = capacity_from_charging / max_battery_capacity_kwh / 2
    cycle_from_discharging = capacity_from_discharging / max_battery_capacity_kwh / 2
    solver.Add(battery_cycles[i] == battery_cycles[i - 1] + cycle_from_charging + cycle_from_discharging)

We use the same optimisation function, lets see how much money the model generates now:
""")

# ---------- VERSION 3 ALLOW POWER STEERING, TRACK CAPACITY AND LIMIT CYCLES ----------
solver = pywraplp.Solver(
    'VERSION 3 MAXIMIZE REVENUE, ACCOUNT FOR SoC AND CYCLES',
    pywraplp.Solver.GLOP_LINEAR_PROGRAMMING
)
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
    charge_efficiency=1,  # Still 100% RTE
    discharge_efficiency=1,
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
    optimal_revenue = solver.Objective().Value()
    optimiser_time = solver.wall_time()
    optimiser_iterations = solver.iterations()

    # Parse the results into lists
    optimal_revenue = solver.Objective().Value()
    optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
    optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
    optimal_capacity = [capacity[i].solution_value() for i in range(0, len(capacity))]
    optimal_cycles = [cycles[i].solution_value() for i in range(0, len(cycles))]
    average_state_of_charge = sum(optimal_capacity) / len(optimal_capacity)
    average_state_of_charge_perc = average_state_of_charge / max_battery_capacity_kwh * 100

    title = f"Battery Trading Benchmark - Dayahead {date_in_title} {country_name}\n" \
            f"Maximize revenue account for State of Charge and Cycles\n" \
            f"Average State of Charge: {average_state_of_charge_perc:,.2f}% " \
            f"Cycles: {optimal_cycles[-1]:.2f}\n" \
            f"Revenue: €{optimal_revenue:,.2f}\n" \
            f"Solved in {optimiser_time:.0f} ms in {optimiser_iterations} iterations"

    fig = plot_power_schedule_capacity_and_prices(
        price_schedule_df=price_schedule_df,
        x_axis=x_axis,
        charge_schedule=optimal_charge_power,
        discharge_schedule=optimal_discharge_power,
        capacity=optimal_capacity,
        title=title
    )
    col1, col2, col3 = st.columns(3)
    with col2:
        st.pyplot(fig)
else:
    print('The solver could not find an optimal solution.')

st.write(f"""
Depending on the day you have chosen, taking cycles into consideration can change a lot.
It looks like the optimum for steering your {max_power_kw:,.0f} kW BESS with {allowed_cycles:,.2f} cycles
 on the Dayahead market would generate €{optimal_revenue:,.2f} revenue!

This version still takes the SoC limits of {min_battery_capacity_kwh}-{max_battery_capacity_kwh} kWh into account.
However it will also limit how often it uses the battery by tracking the number of cycles it is making.
This means that this version has to be even smarter,
 and choose the limited amount of right moments to maximize its revenue.
It is forced to let prices go because it has already reached it maximum allowed number of cycles.

Adding cycles to the model has further improved our benchmark.
There is however one more consideration we can do.
""")

st.write(f"""
## Version 4. Add Round-Trip Efficiency, while steering power, tracking capacity and tracking cycles
Up until now we have allowed all charged and discharge power of the BESS to be stored in the SoC of the system.
In reality however, the BESS is not 100% efficient, and the system loses some of this power "to the birds".
You have configured your BESS with {charge_efficiency * 100:,.0f}% charge efficiency
 and {discharge_efficiency * 100:,.0f}% discharge efficiency.
That means that for every 10 MWh charged, only {10 * charge_efficiency:,.2f} MWh is stored in the system.
That means that for every 10 MWh discharged, only {10 * discharge_efficiency:,.2f} MWh is taken from the system.

In the case of charge_efficiency, if the prices are negative, this can improve your revenue.
As you can use more power (which you are being paid to use) before capacity limitations come lurking around the corner.

We add these efficiencies to our previously calculated capacity variables.

    capacity = [solver.IntVar(min_battery_capacity_kwh, max_battery_capacity_kwh, f'capacity_period_i')
                for i in range(0, len(charge_power) + 1)]
    # Capacity constraint ensure capacity follows from previous timestep
    capacity_from_charging = charge_power[i - 1] * length_of_timestep_hour
    capacity_from_charging = capacity_from_charging * charge_efficiency
    capacity_from_discharging = discharge_power[i - 1] * length_of_timestep_hour
    capacity_from_discharging = capacity_from_discharging * discharge_efficiency
    solver.Add(capacity[i] == capacity[i - 1] + capacity_from_charging - capacity_from_discharging)

We utilise the same optimisation function, lets see how much money the model generates now:
""")

# ---------- VERSION 4 ALLOW POWER STEERING, TRACK CAPACITY, LIMIT CYCLES AND ADD ROUND TRIP EFFICIENCY ----------
solver = pywraplp.Solver(
    'VERSION 4 MAXIMIZE REVENUE, ACCOUNT FOR SoC, CYCLES and RTE',
    pywraplp.Solver.GLOP_LINEAR_PROGRAMMING
)
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
    optimal_revenue = solver.Objective().Value()
    optimiser_time = solver.wall_time()
    optimiser_iterations = solver.iterations()

    # Parse the results into lists
    optimal_revenue = solver.Objective().Value()
    optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
    optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
    optimal_capacity = [capacity[i].solution_value() for i in range(0, len(capacity))]
    optimal_cycles = [cycles[i].solution_value() for i in range(0, len(cycles))]
    average_state_of_charge = sum(optimal_capacity) / len(optimal_capacity)
    average_state_of_charge_perc = average_state_of_charge / max_battery_capacity_kwh * 100

    title = f"Battery Trading Benchmark - Dayahead {date_in_title} {country_name}\n" \
            f"Maximize revenue account for State of Charge, Cycles and RTE\n" \
            f"Average State of Charge: {average_state_of_charge_perc:,.2f}% " \
            f"Cycles: {optimal_cycles[-1]:.2f} " \
            f"Round Trip Efficiency: {round_trip_efficiency:.0f}%\n" \
            f"Revenue: €{optimal_revenue:,.2f}\n" \
            f"Solved in {optimiser_time:.0f} ms in {optimiser_iterations} iterations"
    fig = plot_power_schedule_capacity_and_prices(
        price_schedule_df=price_schedule_df,
        x_axis=x_axis,
        charge_schedule=optimal_charge_power,
        discharge_schedule=optimal_discharge_power,
        capacity=optimal_capacity,
        title=title
    )
    col1, col2, col3 = st.columns(3)
    with col2:
        st.pyplot(fig)
else:
    print('The solver could not find an optimal solution.')

st.write(f"""
Adding Round-Trip Efficiency to the equation forces the system to sometimes make smaller actions, rather than use the
 full power of the BESS.
It looks like the optimum for steering your {max_power_kw:,.0f} kW BESS with {allowed_cycles:,.2f} cycles
 and {round_trip_efficiency:.0f}% RTE on the Dayahead market would generate €{optimal_revenue:,.2f} revenue!
""")

st.write(f"""
## Conclusion
We have developed a model that uses perfect knowledge to benchmark the earnings of a BESS on the Dayahead market.
The following constraints were implemented in an iterative manner to demonstrate their influence on the result and
 the power of this optimisation technique:

* Power (MW)
* Capacity (MWh)
* Allowed Cycles
* Round-Trip Efficiency

For the very alert reader, the model makes some other assumptions regarding the benchmark.
If no `final_battery_capacity_kwh` is configured, the model will often ensure the BESS is empty at the end of the day.
This is because selling all capacity for whatever price will maximize the revenue.
Similarly, if the model is allowed to decide what its `initial_battery_capacity_kwh` is, the model will ensure that
 it starts the day at 100% SoC.
This allows it the possibility to sell as much energy as possible.

This blog post is the tip of the iceberg regarding the Battery Trading Benchmark.
The goal of [GIGA Storage]({GIGA_HOME_PAGE}) is too develop this tool further.
Not only for other energy markets, but with anybody who is interested in benchmarking the revenue of BESS.

The model built in this article as well as the source code of this article is available at
 [GigaStorage/battery-trading-benchmark]({REPOSITORY_HOME_PAGE}).
Feel free to dive into our [open-source community]({REPOSITORY_HOME_PAGE}).

### Change Log

* 17-04-2024: [PR #4 [ADD] Streamlit Blog Post introducing
 the Battery Trading Benchmark](https://github.com/GigaStorage/battery-trading-benchmark/pull/4)
""")
