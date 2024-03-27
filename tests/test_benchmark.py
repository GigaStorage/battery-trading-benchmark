import unittest

from ortools.linear_solver import pywraplp

from benchmark import add_power_schedules_to_solver


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


if __name__ == '__main__':
    unittest.main()
