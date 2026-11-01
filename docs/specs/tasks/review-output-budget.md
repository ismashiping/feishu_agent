# Review output budget

Confirmed live replay:38 claims, max_tokens1500, output_tokens1500, finish_reason length.
Scope: cap review batches at6 whole claims in addition to existing character limit;
request concise basis. Keep per-call1500 config, total deadline and unknown/error semantics.
Do not retry indefinitely or promote failed batches. Save finish_reason in safe error details.
Regression: character-small but many-claim report must split, exact coverage, no duplicate
or missing IDs. Real re-review same saved analysis/retrieval without regeneration.
6-claim cap is conservative for measured1500-token configuration, not guarantee for all
providers or much smaller user-supplied output budgets. Unfinished stays not_reviewed.

Results: live truncation reproduced with length/output_tokens1500/max_tokens1500.
Final targeted69 passed, Ruff/mypy passed. Same real evidence re-review7/9 batches covered
38/49 claims exactly, no not_reviewed items,11.735/13.781s. Reports remain incomplete for
support limitations. Full record docs/acceptance/review-output-budget-20261102/README.md.
