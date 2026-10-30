# 整理前后实际目录树

包含全部未忽略的仓库文件。虚拟环境、密钥、模型及运行产物不纳入。代码无迁移；文档新增current/guides/governance/archive及主题索引。

## 整理前

```text
├── .dockerignore
├── .env.example
├── .github/
│   └── workflows/
│       └── evaluation.yml
├── .gitignore
├── .python-version
├── AGENTS.md.txt
├── Dockerfile
├── PROJECT.md.txt
├── README.md
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── p106_0001_initial_postgres_schema.py
│       ├── p107_0002_ingestion_metadata.py
│       ├── p501_0003_keyword_search.py
│       ├── p801_0004_document_versions.py
│       ├── p802_0005_update_runs.py
│       ├── p803_0006_source_governance.py
│       └── p804_0007_maintenance.py
├── alembic.ini
├── docker-compose.yml
├── docs/
│   ├── api.md
│   ├── architecture.md
│   ├── basic-rag.md
│   ├── cli.md
│   ├── development-plan.md
│   ├── documentation-audit.md
│   ├── feishu-dedup.md
│   ├── feishu-events.md
│   ├── feishu-runtime.md
│   ├── feishu-sender.md
│   ├── feishu-worker.md
│   ├── learning/
│   │   ├── ma-01/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── ma-02/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-00/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-01/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── install-python.ps1
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-03/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-04/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-05/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-06/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-07/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-08/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── governance_demo.py
│   │   │   ├── interview.md
│   │   │   ├── maintenance.md
│   │   │   ├── maintenance_demo.py
│   │   │   ├── source-governance.md
│   │   │   ├── troubleshooting.md
│   │   │   ├── tutorial.md
│   │   │   ├── update-manifest.json
│   │   │   └── update-runs.md
│   │   └── phase-09/
│   │       ├── README.md
│   │       ├── code-walkthrough.md
│   │       ├── demo.py
│   │       ├── exercises.md
│   │       ├── interview.md
│   │       ├── troubleshooting.md
│   │       └── tutorial.md
│   ├── local-embedding.md
│   ├── ma01-acceptance.md
│   ├── ma02-acceptance.md
│   ├── minimal-evaluation-baseline-plan.md
│   ├── multi-agent-roadmap.md
│   ├── offline-ingestion.md
│   ├── phase0-acceptance.md
│   ├── phase1-acceptance.md
│   ├── phase1-medical-review.md
│   ├── phase3-acceptance.md
│   ├── phase4-acceptance.md
│   ├── phase5-acceptance.md
│   ├── phase6-acceptance.md
│   ├── phase7-acceptance.md
│   ├── phase7-medical-review.md
│   ├── phase8-acceptance.md
│   ├── phase9-acceptance.md
│   ├── postgres.md
│   ├── research/
│   │   ├── dependencies/
│   │   │   ├── cpu-resolution-results.json
│   │   │   ├── ml-cpu-py312-linux.txt
│   │   │   ├── ml-cpu-py312-windows.txt
│   │   │   ├── ml-py312-linux.txt
│   │   │   ├── ml-py312-windows.txt
│   │   │   ├── ml.in
│   │   │   ├── phase0-py312-linux.txt
│   │   │   ├── phase0-py312-windows.txt
│   │   │   ├── phase0.in
│   │   │   ├── phase1-py312-linux.txt
│   │   │   ├── phase1-py312-windows.txt
│   │   │   ├── phase1.in
│   │   │   └── resolution-results.json
│   │   ├── environment-audit.md
│   │   ├── p0-03-validation.md
│   │   ├── p1-05-model-manifest.json
│   │   ├── pypi-metadata-2026-10-26.json
│   │   └── reference-repository-analysis.md
│   ├── specs/
│   │   ├── 00-project-overview.md
│   │   ├── 01-mvp.md
│   │   ├── 02-async-experience.md
│   │   ├── 03-pico.md
│   │   ├── 04-pubmed-search.md
│   │   ├── 05-hybrid-retrieval.md
│   │   ├── 06-evidence-analysis.md
│   │   ├── 07-citation-report.md
│   │   ├── 08-knowledge-update.md
│   │   ├── 09-evaluation.md
│   │   └── tasks/
│   │       ├── langchain-model-boundary.md
│   │       ├── ma-01-planner-scout.md
│   │       ├── ma-02-feedback.md
│   │       ├── minimal-evaluation-baseline.md
│   │       ├── p1-01-literature-contracts.md
│   │       ├── p1-02-pdf-parsing.md
│   │       ├── p1-03-pubmed-xml.md
│   │       ├── p1-04-source-chunking.md
│   │       ├── p1-05-local-embedding.md
│   │       ├── p1-06-postgres-schema.md
│   │       ├── p1-07-offline-ingestion.md
│   │       ├── p1-08-vector-retrieval.md
│   │       ├── p1-09-basic-rag.md
│   │       ├── p1-10-cli-entrypoints.md
│   │       ├── p1-11-fastapi.md
│   │       ├── p1-12-feishu-events.md
│   │       ├── p1-13-redis-dedup.md
│   │       ├── p1-14-feishu-worker.md
│   │       ├── p1-15-feishu-sender.md
│   │       ├── p1-16-feishu-runtime.md
│   │       ├── p1-17-mvp-acceptance.md
│   │       ├── p3-01-pico.md
│   │       ├── p4-01-pubmed-online.md
│   │       ├── p5-01-hybrid-retrieval.md
│   │       ├── p6-01-evidence-analysis.md
│   │       ├── p7-01-citation-report.md
│   │       ├── p8-01-version-publication.md
│   │       ├── p8-02-update-runs.md
│   │       ├── p8-03-source-governance.md
│   │       ├── p8-completion.md
│   │       ├── p9-evaluation.md
│   │       ├── phase0-acceptance.md
│   │       └── phase0-implementation.md
│   ├── tech-stack.md
│   ├── testing-strategy.md
│   └── vector-retrieval.md
├── evaluation/
│   ├── README.md
│   ├── minimal-v1/
│   │   ├── evidence/
│   │   │   ├── blood-pressure-pubmed.json
│   │   │   ├── continuation-summary.json
│   │   │   ├── e2e-attempt1-summary.json
│   │   │   ├── e2e-attempt2-summary.json
│   │   │   ├── model-calls.json
│   │   │   ├── model-response-1.txt
│   │   │   ├── model-response-2.txt
│   │   │   ├── model-response-3.txt
│   │   │   ├── model-response-4.txt
│   │   │   ├── samples.json
│   │   │   ├── sepsis-pubmed.json
│   │   │   ├── source-audit.json
│   │   │   └── summary.json
│   │   ├── human-labels.json
│   │   ├── manifest.json
│   │   └── source-state.json
│   ├── phase9-v1/
│   │   ├── dataset.json
│   │   ├── observations.json
│   │   └── thresholds.json
│   └── results/
│       ├── local-start-smoke/
│       │   ├── results.json
│       │   └── results.md
│       ├── ma01-baseline-replay/
│       │   ├── migration-checks.json
│       │   ├── results.json
│       │   └── results.md
│       ├── ma02-baseline-replay/
│       │   ├── results.json
│       │   └── results.md
│       ├── minimal-v1/
│       │   ├── results.json
│       │   └── results.md
│       ├── p802-fixed-regression/
│       │   ├── results.json
│       │   └── results.md
│       ├── phase8-completion/
│       │   ├── results.json
│       │   └── results.md
│       ├── phase9-final/
│       │   ├── results.json
│       │   └── results.md
│       ├── phase9-formulas/
│       │   ├── results.json
│       │   └── results.md
│       └── phase9-historical/
│           ├── results.json
│           └── results.md
├── pyproject.toml
├── scripts/
│   ├── audit_repository.py
│   ├── evaluate_minimal_baseline.py
│   ├── evaluate_phase9.py
│   ├── govern_sources.py
│   ├── rebuild_knowledge.py
│   ├── sync_pubmed.py
│   └── update_literature.py
├── src/
│   ├── clinical_agent/
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── embedding.py
│   │   │   ├── langchain_generation.py
│   │   │   ├── llm.py
│   │   │   ├── offline.py
│   │   │   ├── pdf.py
│   │   │   ├── postgres/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── connection.py
│   │   │   │   ├── governance.py
│   │   │   │   ├── maintenance.py
│   │   │   │   ├── models.py
│   │   │   │   ├── online_publication.py
│   │   │   │   ├── rebuild.py
│   │   │   │   ├── retrieval.py
│   │   │   │   ├── store.py
│   │   │   │   ├── update_runs.py
│   │   │   │   └── versions.py
│   │   │   ├── pubmed_online.py
│   │   │   ├── pubmed_xml.py
│   │   │   └── report_snapshot.py
│   │   ├── api.py
│   │   ├── api_runtime.py
│   │   ├── application/
│   │   │   ├── __init__.py
│   │   │   ├── agents.py
│   │   │   ├── analysis.py
│   │   │   ├── evaluation.py
│   │   │   ├── ingestion.py
│   │   │   ├── online_updates.py
│   │   │   ├── pico.py
│   │   │   ├── pubmed.py
│   │   │   ├── report.py
│   │   │   ├── research.py
│   │   │   ├── retrieval.py
│   │   │   ├── updates.py
│   │   │   └── workflow.py
│   │   ├── bootstrap.py
│   │   ├── cli.py
│   │   ├── command_runtime.py
│   │   ├── config.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── analysis.py
│   │   │   ├── chunking.py
│   │   │   ├── citations.py
│   │   │   ├── embedding.py
│   │   │   ├── governance.py
│   │   │   ├── hybrid.py
│   │   │   ├── ingestion.py
│   │   │   ├── maintenance.py
│   │   │   ├── models.py
│   │   │   ├── pico.py
│   │   │   ├── pubmed.py
│   │   │   ├── report.py
│   │   │   ├── research.py
│   │   │   ├── retrieval.py
│   │   │   └── updates.py
│   │   └── logging_config.py
│   └── feishu/
│       ├── __init__.py
│       ├── dedup.py
│       ├── events.py
│       ├── main.py
│       ├── sender.py
│       └── worker.py
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── hybrid/
│   │   │   └── cases.json
│   │   └── pico/
│   │       └── questions.json
│   ├── integration/
│   │   ├── test_api.py
│   │   ├── test_api_pipeline.py
│   │   ├── test_chunking.py
│   │   ├── test_cli.py
│   │   ├── test_command_entrypoints.py
│   │   ├── test_command_pipeline.py
│   │   ├── test_embedding_real.py
│   │   ├── test_evaluation.py
│   │   ├── test_feishu_dedup_redis.py
│   │   ├── test_feishu_runtime_live.py
│   │   ├── test_hybrid_retrieval.py
│   │   ├── test_ingestion.py
│   │   ├── test_knowledge_versions.py
│   │   ├── test_llm.py
│   │   ├── test_offline_reader.py
│   │   ├── test_pdf.py
│   │   ├── test_phase1_acceptance.py
│   │   ├── test_phase8_completion.py
│   │   ├── test_pico.py
│   │   ├── test_postgres.py
│   │   ├── test_pubmed_online.py
│   │   ├── test_pubmed_xml.py
│   │   ├── test_research_live.py
│   │   ├── test_retrieval.py
│   │   ├── test_source_governance.py
│   │   └── test_update_runs.py
│   └── unit/
│       ├── test_agent_roles.py
│       ├── test_api_runtime.py
│       ├── test_bootstrap.py
│       ├── test_chunking.py
│       ├── test_citation_report.py
│       ├── test_command_cli.py
│       ├── test_command_runtime.py
│       ├── test_config.py
│       ├── test_embedding.py
│       ├── test_evaluation.py
│       ├── test_evidence_analysis.py
│       ├── test_feedback_agents.py
│       ├── test_feishu_dedup.py
│       ├── test_feishu_deployment.py
│       ├── test_feishu_events.py
│       ├── test_feishu_main.py
│       ├── test_feishu_sender.py
│       ├── test_feishu_worker.py
│       ├── test_hybrid_retrieval.py
│       ├── test_ingestion.py
│       ├── test_ingestion_mapping.py
│       ├── test_knowledge_update.py
│       ├── test_knowledge_versions.py
│       ├── test_langchain_generation.py
│       ├── test_literature_models.py
│       ├── test_logging_config.py
│       ├── test_minimal_baseline.py
│       ├── test_package.py
│       ├── test_pdf_contracts.py
│       ├── test_phase8_completion.py
│       ├── test_pico.py
│       ├── test_postgres.py
│       ├── test_pubmed_contracts.py
│       ├── test_pubmed_online.py
│       ├── test_research.py
│       ├── test_retrieval.py
│       └── test_source_governance.py
└── uv.lock
```

## 整理后

```text
├── .dockerignore
├── .env.example
├── .github/
│   └── workflows/
│       └── evaluation.yml
├── .gitignore
├── .python-version
├── AGENTS.md.txt
├── Dockerfile
├── PROJECT.md.txt
├── README.md
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── p106_0001_initial_postgres_schema.py
│       ├── p107_0002_ingestion_metadata.py
│       ├── p501_0003_keyword_search.py
│       ├── p801_0004_document_versions.py
│       ├── p802_0005_update_runs.py
│       ├── p803_0006_source_governance.py
│       └── p804_0007_maintenance.py
├── alembic.ini
├── docker-compose.yml
├── docs/
│   ├── README.md
│   ├── api.md
│   ├── architecture.md
│   ├── archive/
│   │   ├── architecture-before-governance.md
│   │   ├── development-plan-before-governance.md
│   │   └── readme-before-governance.md
│   ├── basic-rag.md
│   ├── cli.md
│   ├── current/
│   │   └── architecture.md
│   ├── development-plan.md
│   ├── documentation-audit.md
│   ├── feishu-dedup.md
│   ├── feishu-events.md
│   ├── feishu-runtime.md
│   ├── feishu-sender.md
│   ├── feishu-worker.md
│   ├── governance/
│   │   ├── README.md
│   │   ├── baseline.json
│   │   ├── inventory.md
│   │   ├── plan.md
│   │   └── tree.md
│   ├── guides/
│   │   └── README.md
│   ├── learning/
│   │   ├── README.md
│   │   ├── ma-01/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── ma-02/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-00/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-01/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── install-python.ps1
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-03/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-04/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-05/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-06/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-07/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── interview.md
│   │   │   ├── troubleshooting.md
│   │   │   └── tutorial.md
│   │   ├── phase-08/
│   │   │   ├── README.md
│   │   │   ├── code-walkthrough.md
│   │   │   ├── demo.py
│   │   │   ├── exercises.md
│   │   │   ├── governance_demo.py
│   │   │   ├── interview.md
│   │   │   ├── maintenance.md
│   │   │   ├── maintenance_demo.py
│   │   │   ├── source-governance.md
│   │   │   ├── troubleshooting.md
│   │   │   ├── tutorial.md
│   │   │   ├── update-manifest.json
│   │   │   └── update-runs.md
│   │   └── phase-09/
│   │       ├── README.md
│   │       ├── code-walkthrough.md
│   │       ├── demo.py
│   │       ├── exercises.md
│   │       ├── interview.md
│   │       ├── troubleshooting.md
│   │       └── tutorial.md
│   ├── local-embedding.md
│   ├── ma01-acceptance.md
│   ├── ma02-acceptance.md
│   ├── minimal-evaluation-baseline-plan.md
│   ├── multi-agent-roadmap.md
│   ├── offline-ingestion.md
│   ├── phase0-acceptance.md
│   ├── phase1-acceptance.md
│   ├── phase1-medical-review.md
│   ├── phase3-acceptance.md
│   ├── phase4-acceptance.md
│   ├── phase5-acceptance.md
│   ├── phase6-acceptance.md
│   ├── phase7-acceptance.md
│   ├── phase7-medical-review.md
│   ├── phase8-acceptance.md
│   ├── phase9-acceptance.md
│   ├── postgres.md
│   ├── research/
│   │   ├── dependencies/
│   │   │   ├── cpu-resolution-results.json
│   │   │   ├── ml-cpu-py312-linux.txt
│   │   │   ├── ml-cpu-py312-windows.txt
│   │   │   ├── ml-py312-linux.txt
│   │   │   ├── ml-py312-windows.txt
│   │   │   ├── ml.in
│   │   │   ├── phase0-py312-linux.txt
│   │   │   ├── phase0-py312-windows.txt
│   │   │   ├── phase0.in
│   │   │   ├── phase1-py312-linux.txt
│   │   │   ├── phase1-py312-windows.txt
│   │   │   ├── phase1.in
│   │   │   └── resolution-results.json
│   │   ├── environment-audit.md
│   │   ├── p0-03-validation.md
│   │   ├── p1-05-model-manifest.json
│   │   ├── pypi-metadata-2026-10-26.json
│   │   └── reference-repository-analysis.md
│   ├── specs/
│   │   ├── 00-project-overview.md
│   │   ├── 01-mvp.md
│   │   ├── 02-async-experience.md
│   │   ├── 03-pico.md
│   │   ├── 04-pubmed-search.md
│   │   ├── 05-hybrid-retrieval.md
│   │   ├── 06-evidence-analysis.md
│   │   ├── 07-citation-report.md
│   │   ├── 08-knowledge-update.md
│   │   ├── 09-evaluation.md
│   │   └── tasks/
│   │       ├── langchain-model-boundary.md
│   │       ├── ma-01-planner-scout.md
│   │       ├── ma-02-feedback.md
│   │       ├── minimal-evaluation-baseline.md
│   │       ├── p1-01-literature-contracts.md
│   │       ├── p1-02-pdf-parsing.md
│   │       ├── p1-03-pubmed-xml.md
│   │       ├── p1-04-source-chunking.md
│   │       ├── p1-05-local-embedding.md
│   │       ├── p1-06-postgres-schema.md
│   │       ├── p1-07-offline-ingestion.md
│   │       ├── p1-08-vector-retrieval.md
│   │       ├── p1-09-basic-rag.md
│   │       ├── p1-10-cli-entrypoints.md
│   │       ├── p1-11-fastapi.md
│   │       ├── p1-12-feishu-events.md
│   │       ├── p1-13-redis-dedup.md
│   │       ├── p1-14-feishu-worker.md
│   │       ├── p1-15-feishu-sender.md
│   │       ├── p1-16-feishu-runtime.md
│   │       ├── p1-17-mvp-acceptance.md
│   │       ├── p3-01-pico.md
│   │       ├── p4-01-pubmed-online.md
│   │       ├── p5-01-hybrid-retrieval.md
│   │       ├── p6-01-evidence-analysis.md
│   │       ├── p7-01-citation-report.md
│   │       ├── p8-01-version-publication.md
│   │       ├── p8-02-update-runs.md
│   │       ├── p8-03-source-governance.md
│   │       ├── p8-completion.md
│   │       ├── p9-evaluation.md
│   │       ├── phase0-acceptance.md
│   │       └── phase0-implementation.md
│   ├── tech-stack.md
│   ├── testing-strategy.md
│   └── vector-retrieval.md
├── evaluation/
│   ├── README.md
│   ├── minimal-v1/
│   │   ├── evidence/
│   │   │   ├── blood-pressure-pubmed.json
│   │   │   ├── continuation-summary.json
│   │   │   ├── e2e-attempt1-summary.json
│   │   │   ├── e2e-attempt2-summary.json
│   │   │   ├── model-calls.json
│   │   │   ├── model-response-1.txt
│   │   │   ├── model-response-2.txt
│   │   │   ├── model-response-3.txt
│   │   │   ├── model-response-4.txt
│   │   │   ├── samples.json
│   │   │   ├── sepsis-pubmed.json
│   │   │   ├── source-audit.json
│   │   │   └── summary.json
│   │   ├── human-labels.json
│   │   ├── manifest.json
│   │   └── source-state.json
│   ├── phase9-v1/
│   │   ├── dataset.json
│   │   ├── observations.json
│   │   └── thresholds.json
│   └── results/
│       ├── local-start-smoke/
│       │   ├── results.json
│       │   └── results.md
│       ├── ma01-baseline-replay/
│       │   ├── migration-checks.json
│       │   ├── results.json
│       │   └── results.md
│       ├── ma02-baseline-replay/
│       │   ├── results.json
│       │   └── results.md
│       ├── minimal-v1/
│       │   ├── results.json
│       │   └── results.md
│       ├── p802-fixed-regression/
│       │   ├── results.json
│       │   └── results.md
│       ├── phase8-completion/
│       │   ├── results.json
│       │   └── results.md
│       ├── phase9-final/
│       │   ├── results.json
│       │   └── results.md
│       ├── phase9-formulas/
│       │   ├── results.json
│       │   └── results.md
│       └── phase9-historical/
│           ├── results.json
│           └── results.md
├── pyproject.toml
├── scripts/
│   ├── audit_repository.py
│   ├── evaluate_minimal_baseline.py
│   ├── evaluate_phase9.py
│   ├── govern_sources.py
│   ├── rebuild_knowledge.py
│   ├── sync_pubmed.py
│   └── update_literature.py
├── src/
│   ├── clinical_agent/
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── embedding.py
│   │   │   ├── langchain_generation.py
│   │   │   ├── llm.py
│   │   │   ├── offline.py
│   │   │   ├── pdf.py
│   │   │   ├── postgres/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── connection.py
│   │   │   │   ├── governance.py
│   │   │   │   ├── maintenance.py
│   │   │   │   ├── models.py
│   │   │   │   ├── online_publication.py
│   │   │   │   ├── rebuild.py
│   │   │   │   ├── retrieval.py
│   │   │   │   ├── store.py
│   │   │   │   ├── update_runs.py
│   │   │   │   └── versions.py
│   │   │   ├── pubmed_online.py
│   │   │   ├── pubmed_xml.py
│   │   │   └── report_snapshot.py
│   │   ├── api.py
│   │   ├── api_runtime.py
│   │   ├── application/
│   │   │   ├── __init__.py
│   │   │   ├── agents.py
│   │   │   ├── analysis.py
│   │   │   ├── evaluation.py
│   │   │   ├── ingestion.py
│   │   │   ├── online_updates.py
│   │   │   ├── pico.py
│   │   │   ├── pubmed.py
│   │   │   ├── report.py
│   │   │   ├── research.py
│   │   │   ├── retrieval.py
│   │   │   ├── updates.py
│   │   │   └── workflow.py
│   │   ├── bootstrap.py
│   │   ├── cli.py
│   │   ├── command_runtime.py
│   │   ├── config.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── analysis.py
│   │   │   ├── chunking.py
│   │   │   ├── citations.py
│   │   │   ├── embedding.py
│   │   │   ├── governance.py
│   │   │   ├── hybrid.py
│   │   │   ├── ingestion.py
│   │   │   ├── maintenance.py
│   │   │   ├── models.py
│   │   │   ├── pico.py
│   │   │   ├── pubmed.py
│   │   │   ├── report.py
│   │   │   ├── research.py
│   │   │   ├── retrieval.py
│   │   │   └── updates.py
│   │   └── logging_config.py
│   └── feishu/
│       ├── __init__.py
│       ├── dedup.py
│       ├── events.py
│       ├── main.py
│       ├── sender.py
│       └── worker.py
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── hybrid/
│   │   │   └── cases.json
│   │   └── pico/
│   │       └── questions.json
│   ├── integration/
│   │   ├── test_api.py
│   │   ├── test_api_pipeline.py
│   │   ├── test_chunking.py
│   │   ├── test_cli.py
│   │   ├── test_command_entrypoints.py
│   │   ├── test_command_pipeline.py
│   │   ├── test_embedding_real.py
│   │   ├── test_evaluation.py
│   │   ├── test_feishu_dedup_redis.py
│   │   ├── test_feishu_runtime_live.py
│   │   ├── test_hybrid_retrieval.py
│   │   ├── test_ingestion.py
│   │   ├── test_knowledge_versions.py
│   │   ├── test_llm.py
│   │   ├── test_offline_reader.py
│   │   ├── test_pdf.py
│   │   ├── test_phase1_acceptance.py
│   │   ├── test_phase8_completion.py
│   │   ├── test_pico.py
│   │   ├── test_postgres.py
│   │   ├── test_pubmed_online.py
│   │   ├── test_pubmed_xml.py
│   │   ├── test_research_live.py
│   │   ├── test_retrieval.py
│   │   ├── test_source_governance.py
│   │   └── test_update_runs.py
│   └── unit/
│       ├── test_agent_roles.py
│       ├── test_api_runtime.py
│       ├── test_bootstrap.py
│       ├── test_chunking.py
│       ├── test_citation_report.py
│       ├── test_command_cli.py
│       ├── test_command_runtime.py
│       ├── test_config.py
│       ├── test_embedding.py
│       ├── test_evaluation.py
│       ├── test_evidence_analysis.py
│       ├── test_feedback_agents.py
│       ├── test_feishu_dedup.py
│       ├── test_feishu_deployment.py
│       ├── test_feishu_events.py
│       ├── test_feishu_main.py
│       ├── test_feishu_sender.py
│       ├── test_feishu_worker.py
│       ├── test_hybrid_retrieval.py
│       ├── test_ingestion.py
│       ├── test_ingestion_mapping.py
│       ├── test_knowledge_update.py
│       ├── test_knowledge_versions.py
│       ├── test_langchain_generation.py
│       ├── test_literature_models.py
│       ├── test_logging_config.py
│       ├── test_minimal_baseline.py
│       ├── test_package.py
│       ├── test_pdf_contracts.py
│       ├── test_phase8_completion.py
│       ├── test_pico.py
│       ├── test_postgres.py
│       ├── test_pubmed_contracts.py
│       ├── test_pubmed_online.py
│       ├── test_research.py
│       ├── test_retrieval.py
│       └── test_source_governance.py
└── uv.lock
```
