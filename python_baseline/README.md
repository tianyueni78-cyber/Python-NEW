# Python baseline

This directory will contain the faithful Python reproduction.

Planned responsibilities:

- shared instance data model, chromosome representation, decoder, objectives,
  and metrics;
- separate QNSGA-II, NSGA-II, MOEA/D, and MOPSO optimizer entry points;
- explicit paper-defined ablation configurations;
- separate order-cancellation, machine-failure, and AGV-failure rescheduling;
- IS, RS, and CS strategy implementations.

No implementation belongs here until its MATLAB source path and validation
method have been recorded under `reproduction/`.
