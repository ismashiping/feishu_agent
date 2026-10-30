# Phase 9 replay

Status: fail
Dataset: phase9-synthetic-v1 (synthetic_formula_fixture)

| Metric | Value | Numerator | Denominator | Status |
| --- | --- | --- | --- | --- |
| recall_at_k | 0.5 | 1.0 | 2.0 | fail |
| mrr | 0.25 | 0.5 | 2.0 | fail |
| identity_accuracy | 0.5 | 1.0 | 2.0 | fail |
| location_accuracy | 0.5 | 1.0 | 2.0 | fail |
| claim_support | 0.0 | 0.0 | 2.0 | fail |
| citation_coverage | 0.5 | 1.0 | 2.0 | fail |
| success_rate | 0.6666666666666666 | 2.0 | 3.0 | fail |
| refusal_accuracy | 1.0 | 1.0 | 1.0 | not_gated |
| allowed_claim_recall | 0.0 | 0.0 | 2.0 | fail |
| forbidden_claim_rate | 0.5 | 1.0 | 2.0 | fail |

Unexecuted: real_model, external, medical_review, service_load
Synthetic replay does not establish medical quality or production capacity.
Full observations, errors, configuration and provenance: results.json
