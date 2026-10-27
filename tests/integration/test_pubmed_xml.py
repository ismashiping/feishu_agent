"""Offline, synthetic PubMed XML fixtures through the real safe XML parser."""

import hashlib
import socket
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest

pytestmark = pytest.mark.integration
NOW = datetime(2026, 10, 26, 16, tzinfo=UTC)
PMID = "1234567890"


def _article(pmid=PMID, date="<Year>2020</Year><Month>Feb</Month><Day>29</Day>"):
    return f"""<PubmedArticle><MedlineCitation><PMID>{pmid}</PMID>
    <Article><Journal><Title>Fixture Journal</Title>
    <JournalIssue><PubDate>{date}</PubDate></JournalIssue></Journal>
    <ArticleTitle>Synthetic <i>alpha</i> title</ArticleTitle>
    <ELocationID EIdType="doi">10.fixture/source</ELocationID>
    <Abstract><AbstractText Label="BACKGROUND"
    NlmCategory="BACKGROUND">A <i>mixed</i> text.</AbstractText>
    <AbstractText Label="EMPTY">   </AbstractText>
    <AbstractText Label="RESULTS" NlmCategory="RESULTS">Result &#945;🙂 &amp; tail.</AbstractText>
    </Abstract>
    <AuthorList><Author><LastName>Example</LastName><ForeName>Ada</ForeName><Initials>A</Initials></Author>
    <Author><CollectiveName>Fixture Group</CollectiveName></Author></AuthorList>
    <ArticleDate><Year>1999</Year><Month>1</Month><Day>1</Day></ArticleDate>
    </Article></MedlineCitation><PubmedData><ArticleIdList>
    <ArticleId IdType="pubmed">{pmid}</ArticleId>
    <ArticleId IdType="doi">10.fixture/source</ArticleId>
    </ArticleIdList><History><PubMedPubDate PubStatus="pubmed"><Year>2030</Year></PubMedPubDate>
    </History>
    </PubmedData></PubmedArticle>"""


def _write(path, records, *, prefix="", encoding="utf-8"):
    text = prefix + "<PubmedArticleSet>" + records + "</PubmedArticleSet>"
    path.write_bytes(text.encode(encoding))
    return path


def _identity(pmid):
    return uuid5(NAMESPACE_URL, "synthetic-pubmed-fixture:" + pmid)


def _parse(module, path, root, **kwargs):
    return module.parse_pubmed_xml(
        path,
        allowed_root=root,
        ingestion_time=NOW,
        document_id_factory=kwargs.pop("document_id_factory", _identity),
        **kwargs,
    )


def test_real_multi_article_metadata_sections_hash_and_roundtrip(tmp_path):
    from clinical_agent.adapters import pubmed_xml
    from clinical_agent.domain.models import PubmedXmlBatch

    path = _write(tmp_path / "fixture.xml", _article() + _article("1234567891"))
    batch = _parse(pubmed_xml, path, tmp_path)
    assert [entry.index for entry in batch.entries] == [1, 2]
    assert [entry.status for entry in batch.entries] == ["parsed", "parsed"]
    assert all(entry.error_code is None for entry in batch.entries)
    article = batch.entries[0].article
    document = article.document
    assert document.document_id == _identity(PMID) and document.pmid == PMID
    assert document.title == "Synthetic alpha title" and document.title_origin == "pubmed_metadata"
    assert document.authors == ["Ada Example", "Fixture Group"]
    assert document.journal == "Fixture Journal" and document.doi == "10.fixture/source"
    assert document.publication_date.model_dump() == {
        "precision": "day",
        "raw": "2020 Feb 29",
        "year": 2020,
        "month": 2,
        "day": 29,
    }
    assert document.abstract == "A mixed text.\n\nResult α🙂 & tail."
    assert document.text is None and document.content_scope == "abstract"
    assert document.source_url is None and document.evidence_chunks == []
    assert document.ingestion_time == NOW
    assert batch.source.content_hash == hashlib.sha256(path.read_bytes()).hexdigest()
    assert str(batch.source.source_uri) == path.resolve().as_uri()
    assert document.content_hash == batch.source.content_hash
    assert [unit.index for unit in article.source_units] == [1, 2]
    assert [unit.label for unit in article.source_units] == ["BACKGROUND", "RESULTS"]
    assert [unit.category for unit in article.source_units] == ["BACKGROUND", "RESULTS"]
    for unit in article.source_units:
        assert document.abstract[unit.start : unit.end] == unit.text
        assert unit.normalization_version == "pubmed-xml-text-v1"
    assert batch.parser_name == "defusedxml" and batch.parser_version == "0.7.1"
    assert PubmedXmlBatch.model_validate_json(batch.model_dump_json()) == batch


@pytest.mark.parametrize(
    "date,precision,year,month,day,raw",
    [
        ("", "unknown", None, None, None, None),
        ("<Year>2020</Year>", "year", 2020, None, None, "2020"),
        ("<Year>2020</Year><Month>12</Month>", "month", 2020, 12, None, "2020 12"),
        (
            "<Year>2020</Year><Month>January</Month><Day>2</Day>",
            "day",
            2020,
            1,
            2,
            "2020 January 2",
        ),
        (
            "<MedlineDate>2020 Dec-2021 Jan</MedlineDate>",
            "unknown",
            None,
            None,
            None,
            "2020 Dec-2021 Jan",
        ),
        ("<Year>2020</Year><Season>Winter</Season>", "unknown", None, None, None, "2020 Winter"),
        ("<Year>2020</Year><Month>Feb-Mar</Month>", "unknown", None, None, None, "2020 Feb-Mar"),
    ],
)
def test_publication_precision_is_not_invented(tmp_path, date, precision, year, month, day, raw):
    from clinical_agent.adapters import pubmed_xml

    batch = _parse(pubmed_xml, _write(tmp_path / "date.xml", _article(date=date)), tmp_path)
    value = batch.entries[0].article.document.publication_date
    assert value.model_dump() == {
        "precision": precision,
        "raw": raw,
        "year": year,
        "month": month,
        "day": day,
    }


@pytest.mark.parametrize(
    "date",
    [
        "<Year>2021</Year><Month>Feb</Month><Day>29</Day>",
        "<Year>2020</Year><Month>13</Month>",
        "<Year>0</Year>",
        "<Month>Feb</Month>",
        "<Year>2020</Year><Day>1</Day>",
        "<Year>2020</Year><MedlineDate>2021</MedlineDate>",
    ],
)
def test_bad_dates_reject_only_the_article(tmp_path, date):
    from clinical_agent.adapters import pubmed_xml

    batch = _parse(
        pubmed_xml,
        _write(tmp_path / "bad-date.xml", _article(date=date) + _article("1234567891")),
        tmp_path,
    )
    assert (
        batch.entries[0].status == "rejected"
        and batch.entries[0].error_code == "pubmed_invalid_date"
    )
    assert batch.entries[1].status == "parsed"


@pytest.mark.parametrize(
    "case,code",
    [
        ("missing_pmid", "pubmed_invalid_pmid"),
        ("invalid_pmid", "pubmed_invalid_pmid"),
        ("conflicting_pmid", "pubmed_pmid_conflict"),
        ("title", "pubmed_missing_title"),
        ("abstract", "pubmed_no_abstract"),
        ("author", "pubmed_invalid_author"),
        ("doi", "pubmed_doi_conflict"),
    ],
)
def test_mapping_rejections_are_per_record_and_do_not_allocate_identity(tmp_path, case, code):
    from clinical_agent.adapters import pubmed_xml

    article = _article()
    if case == "missing_pmid":
        article = article.replace(f"<PMID>{PMID}</PMID>", "")
    if case == "invalid_pmid":
        article = article.replace(f"<PMID>{PMID}</PMID>", "<PMID>bad</PMID>")
    if case == "conflicting_pmid":
        article = article.replace(
            f'<ArticleId IdType="pubmed">{PMID}', '<ArticleId IdType="pubmed">999'
        )
    if case == "title":
        article = article.replace("Synthetic <i>alpha</i> title", "  ")
    if case == "abstract":
        article = article.replace("<Abstract>", "<OtherAbstract>").replace(
            "</Abstract>", "</OtherAbstract>"
        )
    if case == "author":
        article = article.replace("<LastName>Example</LastName>", "")
    if case == "doi":
        article = article.replace(
            '<ArticleId IdType="doi">10.fixture/source', '<ArticleId IdType="doi">10.fixture/other'
        )
    calls = []

    def allocate(pmid):
        calls.append(pmid)
        return _identity(pmid)

    batch = _parse(
        pubmed_xml,
        _write(tmp_path / "mapping.xml", article + _article("1234567891")),
        tmp_path,
        document_id_factory=allocate,
    )
    assert batch.entries[0].article is None and batch.entries[0].error_code == code
    assert batch.entries[1].status == "parsed" and calls == ["1234567891"]


def test_duplicates_unsupported_and_missing_optional_metadata(tmp_path):
    from clinical_agent.adapters import pubmed_xml

    article = _article()
    article = article.replace('<ELocationID EIdType="doi">10.fixture/source</ELocationID>', "")
    article = article.replace('<ArticleId IdType="doi">10.fixture/source</ArticleId>', "")
    article = article.replace("<Title>Fixture Journal</Title>", "")
    batch = _parse(
        pubmed_xml,
        _write(tmp_path / "mixed.xml", article + _article() + "<PubmedBookArticle/>"),
        tmp_path,
    )
    assert batch.entries[0].article.document.doi is None
    assert batch.entries[0].article.document.journal is None
    assert [entry.error_code for entry in batch.entries] == [
        None,
        "pubmed_duplicate_pmid",
        "pubmed_unsupported_record",
    ]


def test_author_initials_suffix_invalid_author_and_journal_abbreviation(tmp_path):
    from clinical_agent.adapters import pubmed_xml

    article = (
        _article()
        .replace("<ForeName>Ada</ForeName>", "")
        .replace("<Initials>A</Initials>", "<Initials>AB</Initials><Suffix>Jr</Suffix>")
    )
    article = article.replace(
        "<AuthorList>", '<AuthorList><Author ValidYN="N"><LastName>Invalid</LastName></Author>'
    )
    article = article.replace(
        "<Title>Fixture Journal</Title>", "<ISOAbbreviation>Fixture J</ISOAbbreviation>"
    )
    result = (
        _parse(pubmed_xml, _write(tmp_path / "authors.xml", article), tmp_path)
        .entries[0]
        .article.document
    )
    assert result.authors == ["AB Example Jr", "Fixture Group"] and result.journal == "Fixture J"


def test_doctype_does_not_fetch_network_or_external_file(tmp_path, monkeypatch):
    from clinical_agent.adapters import pubmed_xml

    def forbidden(*args, **kwargs):
        pytest.fail("XML parsing attempted external access")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    prefix = '<!DOCTYPE PubmedArticleSet SYSTEM "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_250101.dtd">'
    path = _write(tmp_path / "doctype.xml", _article(), prefix=prefix)
    assert _parse(pubmed_xml, path, tmp_path).entries[0].status == "parsed"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
@pytest.mark.parametrize(
    "entity", ['"PRIVATE_ENTITY_SENTINEL"', 'SYSTEM "file:///not-opened-secret"']
)
def test_entity_declarations_are_rejected_before_expansion(tmp_path, encoding, entity):
    from clinical_agent.adapters import pubmed_xml

    prefix = f"<!DOCTYPE PubmedArticleSet [<!ENTITY private {entity}>]>"
    path = _write(
        tmp_path / "entity.xml",
        _article().replace("Synthetic <i>alpha</i> title", "&private;"),
        prefix=prefix,
        encoding=encoding,
    )
    with pytest.raises(pubmed_xml.PubmedXmlError, match="^xml_unsafe$"):
        _parse(pubmed_xml, path, tmp_path)


@pytest.mark.parametrize(
    "content,code",
    [
        (b"", "xml_invalid"),
        (b"<Other/>", "xml_root_invalid"),
        (("<PubmedArticleSet>" + _article() + "<bad").encode(), "xml_invalid"),
    ],
)
def test_whole_file_failures_do_not_return_partial_results_or_call_factory(tmp_path, content, code):
    from clinical_agent.adapters import pubmed_xml

    path = tmp_path / "PRIVATE_FILE.xml"
    path.write_bytes(content)

    def forbidden(pmid):
        pytest.fail("Identity allocated before XML validation")

    with pytest.raises(pubmed_xml.PubmedXmlError, match="^" + code + "$"):
        _parse(pubmed_xml, path, tmp_path, document_id_factory=forbidden)


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("max_file_bytes", 1, "xml_too_large"),
        ("max_records", 1, "xml_record_limit"),
        ("max_depth", 2, "xml_depth_limit"),
        ("max_nodes", 3, "xml_node_limit"),
    ],
)
def test_global_budgets_are_not_silent_truncation(tmp_path, field, value, code):
    from clinical_agent.adapters import pubmed_xml

    path = _write(tmp_path / "budget.xml", _article() + _article("1234567891"))
    with pytest.raises(pubmed_xml.PubmedXmlError, match="^" + code + "$"):
        _parse(pubmed_xml, path, tmp_path, limits=pubmed_xml.PubmedXmlLimits(**{field: value}))


def test_abstract_budget_is_a_per_article_rejection(tmp_path):
    from clinical_agent.adapters import pubmed_xml

    path = _write(tmp_path / "text-budget.xml", _article())
    result = _parse(
        pubmed_xml, path, tmp_path, limits=pubmed_xml.PubmedXmlLimits(max_abstract_characters=1)
    )
    assert result.entries[0].error_code == "pubmed_text_limit"


def test_clock_checked_after_mapping_and_callback_errors_not_swallowed(tmp_path, monkeypatch):
    from clinical_agent.adapters import pubmed_xml

    path = _write(tmp_path / "clock.xml", _article())
    done = []

    def allocate(pmid):
        done.append(True)
        return _identity(pmid)

    monkeypatch.setattr(pubmed_xml, "monotonic", lambda: 40.0 if done else 0.0)
    with pytest.raises(pubmed_xml.PubmedXmlError, match="^xml_timeout$"):
        _parse(pubmed_xml, path, tmp_path, document_id_factory=allocate)
    monkeypatch.setattr(pubmed_xml, "monotonic", lambda: 0.0)

    def broken(pmid):
        raise RuntimeError("fixture callback failed")

    with pytest.raises(RuntimeError, match="fixture callback failed"):
        _parse(pubmed_xml, path, tmp_path, document_id_factory=broken)


def test_snapshot_and_empty_batch_and_closed_input(tmp_path, monkeypatch):
    from clinical_agent.adapters import pubmed_xml

    path = _write(tmp_path / "snapshot.xml", _article())
    snapshot = path.read_bytes()
    files = []
    original_open = Path.open

    def track(target, *args, **kwargs):
        stream = original_open(target, *args, **kwargs)
        if target == path:
            files.append(stream)
        return stream

    monkeypatch.setattr(Path, "open", track)

    def allocate(pmid):
        assert files and all(stream.closed for stream in files)
        path.write_bytes(b"Changed by fixture callback after XML parse")
        return _identity(pmid)

    result = _parse(pubmed_xml, path, tmp_path, document_id_factory=allocate)
    assert result.source.content_hash == hashlib.sha256(snapshot).hexdigest()
    assert result.entries[0].article.document.title == "Synthetic alpha title"
    empty = _parse(pubmed_xml, _write(tmp_path / "empty.xml", ""), tmp_path)
    assert empty.entries == []


@pytest.mark.parametrize("case", ["missing", "directory", "outside"])
def test_input_must_be_under_allowed_root(tmp_path, case):
    from clinical_agent.adapters import pubmed_xml

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    path = allowed / "missing.xml"
    if case == "directory":
        path = allowed
    if case == "outside":
        path = _write(tmp_path / "outside.xml", _article())
    with pytest.raises(pubmed_xml.PubmedXmlError, match="^xml_path_invalid$"):
        _parse(pubmed_xml, path, allowed)


def test_blank_section_attributes_mean_unknown_not_batch_failure(tmp_path):
    from clinical_agent.adapters import pubmed_xml

    article = (
        _article()
        .replace('Label="BACKGROUND"', 'Label="  "')
        .replace('NlmCategory="BACKGROUND"', 'NlmCategory="  "')
    )
    result = _parse(pubmed_xml, _write(tmp_path / "attributes.xml", article), tmp_path)
    assert result.entries[0].status == "parsed"
    unit = result.entries[0].article.source_units[0]
    assert unit.label is None and unit.category is None


@pytest.mark.parametrize(
    "date",
    [
        "<Year>0000</Year><Season>Winter</Season>",
        "<Year>0000</Year><Month>Unknown</Month>",
    ],
)
def test_invalid_known_year_is_not_hidden_by_unknown_precision(tmp_path, date):
    from clinical_agent.adapters import pubmed_xml

    result = _parse(
        pubmed_xml, _write(tmp_path / "invalid-year.xml", _article(date=date)), tmp_path
    )
    assert result.entries[0].status == "rejected"
    assert result.entries[0].error_code == "pubmed_invalid_date"


def test_invalid_known_day_is_not_hidden_by_unknown_month(tmp_path):
    from clinical_agent.adapters import pubmed_xml

    date = "<Year>2020</Year><Month>Unknown</Month><Day>99</Day>"
    result = _parse(pubmed_xml, _write(tmp_path / "invalid-day.xml", _article(date=date)), tmp_path)
    assert result.entries[0].error_code == "pubmed_invalid_date"


def test_valid_utf16_unicode_abstract(tmp_path):
    from clinical_agent.adapters import pubmed_xml

    path = _write(tmp_path / "utf16.xml", _article(), encoding="utf-16")
    result = _parse(pubmed_xml, path, tmp_path)
    assert result.entries[0].article.document.abstract == "A mixed text.\n\nResult α🙂 & tail."


def test_file_read_error_has_only_a_safe_code(tmp_path, monkeypatch):
    from clinical_agent.adapters import pubmed_xml

    path = _write(tmp_path / "permission.xml", _article())

    def denied(*args, **kwargs):
        raise PermissionError("PRIVATE_XML_SENTINEL")

    monkeypatch.setattr(Path, "open", denied)
    with pytest.raises(pubmed_xml.PubmedXmlError, match="^xml_io_error$"):
        _parse(pubmed_xml, path, tmp_path)
