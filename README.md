# Python-NEW基于论文与现有发布代码重建的 baseline

Python reproduction of the MATLAB implementation accompanying the paper
*A Q-Learning based NSGA-II for dynamic flexible job shop scheduling with limited transportation resources*.

## Current status

Repository scaffold only. Algorithm migration has not started, and no baseline
has been claimed or accepted.

## Baseline principle

The project prioritizes fidelity to the paper and the executed MATLAB call path.
Deterministic components must be checked against MATLAB; stochastic experiments
must use documented, reproducible protocols. See [AGENTS.md](AGENTS.md) for the
binding reproduction boundary.

## Repository layout

| Path | Responsibility |
| --- | --- |
| `original_matlab/` | Local-source inventory and provenance notes; original MATLAB files are not republished by default |
| `python_baseline/` | Shared scheduling core and separate QNSGA-II, NSGA-II, MOEA/D, and MOPSO entry points |
| `tests/` | MATLAB-Python parity, feasibility, operator, metric, and dynamic-event checks |
| `experiments/` | Reproducible parameter, ablation, comparator, and rescheduling experiment entry points |
| `reproduction/` | Source map, discrepancy ledger, validation evidence, and baseline acceptance report |
| `results/` | Small reviewed summaries and figures; raw or large generated outputs stay untracked |

## Planned validation gates

1. Input parity
2. Chromosome validity
3. Decoder parity
4. Multi-objective operator parity
5. Q-learning behavior
6. Dynamic-event validity
7. Statistical reproduction

Python implementation begins only after the MATLAB execution path and evidence
map have been documented.
