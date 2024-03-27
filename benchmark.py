from ortools.linear_solver import pywraplp
import pandera as pa

PriceScheduleDataFrame = pa.DataFrameSchema({
    'charge_price': pa.Column(pa.Float),
    'discharge_price': pa.Column(pa.Float),
})


def add_power_schedules_to_solver(solver: pywraplp.Solver, schedule_length: int,
                                  max_power_kw: int) -> (list[pywraplp.Variable], list[pywraplp.Variable]):
    """
    Method to add a charge_power and discharge_power schedule to the solver object,
      the power schedules will be limted to the offered max_power_kw

    :param solver: a pywraplp.Solver instance that the constraints should be added to
    :param schedule_length: Integer specifying the length the power schedules should have
    :param max_power_kw: Integer specifying the max power the power schedules can have

    :return: (list, list) 2 lists representing charge_power and discharge_power
    """
    charge_power = [solver.IntVar(0, max_power_kw, f'charge_power_period_{i}')
                    for i in range(0, schedule_length)]
    discharge_power = [solver.IntVar(0, max_power_kw, f'discharge_power_period_{i}')
                       for i in range(0, schedule_length)]

    return charge_power, discharge_power


def add_capacity_and_cycles_to_solver(solver: pywraplp.Solver,
                                      charge_power: list[pywraplp.Variable],
                                      discharge_power: list[pywraplp.Variable],
                                      min_battery_capacity_kwh: int = 0,
                                      max_battery_capacity_kwh: int = 20,
                                      initial_battery_capacity_kwh: int = 10,
                                      final_battery_capacity_kwh: int = 10,
                                      length_of_timestep_hour: float = 1,
                                      charge_efficiency: float = 0.9,
                                      discharge_efficiency: float = 0.97,
                                      allowed_cycles: float = 1.5
                                      ) -> (list[pywraplp.Variable], list[pywraplp.Variable]):
    """
    Method to define a capacity schedule to the solver object,
      the capacity schedules will be limited by min and max battery_capacity_kwh,
      the schedule will start at initial_battery_capacity_kwh and end at final_battery_capacity_kwh
      length_of_timestep_hour, charge_efficiency and discharge_effciency are used to convert power to capacity

    :param solver: a pywraplp.Solver instance that the constraints should be added to
    :param charge_power: A charge power schedule specifying the amount of charge power per timestep
    :param discharge_power: A discharge power schedule specifying the amount of discharge power per timestep
    :param min_battery_capacity_kwh: An integer specifying the lower bound of the state of charge in kWh
    :param max_battery_capacity_kwh: An integer specifying the upper bound of the state of charge in kWh
    :param initial_battery_capacity_kwh: An integer specifying the initial capacity of the system
    :param final_battery_capacity_kwh: An integer specifying the final capacity of the system
    :param length_of_timestep_hour: A float specifying how to convert the power to capacity
    :param charge_efficiency: A float specifying how much chargepower is succesfully transformed into capacity
    :param discharge_efficiency: A float specifying how much discharge power is succesfully transformed into capacity
    :param allowed_cycles: A float specifying how many cycles are allowed to be made

    :return: capacity, a list representing the capacity in a battery at timestep i
    """
    # TODO add validation for the variables above.
    # Create capacity constraints
    capacity = [solver.IntVar(min_battery_capacity_kwh, max_battery_capacity_kwh, f'capacity_period_{i}')
                for i in range(0, len(charge_power) + 1)]
    battery_cycles = [solver.NumVar(0, allowed_cycles, f'battery_cycles_period_{i}')
                      for i in range(0, len(capacity))]

    for i in range(len(capacity)):
        if i == 0:  # Initial capacity for timestep 0
            solver.Add(capacity[i] == initial_battery_capacity_kwh)
            solver.Add(battery_cycles[i] == 0.0)
            continue
        if i == len(capacity) - 1:  # Capacity for final timestep
            solver.Add(capacity[i] == final_battery_capacity_kwh)

        # Capacity constraint ensure capacity follows from previous timestep
        capacity_from_charging = charge_power[i - 1] * length_of_timestep_hour
        capacity_from_charging = capacity_from_charging * charge_efficiency
        capacity_from_discharging = discharge_power[i - 1] * length_of_timestep_hour
        capacity_from_discharging = capacity_from_discharging * discharge_efficiency
        solver.Add(capacity[i] == capacity[i - 1] + capacity_from_charging - capacity_from_discharging)
        # Cycle constraint ensures the cycles are tracked from previous timestep
        cycle_from_charging = capacity_from_charging / max_battery_capacity_kwh / 2
        cycle_from_discharging = capacity_from_discharging / max_battery_capacity_kwh / 2
        solver.Add(battery_cycles[i] == battery_cycles[i - 1] + cycle_from_charging + cycle_from_discharging)

    return capacity, battery_cycles


def add_maximize_revenue(solver: pywraplp.Solver, price_schedule_df: PriceScheduleDataFrame,
                         length_of_timestep_hour: float,
                         charge_schedule: list[pywraplp.Variable], discharge_schedule: list[pywraplp.Variable]):
    charge_prices = price_schedule_df['charge_price'].to_list()
    discharge_prices = price_schedule_df['discharge_price'].to_list()

    costs = sum(charge_schedule[i] / 1000 * length_of_timestep_hour * charge_prices[i]
                for i in range(0, len(charge_schedule)))
    earnings = sum(discharge_schedule[i] / 1000 * length_of_timestep_hour *
                   discharge_prices[i] for i in range(0, len(discharge_schedule)))

    solver.Maximize(earnings - costs)
