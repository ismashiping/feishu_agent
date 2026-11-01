# Sample size semantic boundary

Scope: model-facing extraction contract/instructions, no new output fields or quantities.
sample_size describes explicit participant, admission/record, or experimental sample counts,
keeping units verbatim. Included-study/article counts in a review belong in design/results,
never patient sample_size. A meta-analysis may report aggregate participants: those are valid.
If no eligible count is reported omit sample_size (program keeps not_reported); do not infer.
No blanket ban for systematic reviews and no regex-based medical semantic guess.
Tests verify extraction schema states boundary and valid reported counts remain unchanged.
Real re-extract previously saved review evidence with current model then actual ReportBuilder.
Existing reviewer gate continues to reject semantic mistakes; prompt is not a proof of truth.
