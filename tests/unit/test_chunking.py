"""Source slices and bounded model-length decisions with explicit tokenizer doubles."""

from uuid import UUID

import pytest
from pydantic import ValidationError


def parsed_pdf(texts=("甲α🙂éabcdef", "", "Last page")):
    from clinical_agent.domain.models import LiteratureDocument, ParsedPdf

    document = LiteratureDocument.model_validate(
        {
            "document_id": str(UUID(int=1)),
            "title": "Fixture",
            "title_origin": "filename",
            "authors": [],
            "publication_date": {"precision": "unknown"},
            "journal": None,
            "doi": None,
            "pmid": None,
            "abstract": None,
            "text": "\n\n".join(texts),
            "source_type": "pdf",
            "source_uri": "file:///fixture.pdf",
            "source_url": None,
            "content_hash": "a" * 64,
            "content_scope": "extracted_text",
            "ingestion_time": "2026-10-27T00:00:00Z",
            "evidence_chunks": [],
        }
    )
    return ParsedPdf(
        document=document,
        source_units=[{"page": i, "text": t} for i, t in enumerate(texts, 1)],
        page_count=len(texts),
        parser_version="fixture",
    )


def run(parsed=None, *, tokenizer=None, profile=None, factory=None, **policy):
    from clinical_agent.domain.chunking import ChunkingPolicy, TokenizerProfile, chunk_source

    return chunk_source(
        parsed if parsed is not None else parsed_pdf(),
        tokenizer=tokenizer if tokenizer is not None else lambda s: len(s) + 2,
        profile=profile
        if profile is not None
        else TokenizerProfile(
            model_id="fixture",
            model_revision="fixed-fixture-1",
            tokenizer_revision="fixed-1",
            document_prefix="p: ",
            model_max_tokens=32,
        ),
        policy=ChunkingPolicy(**{"max_tokens": 8, **policy}),
        chunk_id_factory=factory if factory is not None else lambda i: UUID(int=i + 100),
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_tokens", 0),
        ("max_tokens", True),
        ("max_tokens", "8"),
        ("max_input_characters", 0),
        ("max_tokenizer_calls", -1),
        ("max_chunks", False),
        ("chunking_version", "future"),
    ],
)
def test_strict_policy(field, value):
    from clinical_agent.domain.chunking import ChunkingPolicy

    with pytest.raises(ValidationError):
        ChunkingPolicy(**{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_id", " "),
        ("model_revision", ""),
        ("tokenizer_revision", " "),
        ("model_max_tokens", True),
        ("document_prefix", None),
    ],
)
def test_profile_contract(field, value):
    from clinical_agent.domain.chunking import TokenizerProfile

    with pytest.raises(ValidationError):
        TokenizerProfile.model_validate(
            {
                "model_id": "fixture",
                "model_revision": "rev",
                "tokenizer_revision": "rev",
                "document_prefix": "p: ",
                "model_max_tokens": 8,
                field: value,
            }
        )


def test_unicode_page_identity_coverage_budget_and_roundtrip():
    from clinical_agent.domain.chunking import ChunkingResult

    parsed = parsed_pdf()
    before = parsed.model_dump_json()
    seen = []

    def tokenizer(text):
        seen.append(text)
        return len(text) + 2  # Explicit double: two special tokens, one per code point.

    result = run(parsed, tokenizer=tokenizer)
    assert parsed.model_dump_json() == before
    assert ChunkingResult.model_validate_json(result.model_dump_json()) == result
    assert seen and all(s.startswith("p: ") for s in seen)
    assert {item.evidence.location.page for item in result.chunks} == {1, 3}
    for unit in parsed.source_units:
        items = [x for x in result.chunks if x.evidence.location.page == unit.page]
        assert "".join(x.evidence.text for x in items).replace(" ", "") == unit.text.replace(
            " ", ""
        )
        for item in items:
            parsed.validate_chunk(item.evidence)
            assert item.token_count == len("p: " + item.evidence.text) + 2 <= 8
            assert item.evidence.embedding_info is None
            assert item.evidence.source_metadata.content_hash == parsed.document.content_hash
        assert all(
            a.evidence.location.end <= b.evidence.location.start
            for a, b in zip(items, items[1:], strict=False)
        )


def test_exact_fit_no_split_and_whitespace_preserved_inside_slice():
    result = run(parsed_pdf((" A \n",)), max_tokens=9)
    assert len(result.chunks) == 1
    assert result.chunks[0].evidence.text == "A \n"
    assert result.chunks[0].evidence.location.start == 1
    assert result.chunks[0].evidence.location.end == 4
    assert result.chunks[0].token_count == 8


def test_whitespace_units_do_not_call_tokenizer_or_factory():
    seen = []
    result = run(parsed_pdf((" \n\t", "A", "")), tokenizer=lambda s: seen.append(s) or 6)
    assert seen == ["p: A"]
    assert len(result.chunks) == 1 and result.chunks[0].evidence.location.page == 2


@pytest.mark.parametrize("value", [True, -1, 1.2, "3", None, 0])
def test_invalid_tokenizer_counts(value):
    from clinical_agent.domain.chunking import ChunkingError

    with pytest.raises(ChunkingError, match="^chunk_tokenizer_invalid$"):
        run(tokenizer=lambda _: value)


def test_tokenizer_error_does_not_expose_original_message():
    from clinical_agent.domain.chunking import ChunkingError

    def broken(_):
        raise RuntimeError("secret manuscript")

    with pytest.raises(ChunkingError, match="^chunk_tokenizer_failed$") as error:
        run(tokenizer=broken)
    assert error.value.__suppress_context__


@pytest.mark.parametrize(
    "policy,code",
    [
        ({"max_tokens": 33}, "chunk_model_limit"),
        ({"max_tokens": 5}, "chunk_unfit_character"),
        ({"max_input_characters": 1}, "chunk_input_limit"),
        ({"max_tokenizer_calls": 1}, "chunk_call_limit"),
        ({"max_chunks": 1}, "chunk_count_limit"),
    ],
)
def test_bounded_failure(policy, code):
    from clinical_agent.domain.chunking import ChunkingError

    with pytest.raises(ChunkingError, match=f"^{code}$"):
        run(**policy)


@pytest.mark.parametrize("factory", [lambda _: UUID(int=8), lambda _: "not-a-uuid"])
def test_invalid_ids(factory):
    from clinical_agent.domain.chunking import ChunkingError

    with pytest.raises(ChunkingError, match="^chunk_id_invalid$"):
        run(factory=factory)


def test_factory_programming_error_propagates():
    def broken(_):
        raise LookupError("factory bug")

    with pytest.raises(LookupError, match="factory bug"):
        run(factory=broken)


def test_nonmonotonic_counter_is_not_binary_searched():
    seen = []

    def counter(text):
        seen.append(text)
        return {"p: A": 6, "p: AB": 20, "p: ABC": 7}.get(text, 6)

    result = run(parsed_pdf(("ABC",)), tokenizer=counter)
    assert [x.evidence.text for x in result.chunks] == ["A", "BC"]
    assert "p: ABC" not in seen
    assert all(x.token_count <= 8 for x in result.chunks)


def test_mutated_input_revalidated():
    parsed = parsed_pdf()
    parsed.source_units[0].text = "changed"
    with pytest.raises(ValidationError):
        run(parsed)


def test_result_rejects_duplicate_ids_or_false_budget():
    from clinical_agent.domain.chunking import ChunkingResult

    data = run().model_dump()
    for kind in ("duplicate", "budget"):
        mutated = run().model_dump()
        if kind == "duplicate":
            mutated["chunks"][1]["evidence"]["chunk_id"] = data["chunks"][0]["evidence"]["chunk_id"]
        else:
            mutated["chunks"][0]["token_count"] = 9
        with pytest.raises(ValidationError):
            ChunkingResult.model_validate(mutated)


def test_candidate_character_cap_bounds_even_a_constant_counter():
    seen = []
    result = run(
        parsed_pdf(("abcdefghi",)),
        max_chunk_characters=3,
        tokenizer=lambda text: seen.append(text) or 1,
    )
    assert [item.evidence.text for item in result.chunks] == ["abc", "def", "ghi"]
    assert len(seen) == 9 and max(map(len, seen)) == len("p: ") + 3


def test_strict_candidate_character_cap():
    from clinical_agent.domain.chunking import ChunkingPolicy

    with pytest.raises(ValidationError):
        ChunkingPolicy(max_chunk_characters=True)


def test_call_limit_is_checked_before_the_next_callback():
    from clinical_agent.domain.chunking import ChunkingError

    calls = []
    with pytest.raises(ChunkingError, match="chunk_call_limit"):
        run(tokenizer=lambda text: calls.append(text) or 6, max_tokenizer_calls=1)
    assert len(calls) == 1
