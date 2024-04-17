import datetime as dt

import numpy as np
from matplotlib import pyplot as plt

from model import PriceScheduleDataFrame


def plot_power_schedule_capacity_and_prices(
        price_schedule_df: PriceScheduleDataFrame,
        x_axis: list[dt.datetime],
        charge_schedule: list[float],
        discharge_schedule: list[float],
        capacity: list[float],
        title: str = ''):
    """
    This method will create a plot with two subfigures, capacity and power, market prices and power.

    :param price_schedule_df: A PriceScheduleDataFrame with charge and discharge prices
    :param x_axis: List with matching x-axis for the PriceScheduleDataFrame
    :param charge_schedule: A list of floats with charge power actions (kW)
    :param discharge_schedule: A list of floats with discharge power actions (kW)
    :param capacity: A list of floats with the capacity of the system (kWh)
      capacity is assumed to be one length larger than the schedule
    :param title: A title to add to the top of the title sequence of the generated plot
    """
    # Invert the discharge_power to get negative values for discharging the battery
    discharge_power = discharge_schedule
    discharge_power = [-1 * discharge_power[i] for i in range(0, len(discharge_power))]
    charge_power = charge_schedule

    # Create the figure and subplots
    fig, (capacity_axis, prices_axis) = plt.subplots(2, 1, figsize=(10, 12))

    capacity_axis.set_title(title)
    # Plot 1 - Capacity
    capacity_axis.plot(x_axis, capacity[1:], label='Capacity', color='black')
    capacity_axis.set_ylabel('Capacity (kWh)')
    capacity_axis.set_ylim(int(max(capacity) * -0.1), int(max(capacity) * 1.1))

    # Create a secondary y-axis for power
    power_axis_1 = capacity_axis.twinx()
    # Plot the charge and discharge power as bars on the secondary y-axis
    power_axis_1.bar(x_axis, charge_power, width=0.009, alpha=0.6, label='Charge Power')
    power_axis_1.bar(x_axis, discharge_power, width=0.009, alpha=0.6, label='Discharge Power')
    power_axis_1.set_ylabel('Power (kW)')
    # Set the axis of power_axis_1
    max_discharge_power = max(discharge_power)
    max_charge_power = max(charge_power)
    power_axis_range = max(max_charge_power, max_discharge_power)
    power_axis_range = power_axis_range + (power_axis_range * 0.1)
    power_axis_1.set_ylim(-power_axis_range, power_axis_range)

    # Display the legends
    lines_capacity, labels_capacity = capacity_axis.get_legend_handles_labels()
    lines_power_1, label_power_1 = power_axis_1.get_legend_handles_labels()
    capacity_axis.legend(lines_capacity + lines_power_1, labels_capacity + label_power_1)

    # Plot 2 - Imbalance Prices with Power Overlay
    if np.all(price_schedule_df['charge_price'] == price_schedule_df['discharge_price']):
        # Charge and Discharge prices are the exact same, plot once
        prices_axis.bar(x_axis, list(price_schedule_df['charge_price']), width=0.009,
                        label='Energy Price', color='black', alpha=0.75)
    else:
        # Different Charge and Discharge prices, plot both
        prices_axis.bar(x_axis, list(price_schedule_df['charge_price']), width=0.009,
                        label='Charge Price', color='black', alpha=0.75)
        prices_axis.bar(x_axis, list(price_schedule_df['discharge_price']), width=0.009,
                        label='Discharge Price', color='black', alpha=0.25)
    prices_axis.set_xlabel('Time')
    prices_axis.set_ylabel('Energy Prices (€/MWh)')

    # Centre the y-axis 0 line
    max_imbalance_price = price_schedule_df['charge_price'].max()
    min_imbalance_price = price_schedule_df['discharge_price'].min()
    axis_range = max(max_imbalance_price, abs(min_imbalance_price))
    axis_range = axis_range + (axis_range * 0.1)
    prices_axis.set_ylim(-axis_range, axis_range)

    # Create a secondary y-axis for power
    power_axis_2 = prices_axis.twinx()
    # Plot the charge and discharge power as bars on the secondary y-axis
    power_axis_2.bar(x_axis, charge_power, width=0.009, alpha=0.65, label='Charge Power')
    power_axis_2.bar(x_axis, discharge_power, width=0.009, alpha=0.65, label='Discharge Power')
    power_axis_2.set_ylabel('Power (kW)')
    power_axis_2.set_ylim(-power_axis_range, power_axis_range)

    # Display the legends
    lines_prices, labels_prices = prices_axis.get_legend_handles_labels()
    lines_power_2, labels_power_2 = power_axis_2.get_legend_handles_labels()
    prices_axis.legend(lines_prices + lines_power_2, labels_prices + labels_power_2)

    # Rotate the datetime x-axis ticks
    capacity_axis.tick_params(axis='x', rotation=-45)
    prices_axis.tick_params(axis='x', rotation=-45)

    return fig
