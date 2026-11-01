import pytest

from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.domain.analysis import AnalysisSelection
from tests.unit.test_analysis_assembly import _Model, _prepare, _selection


def test_sample_size_schema_distinguishes_study_and_sample_counts():
    schema = AnalysisSelection.model_json_schema()
    description = schema["$defs"]["FieldSelection"]["properties"]["field_name"].get(
        "description", ""
    )
    assert "sample_size" in description
    assert "included studies" in description
    assert "participants" in description


@pytest.mark.parametrize(
    "text,study_type",
    [
        ("The cohort included 2532 patients.", "cohort"),
        ("The dataset contains 8000 admission records.", "other"),
        ("The meta-analysis included 12000 participants.", "systematic_review"),
    ],
)
def test_explicit_participant_count_retains_exact_units(
    source_factory, prepared_factory, text, study_type
):
    request, retrieval, quote_id, text, identity = _prepare(
        source_factory, prepared_factory, text, "Study a cohort"
    )
    selection = _selection(identity, quote_id, "cohort")
    selection["studies"][0]["study_type"] = study_type
    selection["studies"][0]["reported"] = [
        dict(
            field_name="sample_size",
            quote_id=quote_id,
            role="reported",
            sample_size_scope="review_aggregate"
            if study_type == "systematic_review"
            else "current_study",
        )
    ]
    result = EvidenceAnalyzer(model=_Model(selection)).analyze(request, retrieval)
    assert result.studies[0].fields["sample_size"].value == text


def test_review_count_can_be_design_without_sample_size(source_factory, prepared_factory):
    request, retrieval, quote_id, text, identity = _prepare(
        source_factory,
        prepared_factory,
        "This systematic review included 47 studies.",
        "Study a review",
    )
    selection = _selection(identity, quote_id, "review")
    selection["studies"][0]["study_type"] = "systematic_review"
    result = EvidenceAnalyzer(model=_Model(selection)).analyze(request, retrieval)
    assert result.studies[0].fields["design"].value == text
    assert result.studies[0].fields["sample_size"].value is None


@pytest.mark.parametrize("scope", ["cited_study", "unknown", None])
def test_review_does_not_adopt_included_study_sample(source_factory, prepared_factory, scope):
    request, retrieval, quote_id, _, identity = _prepare(
        source_factory,
        prepared_factory,
        "Smith and colleagues enrolled 23950 ICU patients in their cohort.",
        "Study a review",
    )
    selection = _selection(identity, quote_id, "review")
    selection["studies"][0]["study_type"] = "systematic_review"
    item = dict(field_name="sample_size", quote_id=quote_id, role="reported")
    if scope is not None:
        item["sample_size_scope"] = scope
    selection["studies"][0]["reported"] = [item]
    result = EvidenceAnalyzer(model=_Model(selection)).analyze(request, retrieval)
    assert result.studies[0].fields["sample_size"].value is None
    assert result.studies[0].fields["sample_size"].basis == "not_reported"
    assert result.sources


@pytest.mark.parametrize(
    "study_type,scope",
    [
        ("cohort", "cited_study"),
        ("cohort", "review_aggregate"),
        ("systematic_review", "current_study"),
    ],
)
def test_sample_scope_must_match_study_subject(source_factory, prepared_factory, study_type, scope):
    request, retrieval, quote_id, _, identity = _prepare(
        source_factory, prepared_factory, "A study included 100 patients.", "Study a cohort"
    )
    selection = _selection(identity, quote_id, "cohort")
    selection["studies"][0].update(
        study_type=study_type,
        reported=[
            dict(
                field_name="sample_size",
                quote_id=quote_id,
                role="reported",
                sample_size_scope=scope,
            )
        ],
    )
    result = EvidenceAnalyzer(model=_Model(selection)).analyze(request, retrieval)
    assert result.studies[0].fields["sample_size"].value is None


def test_sample_size_cannot_be_reconstructed_as_inference(source_factory, prepared_factory):
    request, retrieval, quote_id, _, identity = _prepare(
        source_factory,
        prepared_factory,
        "The cohort has training and validation groups.",
        "Study a cohort",
    )
    selection = _selection(identity, quote_id, "cohort")
    selection["studies"][0]["inferences"] = [
        dict(
            field_name="sample_size",
            value="100 patients",
            epistemic_kind="model_inference",
            verification_needed="Check original counts",
            quote_id=quote_id,
        )
    ]
    result = EvidenceAnalyzer(model=_Model(selection)).analyze(request, retrieval)
    assert result.studies[0].fields["sample_size"].value is None
