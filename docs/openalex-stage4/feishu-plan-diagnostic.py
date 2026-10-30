import json
from pathlib import Path
from pydantic import ValidationError
from clinical_agent.adapters.llm import LLMSettings, open_llm
from clinical_agent.domain.pico import ClassificationRequest, ExtractionDraft
with open_llm(LLMSettings()) as generator:
    raw = generator.extract(ClassificationRequest(question='MedSAM与nnU-Net用于医学图像分割有什么区别？'), timeout_seconds=20)
Path('/tmp/feishu-plan-diagnostic.json').write_text(raw, encoding='utf-8')
try:
    ExtractionDraft.model_validate_json(raw)
    print('schema_valid')
except ValidationError as error:
    print(json.dumps(error.errors(include_input=False, include_context=False), ensure_ascii=False))
