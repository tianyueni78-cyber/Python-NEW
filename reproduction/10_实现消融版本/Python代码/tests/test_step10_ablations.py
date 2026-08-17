import json
import unittest
from pathlib import Path

from python_baseline.dfjspt.chromosome import Chromosome


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "python_baseline" / "data"
REFERENCE = json.loads(
    (DATA_ROOT / "matlab_reference" / "ablations_step10.json").read_text(
        encoding="utf-8"
    )
)


class AblationConfigurationTests(unittest.TestCase):
    def test_named_feature_matrix_matches_matlab_entry_points(self):
        from python_baseline.dfjspt.ablations import ablation_features

        actual = ablation_features()
        compared = (
            "random_initialization",
            "hybrid_initialization",
            "initial_nondomination_sort",
            "has_local_search",
            "neighborhood_count",
            "random_action",
            "q_action",
            "q_update",
        )
        self.assertEqual(list(actual), REFERENCE["locked_order"])
        for name in REFERENCE["locked_order"]:
            with self.subTest(variant=name):
                expected = REFERENCE["variants"][name]
                self.assertEqual(
                    {key: actual[name][key] for key in compared},
                    {key: expected[key] for key in compared},
                )
                self.assertEqual(actual[name]["python_stop"], "same_generations")

    def test_default_full_mode_equals_explicit_full_mode(self):
        from python_baseline.dfjspt.data import load_experiment_input
        from python_baseline.dfjspt.qnsga2 import run_qnsga2

        data = load_experiment_input(
            DATA_ROOT / "brandimarte" / "Mk01.fjs",
            DATA_ROOT / "resources" / "static_algorithm_comparison.json",
        )
        default = run_qnsga2(data, population_size=10, generations=1, seed=10101)
        explicit = run_qnsga2(
            data,
            population_size=10,
            generations=1,
            seed=10101,
            mode="full",
        )
        self.assertEqual(default, explicit)


class AblationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from python_baseline.dfjspt.data import load_experiment_input

        cls.data = load_experiment_input(
            DATA_ROOT / "brandimarte" / "Mk01.fjs",
            DATA_ROOT / "resources" / "static_algorithm_comparison.json",
        )

    def test_all_four_variants_are_reproducible_and_legal(self):
        from python_baseline.dfjspt.ablations import AblationVariant, run_ablation

        for offset, variant in enumerate(AblationVariant):
            with self.subTest(variant=variant.value):
                first = run_ablation(
                    self.data,
                    variant,
                    population_size=10,
                    generations=2,
                    seed=10200 + offset,
                )
                second = run_ablation(
                    self.data,
                    variant,
                    population_size=10,
                    generations=2,
                    seed=10200 + offset,
                )
                self.assertEqual(first, second)
                self.assertTrue(first.pareto_objectives)
                for chromosome in first.pareto_chromosomes:
                    self.assertIsInstance(chromosome, Chromosome)
                    chromosome.validate(self.data.instance, self.data.agv.count, 4)

    def test_only_full_variant_updates_qtable(self):
        from python_baseline.dfjspt.ablations import AblationVariant, run_ablation

        results = {
            variant: run_ablation(
                self.data,
                variant,
                population_size=10,
                generations=2,
                seed=20260817,
            )
            for variant in AblationVariant
        }
        for variant in (AblationVariant.A, AblationVariant.B, AblationVariant.C):
            self.assertFalse(
                any(value != 0 for row in results[variant].qtable for value in row)
            )
        self.assertTrue(
            any(
                value != 0
                for row in results[AblationVariant.FULL].qtable
                for value in row
            )
        )

    def test_neighborhood_variants_spend_more_evaluations_than_hybrid_only(self):
        from python_baseline.dfjspt.ablations import AblationVariant, run_ablation

        hybrid = run_ablation(
            self.data,
            AblationVariant.B,
            population_size=10,
            generations=1,
            seed=10301,
        )
        random_neighbor = run_ablation(
            self.data,
            AblationVariant.C,
            population_size=10,
            generations=1,
            seed=10301,
        )
        full = run_ablation(
            self.data,
            AblationVariant.FULL,
            population_size=10,
            generations=1,
            seed=10301,
        )
        self.assertEqual(random_neighbor.evaluations - hybrid.evaluations, 10)
        self.assertEqual(full.evaluations - hybrid.evaluations, 10)

    def test_step10_audit_passes(self):
        from scripts.check_step10 import check_step10

        report = check_step10()
        self.assertEqual(report["结论"], "通过")
        self.assertTrue(report["四版本特征矩阵一致"])
        self.assertTrue(report["仅完整版本更新Q表"])


if __name__ == "__main__":
    unittest.main()
