import unittest

from ortools.linear_solver import pywraplp

from benchmark import add_power_schedules_to_solver, add_capacity_and_cycles_to_solver


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


if __name__ == '__main__':
    unittest.main()
