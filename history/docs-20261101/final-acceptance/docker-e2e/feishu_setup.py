import json,httpx
from pathlib import Path
from dotenv import dotenv_values
v=dotenv_values('.env');p=Path('.artifacts/docker-e2e/compose.env');env=dotenv_values(p)
a=v.get('CLINICAL_AGENT_FEISHU_APP_ID') or v.get('FEISHU_APP_ID');s=v.get('CLINICAL_AGENT_FEISHU_APP_SECRET') or v.get('FEISHU_APP_SECRET')
result={}
with httpx.Client(trust_env=False,timeout=10) as c:
 t=c.post('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',json={'app_id':a,'app_secret':s}).json()
 result['auth_code']=t.get('code')
 if t.get('code')==0:
  b=c.get('https://open.feishu.cn/open-apis/bot/v3/info',headers={'Authorization':'Bearer '+t['tenant_access_token']}).json()
  result.update(bot_code=b.get('code'),bot_name=b.get('bot',{}).get('app_name'),activate_status=b.get('bot',{}).get('activate_status'))
  if b.get('code')==0:
   env.update(CLINICAL_AGENT_FEISHU_APP_ID=a,CLINICAL_AGENT_FEISHU_APP_SECRET=s,CLINICAL_AGENT_FEISHU_BOT_OPEN_ID=b['bot']['open_id'])
   p.write_text(''.join(k+'='+str(val)+'\n' for k,val in env.items() if val),encoding='utf-8')
Path('docs/final-acceptance/docker-e2e/feishu-config-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
