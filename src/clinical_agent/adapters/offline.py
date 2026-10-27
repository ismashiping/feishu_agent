"""Bounded content-addressed snapshots and existing offline parsers."""

import hashlib
import os
import tempfile
from pathlib import Path

from clinical_agent.adapters.pdf import PdfMetadataOverrides, PdfParseLimits, parse_pdf
from clinical_agent.adapters.pubmed_xml import PubmedXmlError, PubmedXmlLimits, parse_pubmed_xml
from clinical_agent.domain.ingestion import (
    ImportRequest,
    IngestionError,
    ParsedBatch,
    ParsedEntry,
    ParsedSource,
    document_id_for,
)
from clinical_agent.domain.models import LiteratureDocument, ParsedPdf


class OfflineReader:
    def __init__(
        self,
        snapshot_dir: Path,
        *,
        max_file_bytes: int = 20 * 1024**2,
        pdf_metadata: PdfMetadataOverrides | None = None,
        pdf_limits: PdfParseLimits | None = None,
        xml_limits: PubmedXmlLimits | None = None,
    ) -> None:
        if type(max_file_bytes) is not int or max_file_bytes <= 0:
            raise ValueError("Snapshot byte limit must be a positive integer")
        self._directory, self._max_bytes = snapshot_dir, max_file_bytes
        self._pdf_metadata, self._pdf_limits = pdf_metadata, pdf_limits
        self._xml_limits = xml_limits or PubmedXmlLimits(max_records=32)

    def _snapshot(self, request: ImportRequest) -> tuple[Path, str]:
        temporary: Path | None = None
        try:
            allowed = request.allowed_root.resolve(strict=True)
            source = request.path.resolve(strict=True)
            if not allowed.is_dir() or not source.is_file() or not source.is_relative_to(allowed):
                raise ValueError("Invalid source")
            with source.open("rb") as stream:
                data = stream.read(self._max_bytes + 1)
            if len(data) > self._max_bytes:
                raise ValueError("Invalid source")
            digest = hashlib.sha256(data).hexdigest()
            self._directory.mkdir(parents=True, exist_ok=True)
            root = self._directory.resolve(strict=True)
            destination = root / f"{digest}.{'pdf' if request.source_type == 'pdf' else 'xml'}"
            with tempfile.NamedTemporaryFile(dir=root, prefix=".ingest-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, destination)
            except FileExistsError:
                pass
            resolved = destination.resolve(strict=True)
            if not resolved.is_relative_to(root) or not resolved.is_file():
                raise ValueError("Invalid snapshot")
            with resolved.open("rb") as stream:
                existing = stream.read(self._max_bytes + 1)
            if existing != data:
                raise ValueError("Invalid snapshot")
            return resolved, digest
        except (OSError, ValueError):
            raise IngestionError("source_invalid") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def read(self, request: ImportRequest) -> ParsedBatch:
        request = ImportRequest.model_validate(request)
        path, digest = self._snapshot(request)
        if request.source_type == "pdf":
            parsed = parse_pdf(
                path,
                allowed_root=path.parent,
                ingestion_time=request.ingestion_time,
                document_id=document_id_for("pdf", digest),
                metadata=self._pdf_metadata,
                limits=self._pdf_limits,
            )
            if parsed.document.content_hash != digest:
                raise IngestionError("source_invalid")
            if parsed.document.title_origin == "filename":
                document = LiteratureDocument.model_validate(
                    {**parsed.document.model_dump(), "title": request.path.stem}
                )
                parsed = ParsedPdf.model_validate({**parsed.model_dump(), "document": document})
            source = ParsedSource(
                parsed=parsed, parser_name=parsed.parser_name, parser_version=parsed.parser_version
            )
            return ParsedBatch(entries=[ParsedEntry(index=1, source=source, error_code=None)])
        try:
            batch = parse_pubmed_xml(
                path,
                allowed_root=path.parent,
                ingestion_time=request.ingestion_time,
                document_id_factory=lambda pmid: document_id_for("pubmed", pmid),
                limits=self._xml_limits,
            )
        except PubmedXmlError as error:
            if error.code == "xml_record_limit":
                raise IngestionError("batch_limit") from None
            raise
        if batch.source.content_hash != digest:
            raise IngestionError("source_invalid")
        return ParsedBatch(
            entries=[
                ParsedEntry(
                    index=item.index,
                    source=ParsedSource(
                        parsed=item.article,
                        parser_name=batch.parser_name,
                        parser_version=batch.parser_version,
                    )
                    if item.article
                    else None,
                    error_code=item.error_code,
                )
                for item in batch.entries
            ]
        )
