"""Reject PubMed abstract rows in the shared document tables.

Runs after oa3002_0010 has removed existing pubmed rows. PDF columns stay,
including optional pmid. Downgrade restores the previous checks and does not
restore deleted rows. This revision is not run on import.
"""

from alembic import op

revision = "oa3003_0011"
down_revision = "oa3002_0010"
branch_labels = None
depends_on = None

_CHECKS = {
    "documents": {
        "ck_documents_source_type": (
            "source_type = 'pdf'",
            "source_type IN ('pdf','pubmed')",
        ),
        "ck_documents_scope": (
            "source_type = 'pdf' AND content_scope IN ('extracted_text','full_text')",
            "(source_type='pubmed' AND pmid IS NOT NULL AND content_scope='abstract') OR "
            "(source_type='pdf' AND content_scope IN ('extracted_text','full_text'))",
        ),
        "ck_documents_title_origin": (
            "source_type = 'pdf' AND title_origin IN ('manual','document_metadata','filename')",
            "(source_type='pdf' AND title_origin IN ('manual','document_metadata','filename')) OR "
            "(source_type='pubmed' AND title_origin IN ('manual','pubmed_metadata'))",
        ),
        "ck_documents_content": (
            "abstract IS NULL AND text IS NOT NULL AND btrim(text) <> ''",
            "(content_scope='abstract' AND abstract IS NOT NULL AND btrim(abstract)<>'' "
            "AND text IS NULL) OR (content_scope<>'abstract' AND text IS NOT NULL "
            "AND btrim(text)<>'')",
        ),
    },
    "chunks": {
        "ck_chunks_location": (
            "source_type = 'pdf' AND location_kind = 'pdf_page' AND page IS NOT NULL AND page > 0",
            "(source_type='pdf' AND location_kind='pdf_page' AND page IS NOT NULL AND page>0) OR "
            "(source_type='pubmed' AND location_kind='abstract' AND page IS NULL)",
        ),
    },
}


def _replace(table: str, name: str, expression: str) -> None:
    op.drop_constraint(name, table, type_="check")
    op.create_check_constraint(name, table, expression)


def upgrade() -> None:
    for table, checks in _CHECKS.items():
        for name, (new, _old) in checks.items():
            _replace(table, name, new)


def downgrade() -> None:
    for table, checks in _CHECKS.items():
        for name, (_new, old) in checks.items():
            _replace(table, name, old)
