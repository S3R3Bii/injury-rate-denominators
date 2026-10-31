# Retrospective exposure-concentration diagnostic

The frozen full-cohort results were examined before this addendum. Their eligible exposure total is361383028589 hours and industry32/legacy-unsplit size contributes336633380300. The original21-dependency freeze and all original outputs remain unchanged. This addition is retrospective, not a preregistered robustness test or a protected evaluation.

Before executing this additional diagnostic, fix all top-record counts to[1,5,10,100]. Sort eligible sufficient cells by reported hours descending; expand multiplicity to records. Export hours and cases represented by each top-k set, exact share of full eligible hours and the conditional pooled rate among remaining records. Retain all four cases. No model is refitted, prior strength selected, source record corrected or original estimate replaced.

Independently reconstruct the full weighted record set with SQLite and compare every field using Fraction arithmetic. Source hours must actually be integers before using SQLite integer sums; otherwise stop and revise the accounting representation with the limitation preserved. This is a representation check, not a cohort filter. Keep any failure.

The practical question is whether a same-cohort empirical prior can be dominated by a small number of reported exposures. A large concentration does not by itself prove the source values are erroneous. Conditional rates are diagnostics, not cleaned or representative population estimates. Native identities remain private.
