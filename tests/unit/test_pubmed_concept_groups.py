from clinical_agent.domain.pico import QueryPlan
from clinical_agent.domain.pubmed import PubMedSearchRequest


def test_concept_groups_are_supported():
    assert "concept_groups" in QueryPlan.model_fields


def test_explicit_query_preserved():
    from clinical_agent.domain.pubmed import PubMedOptions

    assert (
        PubMedSearchRequest(
            question="肝脏肿瘤内部亚区", options=PubMedOptions(query="39752907[uid]")
        ).query_text()
        == "39752907[uid]"
    )
