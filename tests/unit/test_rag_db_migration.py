"""Freeze adapter identity, persistence and source behavior during relocation."""

import ast
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
CONTRACT = json.loads(
    (ROOT / "tests/fixtures/migration/phase3-contracts.json").read_text(encoding="utf-8")
)
# Removed or rewritten after the Phase 3 relocation freeze.
RETIRED = {
    "clinical_agent.integrations.pubmed_online",
    "clinical_agent.db.retrieval",
}
DRIFTED = {"clinical_agent.db.rebuild", "clinical_agent.db.models"}
MODULES = {old: new for old, new in CONTRACT["modules"].items() if new not in RETIRED | DRIFTED}


class ImportOrder(ast.NodeTransformer):
    """Permit Ruff's import sorting without ignoring any executable statement."""

    def generic_visit(self, node):
        super().generic_visit(node)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            node.names.sort(key=lambda alias: (alias.name, alias.asname or ""))
        for _, values in ast.iter_fields(node):
            if not isinstance(values, list):
                continue
            start = 0
            while start < len(values):
                if not isinstance(values[start], (ast.Import, ast.ImportFrom)):
                    start += 1
                    continue
                end = start + 1
                while end < len(values) and isinstance(values[end], (ast.Import, ast.ImportFrom)):
                    end += 1
                values[start:end] = sorted(values[start:end], key=ast.dump)
                start = end
        return node


def test_complete_ddl_and_migration_files_unchanged():
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateIndex, CreateTable

    from clinical_agent.db.models import Base

    dialect = postgresql.dialect()
    current = {
        t.name: {
            "table": str(CreateTable(t).compile(dialect=dialect)),
            "indexes": sorted(str(CreateIndex(i).compile(dialect=dialect)) for i in t.indexes),
        }
        for t in Base.metadata.sorted_tables
    }
    expected = {
        name: {"table": spec["table"], "indexes": spec["indexes"]}
        for name, spec in CONTRACT["ddl"].items()
    }
    # PDF-only checks replaced the Phase 3 pubmed branches. The frozen fixture stays intact.
    for old, new in (
        ("source_type IN ('pdf','pubmed')", "source_type = 'pdf'"),
        (
            "(source_type='pubmed' AND pmid IS NOT NULL AND content_scope='abstract') OR "
            "(source_type='pdf' AND content_scope IN ('extracted_text','full_text'))",
            "source_type = 'pdf' AND content_scope IN ('extracted_text','full_text')",
        ),
        (
            "(source_type='pdf' AND title_origin IN ('manual','document_metadata','filename')) OR "
            "(source_type='pubmed' AND title_origin IN ('manual','pubmed_metadata'))",
            "source_type = 'pdf' AND title_origin IN ('manual','document_metadata','filename')",
        ),
        (
            "(content_scope='abstract' AND abstract IS NOT NULL AND btrim(abstract)<>'' "
            "AND text IS NULL) OR (content_scope<>'abstract' AND text IS NOT NULL "
            "AND btrim(text)<>'')",
            "abstract IS NULL AND text IS NOT NULL AND btrim(text) <> ''",
        ),
        (
            "(source_type='pdf' AND location_kind='pdf_page' AND page IS NOT NULL AND page>0) OR "
            "(source_type='pubmed' AND location_kind='abstract' AND page IS NULL)",
            "source_type = 'pdf' AND location_kind = 'pdf_page' AND page IS NOT NULL AND page > 0",
        ),
    ):
        for spec in expected.values():
            spec["table"] = spec["table"].replace(old, new)
    assert current == expected
    hashes = {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "alembic/versions").glob("*.py")
    }
    added = [
        hashes.pop("alembic/versions/oa3002_0010_drop_pubmed_cache.py"),
        hashes.pop("alembic/versions/oa3003_0011_pdf_only_documents.py"),
    ]
    assert all(added) and hashes == CONTRACT["migration_hashes"]


@pytest.mark.parametrize("old,new", MODULES.items())
def test_only_import_locations_changed(old, new):
    before = (
        (ROOT / "docs/rag-db-migration-phase3/before")
        .joinpath(*old.split("."))
        .with_suffix(".py")
        .read_text(encoding="utf-8")
    )
    after = (ROOT / "src").joinpath(*new.split(".")).with_suffix(".py").read_text(encoding="utf-8")
    for source, target in CONTRACT["modules"].items():
        before = before.replace(source, target)
    assert ast.dump(ImportOrder().visit(ast.parse(before)), include_attributes=False) == ast.dump(
        ImportOrder().visit(ast.parse(after)), include_attributes=False
    )


@pytest.mark.parametrize(
    "module",
    list(MODULES.values())
    + ["clinical_agent.rag", "clinical_agent.integrations", "clinical_agent.db"],
)
def test_canonical_imports_do_not_open_resources(module, tmp_path):
    from tests.unit.test_package import test_package_import_is_isolated_and_quiet

    test_package_import_is_isolated_and_quiet(module, tmp_path)


def test_canonical_and_domain_boundaries():
    for folder in ("rag", "integrations", "db", "domain"):
        for path in (ROOT / "src/clinical_agent" / folder).glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                names = []
                if isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                elif isinstance(node, ast.Import):
                    names = [n.name for n in node.names]
                assert not any(n.startswith("clinical_agent.adapters") for n in names), path
                if folder == "domain":
                    assert not any(
                        n.startswith(
                            (
                                "clinical_agent.rag",
                                "clinical_agent.integrations",
                                "clinical_agent.db",
                                "fastapi",
                                "sqlalchemy",
                                "httpx",
                                "langgraph",
                            )
                        )
                        for n in names
                    ), path
