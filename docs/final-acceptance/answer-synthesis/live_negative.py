"""One real generation against a verified negative source, no search/ESearch claim."""
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from dotenv import dotenv_values

from clinical_agent.adapters.llm import LLMSettings, open_llm
from clinical_agent.adapters.pubmed_xml import parse_pubmed_response
from clinical_agent.domain.citations import parse_draft
from clinical_agent.domain.research import GenerationInput, ResearchError

folder = Path(__file__).resolve().parent
root = folder.parents[2]
settings = dotenv_values(root / '.artifacts/docker-e2e/compose.env')
data = {key.lower()[4:]: value for key, value in settings.items()
        if key in {'LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL', 'LLM_MAX_TOKENS'}}
record = parse_pubmed_response(
    (folder / 'organ-segmentation.xml').read_bytes(), fetched_at=datetime.now(UTC)
)[0]
identity = uuid5(NAMESPACE_URL, record.source_url + record.content_hash)
context = GenerationInput(
    question='有没有关于肝脏肿瘤内部亚区划分的研究？有哪些代表性论文，采用了什么亚区划分方法？',
    evidence=[dict(title=record.title, pmid=record.pmid, chunk_id=identity,
                   text=record.abstract, content_scope='abstract',
                   location=dict(kind='abstract', start=0, end=len(record.abstract)))],
)
result = {'kind': 'real generation / fixed negative source; NOT natural retrieval',
          'calls': 0, 'context_characters': len(context.model_dump_json()),
          'context': context.model_dump(mode='json')}
assert result['context_characters'] <= 24000
try:
    configured = LLMSettings(**data)
    result['model'] = configured.model
    with open_llm(configured) as generator:
        model = generator._model

        class Meter:
            def invoke(self, *args, **kwargs):
                result['calls'] += 1
                message = model.invoke(*args, **kwargs)
                result['usage'] = message.usage_metadata
                return message

        generator._model = Meter()
        raw = generator.generate(context, timeout_seconds=60.0)
        draft = parse_draft(raw, max_bytes=32000)
        assert all(c.evidence_chunk_ids == [identity] for c in draft.claims)
        result['draft'] = draft.model_dump(mode='json')
except ResearchError as error:
    result['error'] = error.code
except Exception as error:
    result['error'] = type(error).__name__  # never log provider errors or credentials
(folder / 'live-negative.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8'
)
print(json.dumps({k: v for k, v in result.items() if k not in {'context', 'draft'}},
                 ensure_ascii=False))
