import inspect
import unittest
from pathlib import Path

from paper_static_baseline.dfjspt.qnsga2 import run_qnsga2


BASELINE = Path(__file__).resolve().parents[1]
PRODUCTION = BASELINE / "dfjspt"
DIFFERENCE_TABLE = BASELINE / "evidence" / "A0_与新方法差异表.md"


class InnovationFirewallTests(unittest.TestCase):
    def test_a0_entry_has_no_new_method_control_parameters(self):
        parameters = inspect.signature(run_qnsga2).parameters
        self.assertNotIn("top_k", parameters)
        self.assertNotIn("decode_budget", parameters)
        self.assertNotIn("action_k_n_b", parameters)

    def test_a0_production_has_no_innovation_identifiers(self):
        forbidden = ("top_k", "decode_budget", "action_k_n_b", "(k, n, b)")
        violations = []
        for path in PRODUCTION.glob("*.py"):
            lowered = path.read_text(encoding="utf-8").lower()
            if any(term in lowered for term in forbidden):
                violations.append(path.name)
        self.assertEqual(violations, [])

    def test_difference_table_states_the_immutable_boundary(self):
        text = DIFFERENCE_TABLE.read_text(encoding="utf-8")
        for required in ("Top-K", "(K,N,b)", "完整解码", "A0保持不变"):
            self.assertIn(required, text)


if __name__ == "__main__":
    unittest.main()
