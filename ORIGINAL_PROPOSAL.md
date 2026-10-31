# Injury rate stability for small establishments

## Source-readiness update — 29 October 2026

Unreleased: official summary downloads returned HTTP403; no source records or fitted model. Any later year-linked evaluation also needs an identity/attrition audit. Read the [bounded source hold](https://github.com/S3R3Bii/project-portfolio/blob/main/research-program/source-holds/study16-summary-access.md).

**State: protocol only. No result or novelty claim yet.**

## Decision

When does partial pooling change which workplaces appear to have unusually high reported injury rates?

## Target data

- [OSHA establishment injury and illness records](https://www.osha.gov/Establishment-Specific-Injury-and-Illness-Data) — targeted; exact export and rights must be verified.

## Study design

Exposure-adjusted hierarchical count models.

Year-held-out scoring; denominator checks; interval calibration; suppression sensitivity.

## Contribution to test

Compare raw rates with shrinkage under sparse exposure, without identifying workers. This is a proposed contribution, not a verified gap in the literature. Prior work must be reviewed before any novelty claim.

## Evidence to retain

- Exact source snapshot, request, retrieval time, observation window, definitions, units and redistribution terms.
- Prespecified splits, baseline, search space, tuning budget, seed and decision metric.
- All candidate results, including failures; final holdout used only after model selection.
- Independent headline recomputation, leakage checks and reviewed figures with units and uncertainty.
- Reproduction command and environment; private LaTeX manuscript written from measured results.

## Skills

R, Bayesian modeling, rate estimation, uncertainty. The repository must demonstrate these through executed work before they become portfolio claims.
