# 实际迁移映射

旧路径均保留同模块别名，不删除兼容入口。application/domain继续原位。

| 旧模块 | 唯一实现 |
| --- | --- |
| `clinical_agent.adapters.embedding` | `clinical_agent.rag.embedding` |
| `clinical_agent.adapters.offline` | `clinical_agent.rag.offline` |
| `clinical_agent.adapters.pdf` | `clinical_agent.rag.pdf` |
| `clinical_agent.adapters.pubmed_xml` | `clinical_agent.rag.pubmed_xml` |
| `clinical_agent.adapters.llm` | `clinical_agent.integrations.llm` |
| `clinical_agent.adapters.langchain_generation` | `clinical_agent.integrations.langchain_generation` |
| `clinical_agent.adapters.openalex` | `clinical_agent.integrations.openalex` |
| `clinical_agent.adapters.pubmed_online` | `clinical_agent.integrations.pubmed_online` |
| `clinical_agent.adapters.oa_fulltext` | `clinical_agent.integrations.oa_fulltext` |
| `clinical_agent.adapters.report_snapshot` | `clinical_agent.integrations.report_snapshot` |
| `clinical_agent.adapters.postgres.connection` | `clinical_agent.db.connection` |
| `clinical_agent.adapters.postgres.fulltext` | `clinical_agent.db.fulltext` |
| `clinical_agent.adapters.postgres.governance` | `clinical_agent.db.governance` |
| `clinical_agent.adapters.postgres.maintenance` | `clinical_agent.db.maintenance` |
| `clinical_agent.adapters.postgres.models` | `clinical_agent.db.models` |
| `clinical_agent.adapters.postgres.online_publication` | `clinical_agent.db.online_publication` |
| `clinical_agent.adapters.postgres.rebuild` | `clinical_agent.db.rebuild` |
| `clinical_agent.adapters.postgres.retrieval` | `clinical_agent.db.retrieval` |
| `clinical_agent.adapters.postgres.store` | `clinical_agent.db.store` |
| `clinical_agent.adapters.postgres.update_runs` | `clinical_agent.db.update_runs` |
| `clinical_agent.adapters.postgres.versions` | `clinical_agent.db.versions` |
