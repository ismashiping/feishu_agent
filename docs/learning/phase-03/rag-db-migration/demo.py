"""Read an existing PDF and compile PostgreSQL DDL without external services."""
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from clinical_agent.rag import embedding as legacy_embedding
from clinical_agent.db.models import Base
from clinical_agent.domain.ingestion import document_id_for
from clinical_agent.rag import embedding
from clinical_agent.rag.pdf import parse_pdf


def main():
    root = Path(__file__).resolve().parents[4]
    source = root / "tests/fixtures/oa_fulltext/plos-fulltext.pdf"
    parsed = parse_pdf(
        source,
        allowed_root=source.parent,
        ingestion_time=datetime.now(UTC),
        document_id=document_id_for("pdf", sha256(source.read_bytes()).hexdigest()),
    )
    assert parsed.page_count > 0
    assert legacy_embedding is embedding
    ddl = str(CreateTable(Base.metadata.tables["documents"]).compile(dialect=postgresql.dialect()))
    assert "CREATE TABLE documents" in ddl
    print("PDF pages:", parsed.page_count)
    print("tables:", len(Base.metadata.tables))
    print("legacy embedding is canonical:", legacy_embedding is embedding)


if __name__ == "__main__":
    main()
