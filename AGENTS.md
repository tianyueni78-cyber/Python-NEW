# AGENTS.md

## Project objective

The primary objective of this project is to establish a scientifically valid
Python baseline of the original MATLAB implementation accompanying the paper:

"A Q-Learning based NSGA-II for dynamic flexible job shop scheduling
with limited transportation resources."

Baseline validity takes priority over code elegance, runtime improvement,
refactoring, feature additions, or algorithmic innovation.

Until the baseline is formally accepted, all work is reproduction work,
not innovation work.

## Source-of-truth hierarchy

Use the following evidence hierarchy:

1. The published paper defines the intended problem, model, algorithm,
   experiment design, and reported conclusions.
2. The MATLAB call path actually used for the reported experiments defines
   implementation details omitted from the paper.
3. Input files, parameter files, and saved experiment outputs define the
   concrete experimental configuration.
4. Backup folders, commented code, alternative copies, and file names alone
   are not authoritative.

Do not select a MATLAB implementation merely because its directory or function
name appears correct. Trace the actual entry point and function calls first.

If the paper and executable MATLAB path differ:

- do not silently choose either version;
- record the difference;
- determine whether the difference affects baseline validity;
- ask the user before making a behavior-changing decision;
- when necessary, preserve both as explicit `paper` and `matlab` configurations.

## Non-negotiable baseline boundary

Do not change, simplify, remove, approximate, or reinterpret any of the
following without explicit user approval:

- problem definition;
- scheduling assumptions;
- chromosome representation;
- OS, MS, AS, or AGV speed segments;
- machine eligibility;
- operation precedence;
- AGV assignment and movement;
- loaded and unloaded travel;
- AGV location state;
- AGV battery consumption;
- charging trigger and charging duration;
- machine and AGV availability;
- active/left-shift decoding;
- makespan definition;
- total energy consumption definition;
- NSGA-II selection, crossover, mutation, sorting, crowding, and elitism;
- hybrid initialization;
- Q-learning state, action, reward, exploration, and update rules;
- neighborhood operators N1-N6;
- disturbance timing and duration;
- order cancellation logic;
- machine-failure logic;
- AGV-failure logic;
- IS, RS, and CS rescheduling rules;
- RSI, HV, IGD, and C-metric definitions;
- population size, stopping budget, repetition count, or comparison protocol.

Do not replace paper-specific logic with a library default merely because the
library implementation is standard or more convenient.

## Original MATLAB preservation

Treat all existing MATLAB source files, input files, and original result files
as read-only reference material.

Do not edit, rename, move, format, or delete original MATLAB files.

Place the Python reproduction in a separate, clearly named directory.

Any MATLAB instrumentation needed for comparison must be:

- minimal;
- placed in a separate script or copied working directory;
- clearly labelled as verification-only;
- prohibited from changing algorithm behavior.

## Reproduction before correction

Reproduce observed MATLAB behavior before attempting to correct it.

If a suspected defect, inconsistency, numerical issue, or undocumented behavior
is found:

1. preserve the original behavior in the baseline;
2. document the evidence and affected outputs;
3. determine whether it threatens baseline validity;
4. ask the user before implementing a corrected variant;
5. keep any corrected variant separate from the baseline.

Never silently "improve" the original algorithm.

## Shared-core boundary

Python implementations may share data structures, decoding, objective
evaluation, metrics, and genuinely identical utilities.

Before sharing a component across algorithms:

1. compare the corresponding MATLAB implementations;
2. verify that their behavior is materially identical;
3. record any algorithm-specific differences;
4. keep separate implementations when differences affect results.

Do not force superficially similar MATLAB functions into one shared Python
function when their behavior differs.

QNSGA-II, NSGA-II, MOEA/D, and MOPSO must have separate optimizer entry points.
Ablation variants may share the QNSGA-II implementation only through explicit,
named configurations that correspond to experiments in the paper.

## Required algorithm scope

The complete baseline must include:

- original data loading;
- chromosome representation;
- hybrid initialization;
- schedule decoding;
- makespan and TEC calculation;
- NSGA-II;
- Q-learning local search;
- neighborhood operators N1-N6;
- QNSGA-II;
- NSGA-II comparator;
- MOEA/D comparator;
- MOPSO comparator;
- paper-defined ablation variants;
- order-cancellation rescheduling;
- machine-failure rescheduling;
- AGV-failure rescheduling;
- IS, RS, and CS strategies;
- RSI, HV, IGD, and C-metric;
- repeated experiment execution;
- result export;
- Pareto plots, boxplots, and machine-AGV Gantt charts needed to reproduce
  the paper's experiment structure.

Do not declare the baseline complete when only the main optimizer runs.

## Validation gates

Development must proceed through the following gates.

### Gate 1: Input parity

Python and MATLAB must load materially identical instance data and parameters.

### Gate 2: Chromosome validity

Python encoding, initialization, crossover, mutation, and neighborhoods must
respect the same feasibility and indexing rules as MATLAB.

### Gate 3: Decoder parity

For identical fixed chromosomes, Python and MATLAB must agree, within documented
floating-point tolerance, on:

- machine assignment;
- AGV assignment;
- operation start and finish times;
- AGV loaded and unloaded movements;
- charging events;
- machine schedule;
- AGV schedule;
- makespan;
- total energy consumption.

Do not proceed to claims about optimizer performance before this gate passes.

### Gate 4: Multi-objective operator parity

For fixed objective matrices or populations, Python and MATLAB must agree on:

- dominance;
- non-dominated ranks;
- crowding-distance ordering;
- elite selection;
- metric calculations.

### Gate 5: Q-learning behavior

Tests must demonstrate that:

- states are assigned according to the intended rule;
- actions correspond to the correct neighborhoods;
- rewards match the intended formula;
- exploration follows the intended policy;
- the Q-table is actually updated;
- disabling components produces the intended ablation variants.

### Gate 6: Dynamic-event validity

Tests must demonstrate that:

- completed operations remain fixed;
- resources are unavailable during breakdown intervals;
- affected operations are correctly identified;
- inherited machine, AGV, location, and battery states are correct;
- rescheduled solutions remain feasible;
- IS, RS, and CS implement different intended policies.

### Gate 7: Statistical reproduction

Use the same experimental protocol whenever it is recoverable:

- instances;
- parameters;
- population size;
- stopping rule or budget;
- independent run count;
- metric definitions;
- reference-front construction;
- result aggregation.

Store every Python random seed and raw run result.

Do not select only favorable runs.

## Meaning of "same result"

Deterministic components must match MATLAB within documented numerical tolerance.

Stochastic optimizer trajectories are not required to match generation by
generation because MATLAB and Python may use different random-number streams,
sorting behavior, and floating-point evaluation order.

For stochastic experiments, baseline acceptance requires:

- reproducible Python runs from recorded seeds;
- the same algorithm and experiment budget;
- comparable result distributions;
- the same broad algorithm ranking or a documented investigation of differences;
- no unexplained difference large enough to reverse the paper's central claims.

Random-language differences alone do not invalidate the baseline.
Unexplained model, decoder, objective, constraint, or protocol differences do.

## Change-control rule

Before making any change that may alter schedules, objective values, Pareto
fronts, algorithm rankings, dynamic behavior, or paper conclusions:

1. state the proposed change;
2. identify the MATLAB and paper evidence;
3. explain the baseline risk;
4. ask for user approval;
5. add or update a parity test.

No silent behavior changes are allowed.

## Innovation firewall

Do not mix innovation code into the accepted baseline.

After the baseline is accepted:

- preserve it as a stable reference implementation;
- place innovations behind separate algorithms or configurations;
- compare every innovation against the unchanged baseline;
- use the same decoder, instances, budgets, seeds policy, and metrics unless
  the research question explicitly requires a change;
- document every intentional difference.

The baseline must remain runnable after innovation work begins.

## Reporting requirements

Maintain a reproduction ledger containing:

- paper claim or equation;
- MATLAB entry point;
- MATLAB implementation file;
- Python implementation file;
- parameters;
- verification method;
- parity status;
- unresolved discrepancy;
- baseline impact.

Classify every discrepancy as:

- no impact;
- documented numerical difference;
- configuration difference;
- implementation difference;
- potentially baseline-invalidating.

Potentially baseline-invalidating discrepancies require user review.

## Prohibited completion claims

Do not say that the baseline is reproduced, complete, equivalent, validated,
or successful unless the relevant validation commands have been run and their
outputs inspected.

Passing unit tests alone is not sufficient. Baseline completion requires
decoder parity, algorithm verification, dynamic-event verification, and
statistical reproduction evidence.

## Scope discipline

Use the minimum Python dependencies needed for faithful reproduction.

Do not add unrelated features, services, interfaces, databases, dashboards,
or abstractions.

Do not optimize performance before correctness and parity are established,
unless runtime prevents execution of the required reproduction experiment.

When uncertain, preserve evidence, stop the affected decision, and ask the user.
