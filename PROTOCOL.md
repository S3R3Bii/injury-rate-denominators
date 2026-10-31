# Fixed reported-rate and exposure sensitivity protocol

31 October 2026 UTC. Study16 independent program study. The original year-held-out workplace-ranking proposal is retained in ORIGINAL_PROPOSAL.md and remains unexecuted. This narrower cross-sectional study tests how exposure and explicit shrinkage assumptions affect reported summary rates; it does not forecast employer safety.

## Source and timing

One official OSHA 2025 Summary Data CSV, covering submissions January1-August31,2026. The ordinary visible public browser link succeeded after command-line requests returned403. Its complete bytes were saved privately before this numerical protocol; only its header, size and SHA-256 were inspected. No establishment values, counts, rates, rankings or model outputs have been examined. Do not claim that this protocol predates the file download. It predates establishment-value parsing and comparisons.

Use the exact captured file and all its rows. No case-detail data, worker identifiers or incident narratives. Official sources: https://www.osha.gov/itadata ; https://www.osha.gov/sites/default/files/summary_data_dictionary.pdf ; https://www.osha.gov/sites/default/files/ITA_data_users_guide.pdf .

## Cohort and identity

Fix year_filing_for=2025, valid six-digit NAICS code beginning31/32/33, and reported size code21(20-99 maximum employees),22(100-249) or2(20-249 unsplit legacy). Size is maximum employment during the year, not annual_average_employees. Retain all three broad industry prefixes and all three size classes, including empty cross-cells. NAICS versions may differ; do not infer detailed industry comparability from broad prefixes.

Within the entire file, quarantine whole groups sharing either record ID/year or establishment_ID/year; unknown identities are unavailable. This is a defensive within-file identity rule, not proof of physical-establishment identity or an across-year linkage. No employer names, addresses, EINs, identifiers, source row positions or geographic labels will be public.

Account for every national source row in this precedence: wrong/malformed year; malformed industry; other industry; other size; missing identity; duplicate identity; unknown counts; inconsistent count sums; unknown injury flag; inconsistent flag; unknown exposure; nonpositive exposure; eligible. The target manufacturing/size cohort includes every row after the other-size step. Preserve all missing/invalid categories; never fill them with zero. Counts must be finite nonnegative integers. Exposure hours must be finite numeric and strictly positive for a rate.

Total recordable cases are total_deaths + total_dafw_cases + total_djtr_cases + total_other_cases. Independently compare that total with the six injury/illness-type fields M1-M6. Inconsistent records remain in the source accounts, excluded from rate calculations. no_injuries_illnesses uses documented codes1=had injuries/illnesses,2=none; require code1 with positive count or2 with zero. Unknown or contradictory flags are explicit. Do not cap outlying exposures/rates or silently deduplicate.

## Fixed comparisons

The unit is reported recordable cases per100 full-time-equivalent worker-years: k/(hours/200000). The 200000-hour convention follows the OSHA users guide (100 workers,40 hours/week,50 weeks/year). Export every industry/size account and exact raw pooled rate. On eligible rows retain zero counts as observations; missing counts are unavailable.

Use a stated Gamma-Poisson working model only for descriptive sensitivity. Let t=hours/200000 and mu=sum(k)/sum(t) across the complete eligible cohort. For each row compare the raw rate k/t and the posterior mean (k+b*mu)/(t+b) for exactly b in [0.1,1,10]. Here b is an authored prior exposure in units of200000 hours, and the Gamma(shape=b*mu,rate=b) center is estimated from this same cohort. These decade-spaced strengths are declared sensitivity probes spanning20000-2000000 prior hours, not tuned or validated defaults. Retain every strength and stratum; choose no winner. If the pooled mean is zero or unavailable, report the working model unavailable rather than invent a proper positive-shape prior.

Primary diagnostic: count records whose rate exceeds twice the same-cohort pooled rate, before and after each strength. The two-times boundary is an authored comparison threshold, not a regulatory or operational trigger. Retain exact counts, denominators, all switch directions, exposure weights t/(t+b), and total absolute rate movement per stratum/strength. Do not publish employer ranks or recommend individual action.

As a separate precision illustration under a homogeneous independent Poisson process, report the one-sided95% upper rate for zero events, -log(0.05)/t, summarized by fixed strata. This is an assumption-based zero-count bound, not an empirically calibrated safety interval. No interval coverage, future accuracy, causal effect, general population rate or superiority claim. No tuning/search, random split or hidden holdout. Original year-held-out predictive assessment remains unexecuted; current post-year reported exposure and cases cannot be called prediction-time features.

## Numerical representation

Rates,posterior means,exposure weights,threshold comparisons and counts use exact Fraction arithmetic. Per-cell absolute rate movement is rounded to12 decimal places,half-even,then weighted and summed exactly as Decimal integers at that scale. Its aggregate rounding error is bounded by eligible records times0.5e-12 rate units. Zero-count upper bounds use60-digit Decimal logarithms and12-place half-even rounding. These representation choices are fixed before comparison;they are not empirically tuned tolerances.

## Implementation and independent checks

Public sufficient cells contain only industry prefix, size class, source-account state, exact eligible count/exposure and cell multiplicity, with source hashes and complete account totals. Native source stays private. Independently reconstruct projection with a pandas C parser and SQLite key multiplicities; compare all cells/accounts to csv/Decimal production ingestion. Check complete fixed cells, sums, units, fractions, missingness and disjoint accounts. Before comparing rates, commit a freeze of actual source/method/test dependencies.

Use independent SQLite weighted aggregates and Fraction arithmetic to reconstruct every output without production imports. Tests cover duplicate groups, maximum versus average employment, no-injury code semantics, zero/missing/negative/fractional counts, zero/negative/unknown exposure, contradictory sums, exact threshold ties, all three prior strengths, zero pooled mean and unsupported safety/forecast requests. Preserve all fixtures and full outputs. Check isolated Python replays, source-bound figure coordinates, actual PDF values/tables and rendered pages, privacy scope, and exact candidate/main CI/tree/tag.

## Practical use, rights and limits

A rate dashboard should retain numerator, exposure, zero/missing status and the assumptions behind smoothing. Use the local implementation exercise to return qualified statistical accounts and reject safety ranking, legal fault, worker eligibility and future-risk claims. The exercise certifies neither arbitrary caller data nor a production system.

These are submitted reporting records, not representative worker risk. Optional/nonrequired submissions are retained by OSHA, reporting can change, and aggregation does not resolve underreporting. No cross-year establishment identity is asserted. Public artifacts contain minimal statistical facts and original analysis with OSHA attribution. Raw records and names/addresses/identifiers remain private; no third-party PDFs are republished. MIT covers original code. No OSHA endorsement, new-estimator, deployment or savings claim. Separate formal-publication projects including Azure optimization remain private.

## Acceptance

Complete means lawful reconciled source, all-account and all-sensitivity exports, actual precomparison freeze, meaningful fixtures, independent exact reconstruction, reproducible outputs, executive-readable recommendation, readable source-bound figures/manuscript, privacy scope, and verified exact candidate/main/tree/tag/metadata. Each required gate must pass. Otherwise report incomplete with the actual missing evidence.
