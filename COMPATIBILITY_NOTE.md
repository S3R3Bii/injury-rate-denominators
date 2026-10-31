# Gzip compatibility amendment after descriptive comparisons

The original21-dependency precomparison freeze remains in HISTORY/PLAN_FREEZE_original.json,with original analysis code in HISTORY/analyze_original.py. All original numeric outputs are retained.

A compatibility probe found that gzip.compress(...,mtime=0) writes different OS header bytes on CPython3.10 and3.12 for identical input:ff versus0a on this machine. This would fail the promised byte-exact replay despite equal CSV contents. The source,cohort,rate algebra,thresholds,prior strengths,zero bounds and all existing result bytes are unchanged.

The explicit GzipFile writer uses an empty filename and fixed timestamp,producing the existing3.10 bytes on3.12 for both complete compressed exports. PLAN_FREEZE.json retains21 actual protected dependencies,with the single changed writer hash and a link/hash to the original freeze. This is a disclosed post-analysis packaging amendment,not a new precomparison or blinded protocol. Both isolated full-history replays and complete numerical checks must pass on the amended version before release.
