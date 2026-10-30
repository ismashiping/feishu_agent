"""Render the actual archival schema without connecting to a database."""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from clinical_agent.adapters.postgres.models import DocumentVersionRecord

if __name__ == "__main__":
    print(CreateTable(DocumentVersionRecord.__table__).compile(dialect=postgresql.dialect()))
