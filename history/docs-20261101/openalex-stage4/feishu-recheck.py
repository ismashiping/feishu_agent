import json
import traceback
from pathlib import Path
from uuid import uuid4
from clinical_agent.command_runtime import open_research
from clinical_agent.domain.research import QuestionRequest
result = {}
try:
    with open_research(Path('/app/model')) as research:
        answer = research.answer(QuestionRequest(question='MedSAM与nnU-Net用于医学图像分割有什么区别？', request_id=uuid4(), scope='hybrid'))
        result = {'status': 'success', 'answer': answer.model_dump(mode='json')}
except Exception as error:
    chain = []
    while error is not None:
        chain.append({'type': type(error).__name__, 'code': error.code if hasattr(error, 'code') else None, 'frames': [{'file': f.filename, 'line': f.lineno, 'function': f.name} for f in traceback.extract_tb(error.__traceback__)]})
        error = error.__cause__ or (None if error.__suppress_context__ else error.__context__)
    result = {'status': 'failed', 'chain': chain}
Path('/tmp/feishu-recheck-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))

