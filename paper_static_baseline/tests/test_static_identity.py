import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticBaselineIdentityTests(unittest.TestCase):
    def test_configuration_freezes_qnsga2_a0_and_static_scope(self):
        config = json.loads(
            (ROOT / "config" / "paper_static_v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["identity"], "paper-static-baseline-v1")
        self.assertEqual(config["algorithm"], "A0-QNSGA-II")
        self.assertEqual(config["scope"], "static-machine-agv")
        self.assertEqual(config["objectives"], ["makespan", "machine_energy"])
        self.assertFalse(config["innovation_enabled"])

    def test_dynamic_modules_are_absent(self):
        self.assertFalse((ROOT / "dfjspt" / "dynamic.py").exists())
        self.assertFalse((ROOT / "dfjspt" / "dynamic_experiments.py").exists())
        self.assertFalse((ROOT / "data" / "resources" / "dynamic_event_profiles.json").exists())
        self.assertEqual([], [path for path in ROOT.rglob("*") if "dynamic" in path.name.lower()])

    def test_static_package_imports_without_dynamic_exports(self):
        from paper_static_baseline import dfjspt

        self.assertFalse(hasattr(dfjspt, "DynamicEvent"))
        self.assertFalse(hasattr(dfjspt, "execute_rescheduling"))

    def test_required_static_modules_are_present(self):
        required = {
            "chromosome.py",
            "data.py",
            "decoder.py",
            "genetic.py",
            "initialization.py",
            "multiobjective.py",
            "neighborhoods.py",
            "qlearning.py",
            "qnsga2.py",
        }
        self.assertTrue(required.issubset({path.name for path in (ROOT / "dfjspt").glob("*.py")}))


if __name__ == "__main__":
    unittest.main()
