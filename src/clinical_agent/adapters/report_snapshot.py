"""Reopen trusted acquired snapshots and verify original text locations."""

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

from clinical_agent.application.report import CheckStatus
from clinical_agent.domain.research import CitationSource
from clinical_agent.domain.retrieval import RetrievalResult


class SnapshotVerifier:
    def check(self, source: CitationSource, retrieval: RetrievalResult) -> CheckStatus:
        hits = [h for h in retrieval.hits if h.document.document_id == source.document_id]
        if not hits:
            return "invalid"
        try:
            if source.openalex_record is not None:
                record = source.openalex_record
                record.verify_snapshot()
                for hit in hits:
                    loc = hit.chunk.location
                    if (
                        hit.document.openalex_record != record
                        or loc.kind != "abstract"
                        or record.abstract[loc.start : loc.end] != hit.chunk.text
                    ):
                        return "invalid"
                return "valid"
            if source.snapshot_xml is not None:
                from clinical_agent.adapters.pubmed_xml import parse_pubmed_response

                if sha256(source.snapshot_xml.encode()).hexdigest() != source.content_hash:
                    return "invalid"
                records = parse_pubmed_response(
                    ("<PubmedArticleSet>" + source.snapshot_xml + "</PubmedArticleSet>").encode(),
                    fetched_at=datetime.now(UTC),
                )
                record = next((r for r in records if r.pmid == source.pmid), None)
                if record is None or record.title != source.title or record.doi != source.doi:
                    return "invalid"
                units = record.source_units
                for hit in hits:
                    loc = hit.chunk.location
                    if (
                        loc.kind != "abstract"
                        or loc.end > len(record.abstract)
                        or record.abstract[loc.start : loc.end] != hit.chunk.text
                        or (
                            loc.section is not None
                            and not any(
                                loc.section == u.label and loc.start >= u.start and loc.end <= u.end
                                for u in units
                            )
                        )
                    ):
                        return "invalid"
                return "valid"
            uri = urlsplit(str(hits[0].chunk.source_metadata.source_uri))
            if uri.scheme != "file" or uri.netloc not in {"", "localhost"}:
                return "unavailable"
            path = Path(url2pathname(uri.path))
            if not path.is_file():
                return "unavailable"
            with path.open("rb") as stream:
                content = stream.read(20 * 1024 * 1024 + 1)
            if len(content) > 20 * 1024 * 1024:
                return "unavailable"
            if sha256(content).hexdigest() != source.content_hash:
                return "invalid"
            if source.source_type == "pdf":
                from clinical_agent.adapters.pdf import parse_pdf

                parsed = parse_pdf(
                    path,
                    allowed_root=path.parent,
                    document_id=source.document_id,
                    ingestion_time=datetime.now(UTC),
                )
                for hit in hits:
                    parsed.validate_chunk(hit.chunk)
            else:
                from clinical_agent.adapters.pubmed_xml import parse_pubmed_xml
                from clinical_agent.domain.ingestion import document_id_for

                batch = parse_pubmed_xml(
                    path,
                    allowed_root=path.parent,
                    ingestion_time=datetime.now(UTC),
                    document_id_factory=lambda pmid: document_id_for("pubmed", pmid),
                )
                article = next(
                    (
                        e.article
                        for e in batch.entries
                        if e.article and e.article.document.pmid == source.pmid
                    ),
                    None,
                )
                if article is None:
                    return "invalid"
                for hit in hits:
                    article.validate_chunk(hit.chunk)
            return "valid"
        except OSError:
            return "unavailable"
        except Exception:
            return "invalid"
