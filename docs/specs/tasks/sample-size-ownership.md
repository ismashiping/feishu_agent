# sample_size ownership

Scope: explicit internal selection provenance for sample_size; public AnalysisResult unchanged.
Add sample_size_scope (current_study/review_aggregate/cited_study/unknown) to FieldSelection.
Only current_study counts enter original-study fields; systematic reviews accept only explicit
review_aggregate counts. cited_study, unknown and absent scope mean insufficient attribution,
so sample_size stays not_reported, with original sources retained. Never infer sample counts.
Retain existing quote ownership and exact-text validation before the attribution decision.
No regex guesses, broad refactor or cache changes. Existing historical AnalysisDraft test path
is not migrated; current production schema is AnalysisSelection.
Tests first: cited-study row cannot become review sample_size; original and aggregate counts
remain; unknown scope absent; model-inferred counts absent. Real same saved review evidence
re-extraction + actual report review, raw response saved; no guarantee model classification
is always right, reviewer checks scope against original evidence.
