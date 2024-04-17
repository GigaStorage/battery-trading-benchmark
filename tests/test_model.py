import unittest

import pandas as pd
from ortools.linear_solver import pywraplp

from model import add_power_schedules_to_solver, add_capacity_and_cycles_to_solver, add_maximize_revenue


class TestBenchmark(unittest.TestCase):
    def test_add_power_schedules_to_solver(self):
        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=5,
            max_power_kw=1000,
        )
        self.assertEqual(5, len(charge_power))
        self.assertEqual(5, len(discharge_power))

        sum_charge_power = sum(charge_power)
        sum_discharge_power = sum(discharge_power)

        solver.Maximize(sum_charge_power + sum_discharge_power)

        solver.Solve()

        optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
        optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
        self.assertEqual(5000, sum(optimal_charge_power))
        self.assertEqual(1000, optimal_discharge_power[2])

        # Edit parameters
        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=2,
            max_power_kw=5000,
        )
        self.assertEqual(2, len(charge_power))
        self.assertEqual(2, len(discharge_power))
        sum_charge_power = sum(charge_power)
        sum_discharge_power = sum(discharge_power)

        solver.Maximize(sum_charge_power + sum_discharge_power)

        solver.Solve()

        optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
        optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
        self.assertEqual(10000, sum(optimal_charge_power))
        self.assertEqual(5000, optimal_discharge_power[0])

    def test_add_capacity_and_cycles_to_solver_default_capacity(self):
        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=5,
            max_power_kw=10,
        )
        capacity, cycles = add_capacity_and_cycles_to_solver(
            solver=solver,
            charge_power=charge_power,
            discharge_power=discharge_power,
        )
        self.assertEqual(6, len(capacity))
        self.assertEqual(6, len(cycles))

        sum_capacity = sum(capacity)
        solver.Maximize(sum_capacity)
        solver.Solve()

        optimal_capacity = [capacity[i].solution_value() for i in range(0, len(capacity))]
        self.assertEqual(10, optimal_capacity[0])  # Default initial_battery_capacity_kwh
        self.assertEqual(10, optimal_capacity[-1])  # Default final_battery_capacity_kwh
        self.assertEqual(20, max(optimal_capacity))  # Default max_battery_capacity_kwh
        # Additional test setting different parameters
        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=5,
            max_power_kw=10,
        )
        capacity, cycles = add_capacity_and_cycles_to_solver(
            solver=solver,
            charge_power=charge_power,
            discharge_power=discharge_power,
            initial_battery_capacity_kwh=5,
            final_battery_capacity_kwh=15
        )
        self.assertEqual(6, len(capacity))
        self.assertEqual(6, len(cycles))

        sum_capacity = sum(capacity)
        solver.Minimize(sum_capacity)  # And use minimize to test min_battery_capacity_kwh
        solver.Solve()
        optimal_capacity = [capacity[i].solution_value() for i in range(0, len(capacity))]
        self.assertEqual(5, optimal_capacity[0])
        self.assertEqual(15, optimal_capacity[-1])
        self.assertEqual(0, min(optimal_capacity))  # Default min_battery_capacity_kwh

    def test_add_capacity_and_cycles_to_solver_default_cycles(self):
        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=20,
            max_power_kw=10,
        )
        capacity, cycles = add_capacity_and_cycles_to_solver(
            solver=solver,
            charge_power=charge_power,
            discharge_power=discharge_power,
        )
        self.assertEqual(21, len(capacity))
        self.assertEqual(21, len(cycles))

        sum_cycles = sum(cycles)
        solver.Maximize(sum_cycles)
        solver.Solve()

        optimal_cycles = [cycles[i].solution_value() for i in range(0, len(cycles))]
        self.assertEqual(1.5, max(optimal_cycles))  # Default allowed_cycles

    def test_cycles_are_influenced_by_lower_rte(self):
        solver_high_cycles = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power_high, discharge_power_high = add_power_schedules_to_solver(
            solver=solver_high_cycles,
            schedule_length=20,
            max_power_kw=10,
        )
        capacity_high, cycles_high = add_capacity_and_cycles_to_solver(
            solver=solver_high_cycles,
            charge_power=charge_power_high,
            discharge_power=discharge_power_high,
            allowed_cycles=20.0
        )
        sum_cycles_high = sum(cycles_high)
        solver_high_cycles.Maximize(sum_cycles_high)
        solver_high_cycles.Solve()

        optimal_cycles_high = [cycles_high[i].solution_value() for i in range(0, len(cycles_high))]

        solver_low_cycles = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power_low, discharge_power_low = add_power_schedules_to_solver(
            solver=solver_low_cycles,
            schedule_length=20,
            max_power_kw=10,
        )
        capacity_low, cycles_low = add_capacity_and_cycles_to_solver(
            solver=solver_low_cycles,
            charge_power=charge_power_low,
            discharge_power=discharge_power_low,
            allowed_cycles=20.0,
            charge_efficiency=0.2,
            discharge_efficiency=0.2,
        )
        sum_cycles_low = sum(cycles_low)
        solver_low_cycles.Maximize(sum_cycles_low)
        solver_low_cycles.Solve()

        optimal_cycles_low = [cycles_low[i].solution_value() for i in range(0, len(cycles_low))]

        self.assertGreater(sum(optimal_cycles_high), sum(optimal_cycles_low))

    def test_calculating_capacity_based_on_discharge_power(self):
        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=3,
            max_power_kw=10,
        )
        capacity, cycles = add_capacity_and_cycles_to_solver(
            solver=solver,
            charge_power=charge_power,
            discharge_power=discharge_power,
            initial_battery_capacity_kwh=20,
            final_battery_capacity_kwh=0,
            discharge_efficiency=1.0
        )

        sum_capacity = sum(capacity)
        solver.Minimize(sum_capacity)
        solver.Solve()

        optimal_capacity = [capacity[i].solution_value() for i in range(0, len(capacity))]
        optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
        self.assertEqual(optimal_capacity[0], 20)
        self.assertEqual(optimal_discharge_power[0], 10)
        self.assertEqual(optimal_capacity[1], 10)
        self.assertEqual(optimal_discharge_power[1], 10)
        self.assertEqual(optimal_capacity[2], 0)
        self.assertEqual(optimal_discharge_power[2], 0)
        self.assertEqual(optimal_capacity[3], 0)

    def test_calculating_capacity_based_on_discharge_power_rte(self):
        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=5,
            max_power_kw=10,
        )
        capacity, cycles = add_capacity_and_cycles_to_solver(
            solver=solver,
            charge_power=charge_power,
            discharge_power=discharge_power,
            initial_battery_capacity_kwh=20,
            final_battery_capacity_kwh=0,
            discharge_efficiency=0.5
        )

        sum_capacity = sum(capacity)
        solver.Minimize(sum_capacity)
        solver.Solve()

        optimal_capacity = [capacity[i].solution_value() for i in range(0, len(capacity))]
        optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
        self.assertEqual(optimal_capacity[0], 20)
        self.assertEqual(optimal_discharge_power[0], 10)
        self.assertAlmostEqual(optimal_capacity[1], 15)
        self.assertEqual(optimal_discharge_power[1], 10)
        self.assertAlmostEqual(optimal_capacity[2], 10)
        self.assertEqual(optimal_discharge_power[2], 10)
        self.assertAlmostEqual(optimal_capacity[3], 5)
        self.assertEqual(optimal_discharge_power[3], 10)
        self.assertAlmostEqual(optimal_capacity[4], 0)
        self.assertEqual(optimal_discharge_power[4], 0)
        self.assertAlmostEqual(optimal_capacity[5], 0)

    def test_calculating_capacity_based_on_charge_power(self):
        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=3,
            max_power_kw=10,
        )
        capacity, cycles = add_capacity_and_cycles_to_solver(
            solver=solver,
            charge_power=charge_power,
            discharge_power=discharge_power,
            initial_battery_capacity_kwh=0,
            final_battery_capacity_kwh=20,
            charge_efficiency=1.0
        )

        sum_capacity = sum(capacity)
        solver.Maximize(sum_capacity)
        solver.Solve()

        optimal_capacity = [capacity[i].solution_value() for i in range(0, len(capacity))]
        optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
        self.assertEqual(optimal_capacity[0], 0)
        self.assertEqual(optimal_charge_power[0], 10)
        self.assertEqual(optimal_capacity[1], 10)
        self.assertEqual(optimal_charge_power[1], 10)
        self.assertEqual(optimal_capacity[2], 20)
        self.assertEqual(optimal_charge_power[2], 0)
        self.assertEqual(optimal_capacity[3], 20)

    def test_calculating_capacity_based_on_charge_power_rte(self):
        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=5,
            max_power_kw=10,
        )
        capacity, cycles = add_capacity_and_cycles_to_solver(
            solver=solver,
            charge_power=charge_power,
            discharge_power=discharge_power,
            initial_battery_capacity_kwh=0,
            final_battery_capacity_kwh=20,
            charge_efficiency=0.5
        )

        sum_capacity = sum(capacity)
        solver.Maximize(sum_capacity)
        solver.Solve()

        optimal_capacity = [capacity[i].solution_value() for i in range(0, len(capacity))]
        optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
        self.assertEqual(optimal_capacity[0], 0)
        self.assertEqual(optimal_charge_power[0], 10)
        self.assertAlmostEqual(optimal_capacity[1], 5)
        self.assertEqual(optimal_charge_power[1], 10)
        self.assertAlmostEqual(optimal_capacity[2], 10)
        self.assertEqual(optimal_charge_power[2], 10)
        self.assertAlmostEqual(optimal_capacity[3], 15)
        self.assertEqual(optimal_charge_power[3], 10)
        self.assertAlmostEqual(optimal_capacity[4], 20)
        self.assertEqual(optimal_charge_power[4], 0)
        self.assertAlmostEqual(optimal_capacity[5], 20)

    def test_simple_case_single_charge_and_discharge(self):
        price_schedule_list = [
            {
                'charge_price': 50.0,
                'discharge_price': 50.0
            },
            {
                'charge_price': 0.0,
                'discharge_price': 0.0
            },
            {
                'charge_price': 100.0,
                'discharge_price': 100.0
            },
            {
                'charge_price': 51.0,  # Equal numbers are not really noticed until cycles kick in
                'discharge_price': 51.0
            }
        ]
        price_schedule_df = pd.DataFrame(price_schedule_list)
        max_battery_capacity_kwh = 2000
        initial_battery_capacity_kwh = 1000
        min_battery_capacity_kwh = 0
        max_power_kw = 4000
        charge_efficiency = 1.0
        discharge_efficiency = 1.0
        allowed_cycles = 20
        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=len(price_schedule_df),
            max_power_kw=max_power_kw,
        )
        capacity, cycles = add_capacity_and_cycles_to_solver(
            solver=solver,
            charge_power=charge_power,
            discharge_power=discharge_power,
            initial_battery_capacity_kwh=initial_battery_capacity_kwh,
            final_battery_capacity_kwh=initial_battery_capacity_kwh,
            charge_efficiency=charge_efficiency,
            discharge_efficiency=discharge_efficiency,
            max_battery_capacity_kwh=max_battery_capacity_kwh,
            min_battery_capacity_kwh=min_battery_capacity_kwh,
            allowed_cycles=allowed_cycles,
            length_of_timestep_hour=0.25
        )
        add_maximize_revenue(
            solver=solver,
            price_schedule_df=price_schedule_df,
            charge_schedule=charge_power,
            discharge_schedule=discharge_power,
            length_of_timestep_hour=0.25
        )

        solver.Solve()
        optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
        optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
        optimal_revenue = solver.Objective().Value()
        optimal_cycles = [cycles[i].solution_value() for i in range(0, len(cycles))]

        self.assertListEqual([0.0, 4000.0, 0.0, 0.0], optimal_charge_power)
        self.assertListEqual([0.0, 0.0, 4000.0, 0.0], optimal_discharge_power)
        self.assertEqual(100.0, optimal_revenue)
        self.assertEqual(0.5, optimal_cycles[-1])

    def test_simple_case_single_charge_and_discharge_vice_versa(self):
        price_schedule_list = [
            {
                'charge_price': -50.0,
                'discharge_price': -50.0
            },
            {
                'charge_price': -100.0,
                'discharge_price': -100.0
            },
            {
                'charge_price': 0.0,
                'discharge_price': 0.0
            },
            {
                'charge_price': -49.0,  # Equal numbers are not really noticed until cycles kick in
                'discharge_price': -49.0
            }
        ]
        price_schedule_df = pd.DataFrame(price_schedule_list)
        max_battery_capacity_kwh = 2000
        min_battery_capacity_kwh = 0
        initial_battery_capacity_kwh = 1000
        max_power_kw = 4000
        charge_efficiency = 1.0
        discharge_efficiency = 1.0
        allowed_cycles = 20
        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=len(price_schedule_df),
            max_power_kw=max_power_kw,
        )
        capacity, cycles = add_capacity_and_cycles_to_solver(
            solver=solver,
            charge_power=charge_power,
            discharge_power=discharge_power,
            initial_battery_capacity_kwh=initial_battery_capacity_kwh,
            final_battery_capacity_kwh=initial_battery_capacity_kwh,
            charge_efficiency=charge_efficiency,
            discharge_efficiency=discharge_efficiency,
            max_battery_capacity_kwh=max_battery_capacity_kwh,
            min_battery_capacity_kwh=min_battery_capacity_kwh,
            allowed_cycles=allowed_cycles,
            length_of_timestep_hour=0.25
        )
        add_maximize_revenue(
            solver=solver,
            price_schedule_df=price_schedule_df,
            charge_schedule=charge_power,
            discharge_schedule=discharge_power,
            length_of_timestep_hour=0.25
        )

        solver.Solve()
        optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
        optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
        optimal_revenue = solver.Objective().Value()

        self.assertListEqual([0.0, 4000.0, 0.0, 0.0], optimal_charge_power)
        self.assertListEqual([0.0, 0.0, 4000.0, 0.0], optimal_discharge_power)
        self.assertEqual(100.0, optimal_revenue)

    def test_influence_of_max_power_kw(self):
        price_schedule_list = [
            {
                'charge_price': 50.0,
                'discharge_price': 50.0
            },
            {
                'charge_price': 0.0,
                'discharge_price': 0.0
            },
            {
                'charge_price': 100.0,
                'discharge_price': 100.0
            },
            {
                'charge_price': 51.0,  # Equal numbers are not really noticed until cycles kick in
                'discharge_price': 51.0
            }
        ]
        price_schedule_df = pd.DataFrame(price_schedule_list)
        max_battery_capacity_kwh = 2000
        initial_battery_capacity_kwh = 1000
        min_battery_capacity_kwh = 0
        max_power_kw = 2000
        charge_efficiency = 1.0
        discharge_efficiency = 1.0
        allowed_cycles = 20

        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=len(price_schedule_df),
            max_power_kw=max_power_kw,
        )
        capacity, cycles = add_capacity_and_cycles_to_solver(
            solver=solver,
            charge_power=charge_power,
            discharge_power=discharge_power,
            initial_battery_capacity_kwh=initial_battery_capacity_kwh,
            final_battery_capacity_kwh=initial_battery_capacity_kwh,
            charge_efficiency=charge_efficiency,
            discharge_efficiency=discharge_efficiency,
            max_battery_capacity_kwh=max_battery_capacity_kwh,
            min_battery_capacity_kwh=min_battery_capacity_kwh,
            allowed_cycles=allowed_cycles,
            length_of_timestep_hour=0.25
        )
        add_maximize_revenue(
            solver=solver,
            price_schedule_df=price_schedule_df,
            charge_schedule=charge_power,
            discharge_schedule=discharge_power,
            length_of_timestep_hour=0.25
        )

        solver.Solve()
        optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
        optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
        optimal_revenue = solver.Objective().Value()

        self.assertListEqual([2000.0, 2000.0, 0.0, 0.0], optimal_charge_power)
        self.assertListEqual([0.0, 0.0, 2000.0, 2000.0], optimal_discharge_power)
        self.assertEqual(50.50, optimal_revenue)

    def test_influence_of_max_battery_capacity_kwh(self):
        price_schedule_list = [
            {
                'charge_price': 50.0,
                'discharge_price': 50.0
            },
            {
                'charge_price': 0.0,
                'discharge_price': 0.0
            },
            {
                'charge_price': 100.0,
                'discharge_price': 100.0
            },
            {
                'charge_price': 51.0,  # Equal numbers are not really noticed until cycles kick in
                'discharge_price': 51.0
            }
        ]
        price_schedule_df = pd.DataFrame(price_schedule_list)

        max_battery_capacity_kwh = 4000
        initial_battery_capacity_kwh = 2000
        min_battery_capacity_kwh = 0
        max_power_kw = 4000
        charge_efficiency = 1.0
        discharge_efficiency = 1.0
        allowed_cycles = 20

        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=len(price_schedule_df),
            max_power_kw=max_power_kw,
        )
        capacity, cycles = add_capacity_and_cycles_to_solver(
            solver=solver,
            charge_power=charge_power,
            discharge_power=discharge_power,
            initial_battery_capacity_kwh=initial_battery_capacity_kwh,
            final_battery_capacity_kwh=initial_battery_capacity_kwh,
            charge_efficiency=charge_efficiency,
            discharge_efficiency=discharge_efficiency,
            max_battery_capacity_kwh=max_battery_capacity_kwh,
            min_battery_capacity_kwh=min_battery_capacity_kwh,
            allowed_cycles=allowed_cycles,
            length_of_timestep_hour=0.25
        )
        add_maximize_revenue(
            solver=solver,
            price_schedule_df=price_schedule_df,
            charge_schedule=charge_power,
            discharge_schedule=discharge_power,
            length_of_timestep_hour=0.25
        )

        solver.Solve()
        optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
        optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
        optimal_revenue = solver.Objective().Value()
        optimal_cycles = [cycles[i].solution_value() for i in range(0, len(cycles))]

        self.assertListEqual([4000.0, 4000.0, 0.0, 0.0], optimal_charge_power)
        self.assertListEqual([0.0, 0.0, 4000.0, 4000.0], optimal_discharge_power)
        self.assertEqual(101.0, optimal_revenue)

    def test_influence_of_charge_efficiency(self):
        price_schedule_list = [
            {
                'charge_price': 49.0,
                'discharge_price': 49.0
            },
            {
                'charge_price': 0.0,
                'discharge_price': 0.0
            },
            {
                'charge_price': 100.0,
                'discharge_price': 100.0
            },
            {
                'charge_price': 51.0,  # Equal numbers are not really noticed until cycles kick in
                'discharge_price': 51.0
            }
        ]
        price_schedule_df = pd.DataFrame(price_schedule_list)
        max_battery_capacity_kwh = 2000
        initial_battery_capacity_kwh = 1000
        min_battery_capacity_kwh = 0
        max_power_kw = 4000
        charge_efficiency = 0.5
        discharge_efficiency = 1.0
        allowed_cycles = 20

        solver = pywraplp.Solver('TEST SOLVER', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        charge_power, discharge_power = add_power_schedules_to_solver(
            solver=solver,
            schedule_length=len(price_schedule_df),
            max_power_kw=max_power_kw,
        )
        capacity, cycles = add_capacity_and_cycles_to_solver(
            solver=solver,
            charge_power=charge_power,
            discharge_power=discharge_power,
            initial_battery_capacity_kwh=initial_battery_capacity_kwh,
            final_battery_capacity_kwh=initial_battery_capacity_kwh,
            charge_efficiency=charge_efficiency,
            discharge_efficiency=discharge_efficiency,
            max_battery_capacity_kwh=max_battery_capacity_kwh,
            min_battery_capacity_kwh=min_battery_capacity_kwh,
            allowed_cycles=allowed_cycles,
            length_of_timestep_hour=0.25
        )
        add_maximize_revenue(
            solver=solver,
            price_schedule_df=price_schedule_df,
            charge_schedule=charge_power,
            discharge_schedule=discharge_power,
            length_of_timestep_hour=0.25
        )

        solver.Solve()
        optimal_charge_power = [charge_power[i].solution_value() for i in range(0, len(charge_power))]
        optimal_discharge_power = [discharge_power[i].solution_value() for i in range(0, len(discharge_power))]
        optimal_revenue = solver.Objective().Value()
        optimal_cycles = [cycles[i].solution_value() for i in range(0, len(cycles))]

        self.assertListEqual([4000.0, 4000.0, 0.0, 0.0], optimal_charge_power)
        self.assertListEqual([0.0, 0.0, 4000.0, 0.0], optimal_discharge_power)
        self.assertEqual(51.0, optimal_revenue)
        self.assertEqual(0.5, optimal_cycles[-1])  # Cycles aren't influenced by RTE


if __name__ == '__main__':
    unittest.main()
