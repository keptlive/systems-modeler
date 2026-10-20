"""Real MCP -> visible page acceptance. Handoff file contains a temporary secret.

Create, open its URL in the browser, then exercise. Never commit the handoff file.
"""
import argparse,asyncio,json,os,time
from pathlib import Path
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MODEL={'name':'Agent-driven balance','description':'Synthetic agent/page acceptance example.',
       'source':'https://example.org/synthetic-model','reference':'Synthetic QA; not a financial forecast',
       'stocks':[{'id':'s','name':'Balance','initial_value':100,'units':'units','position':{'x':260,'y':240}}],
       'flows':[{'id':'f','name':'Deposits','equation':'5','to_stock':'s','units':'units/year','position':{'x':100,'y':240}}],
       'time_settings':{'start':5,'end':6,'dt':.25,'integration_method':'rk4'}}
def payload(result):
    assert not result.isError,result.content
    return result.structuredContent or json.loads(result.content[0].text)
async def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['create','exercise','close'])
    parser.add_argument('--url',default='http://127.0.0.1:13250');parser.add_argument('--handoff',required=True)
    args=parser.parse_args();path=Path(args.handoff)
    async with streamablehttp_client(args.url.rstrip('/')+'/mcp/') as (read,write,_):
        async with ClientSession(read,write) as client:
            await client.initialize()
            if args.mode=='create':
                state=payload(await client.call_tool('open_workspace',{'model_json':MODEL}))
                state['page_url']=args.url.rstrip('/')+'/#workspace='+state['workspace_key']
                path.write_text(json.dumps(state));os.chmod(path,0o600)
                print(json.dumps({'created':True,'secret_handoff':str(path)}));return
            state=json.loads(path.read_text());key=state['workspace_key']
            if args.mode=='close':
                payload(await client.call_tool('close_workspace',{'workspace_key':key}));path.unlink();print('Closed private workspace');return
            state=payload(await client.call_tool('inspect_workspace',{'workspace_key':key}))
            assert state['browser']['connected'] and state['browser']['applied_revision']==state['revision'],state['browser']
            changed=payload(await client.call_tool('edit_workspace_elements',{'workspace_key':key,'expected_revision':state['revision'],
                'edits':[{'element_type':'flow','element_id':'f','changes':{'equation':'10'}}]}))
            assert changed['model']['source']==MODEL['source'] and changed['model']['stocks'][0]['units']=='units'
            run=payload(await client.call_tool('run_workspace',{'workspace_key':key,'expected_revision':changed['revision']}))
            assert run['statistics']['Balance']['final']==110
            view=payload(await client.call_tool('set_workspace_view',{'workspace_key':key,'expected_revision':run['revision'],'section':'analytics','fit_diagram':True}))
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                applied=payload(await client.call_tool('inspect_workspace',{'workspace_key':key}))
                if applied['browser']['applied_revision']==view['revision'] and not applied['browser']['error']:break
                await asyncio.sleep(.4)
            else:raise AssertionError('Page did not acknowledge the agent update: '+str(applied['browser']))
            print(json.dumps({'agent_edits':'passed','shared_run_final':110,'page_applied_revision':applied['browser']['applied_revision'],
                'source_units_preserved':True,'ai_provider_calls':0,'library_writes':0}))
asyncio.run(main())
