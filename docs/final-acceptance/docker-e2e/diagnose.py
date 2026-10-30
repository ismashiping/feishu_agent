import traceback
from pathlib import Path
from clinical_agent.command_runtime import open_research
try:
 with open_research(Path('/app/model')) as service: print('runtime_ready')
except Exception as e:
 print(type(e).__name__, getattr(e,'name',''), getattr(e,'code',''))
 print(''.join(traceback.format_tb(e.__traceback__)))

