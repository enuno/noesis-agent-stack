# evals/
# Evaluation suites for the Noesis agent stack.
#
# Categories (charter §Model-catalog automation + §Observability):
#   routing           - route selection, fallback, filter correctness
#   coding            - code quality, test-pass rate, tool reliability
#   private-analysis  - privacy-lane correctness, no leakage, fail-closed behavior
#   safety            - policy/guardrail violations, prompt-injection resistance
#   r3                - manifest completeness, approval protocol, rollback drills
#
# Each suite produces: eval score, test-pass rate, schema validity, safety
# failures, quality drift. Results feed the catalog scorecard (catalog/scored/)
# and circuit-breaker decisions.

# Directory layout
#   README.md                    <- this file
#   routing/                     <- routing eval harness + cases
#   coding/                      <- coding eval harness + cases
#   private-analysis/            <- privacy-lane eval harness + cases
#   safety/                      <- safety eval harness + cases
#   r3/                          <- R3 approval-protocol drills
#   results/                     <- dated run outputs (eval_score, test_pass_rate, schema_validity)

version: "1.0.0"
updated: 2026-08-19
