import random
import unittest
from pathlib import Path
from types import SimpleNamespace

from paper_static_baseline.dfjspt import moead, mopso, nsga2, qnsga2
from paper_static_baseline.dfjspt.data import load_experiment_input
from paper_static_baseline.dfjspt.initialization import random_population
from paper_static_baseline.dfjspt.objectives import evaluate_objectives


ROOT = Path(__file__).resolve().parents[1]


class UnifiedObjectiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_experiment_input(
            ROOT / "data" / "brandimarte" / "Mk01.fjs",
            ROOT / "data" / "resources" / "static_algorithm_comparison.json",
        )
        cls.chromosome = random_population(
            cls.data, 1, len(cls.data.agv.speeds), random.Random(1)
        ).chromosomes[0]

    def test_tec_excludes_agv_energy(self):
        schedule = SimpleNamespace(makespan=12.0, machine_energy=34.0, agv_energy=56.0)
        self.assertEqual((12.0, 34.0), evaluate_objectives(schedule))

    def test_chromosome_optimizers_share_one_objective(self):
        expected = qnsga2._evaluate(self.data, self.chromosome)
        self.assertEqual(expected, nsga2._evaluate(self.data, self.chromosome))
        self.assertEqual(expected, moead._evaluate(self.data, self.chromosome))

    def test_mopso_uses_unified_objective_for_its_decoded_chromosome(self):
        operation_count = sum(self.data.instance.operation_counts)
        objective, chromosome = mopso._evaluate(self.data, (0.0,) * (5 * operation_count))
        self.assertEqual(qnsga2._evaluate(self.data, chromosome), objective)


if __name__ == "__main__":
    unittest.main()
