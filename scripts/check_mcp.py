"""Real SDK handshake/tool/resource/prompt checks. Never calls AI or writes models."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

MODEL = {"name": "MCP regression growth", "stocks": [{"id": "s", "name": "X", "initial_value": 100}],
         "flows": [{"name": "growth", "equation": "X * rate", "to_stock": "s"}],
         "variables": [{"name": "rate", "equation": "0.1"}],
         "time_settings": {"start": 5, "end": 6, "dt": .25, "integration_method": "rk4"}}


def payload(result):
    assert not result.isError, result.content
    return result.structuredContent or json.loads(result.content[0].text)


async def exercise(read, write, pages=True):
    async with ClientSession(read, write) as session:
        initialized = await session.initialize()
        tools = await session.list_tools()
        names = {tool.name for tool in tools.tools}
        assert {"list_models", "get_model", "simulate_model", "validate_model", "compare_scenarios",
                "analyze_model", "export_model_xmile", "generate_model_from_description",
                "modify_existing_model"} <= names
        assert {'open_workspace','inspect_workspace','update_workspace_model','edit_workspace_elements',
                'run_workspace','set_workspace_view','close_workspace'} <= names
        listed = payload(await session.call_tool("list_models", {"search": "growth", "limit": 2}))
        assert listed["returned"] > 0
        mid = listed["models"][0]["id"]
        assert payload(await session.call_tool("get_model", {"model_id": mid}))["id"] == mid
        validation = payload(await session.call_tool("validate_model", {"model_json": MODEL}))
        assert validation["valid"]
        cited = {**MODEL, 'source': 'https://doi.org/10.1016/j.jtbi.2017.11.024',
                 'reference': 'Keeling MJ, Rohani P. Modeling Infectious Diseases in Humans and Animals. Princeton University Press, 2008.'}
        checked = payload(await session.call_tool('validate_model', {'model_json': cited}))
        assert any(issue['code'] == 'citation_mismatch' for issue in checked['issues'])
        assert checked['scientific_validation'] == 'not established'
        investigation = payload(await session.call_tool("investigate_model", {"model_json": MODEL}))
        assert len(investigation["runs"]) == 3
        assert investigation["baseline"]["status"] == "completed"
        random_model = {"variables":[{"name":"Draw","equation":"RANDOM(0,1)"}],
                        "time_settings":{"end":1,"dt":.25}}
        random_run = payload(await session.call_tool("simulate_model", {"model_json": random_model}))
        replay = payload(await session.call_tool("simulate_model", {"model_json":random_model,"random_seed":random_run["random_seed"]}))
        assert random_run["data"] == replay["data"]
        sim = payload(await session.call_tool("simulate_model", {"model_json": MODEL, "max_points": 3}))
        assert sim["time_range"] == [5, 6] and sim["data"]["time"] == [5, 5.5, 6]
        assert abs(sim["summary"]["X"]["final"] - 110.5170918) < .00001
        analysis = payload(await session.call_tool("analyze_model", {"model_json": MODEL}))
        assert analysis["time_points"] == 5
        assert analysis['descriptive']['statistics']['X']['time_weighted_mean'] > 100
        assert analysis['descriptive']['patterns']['X'] == 'exponential_growth'
        scenarios = payload(await session.call_tool("compare_scenarios", {
            "model_id": "bank-balance-with-compound-interest-eco",
            "scenarios": [{"name": "Baseline", "parameters": {}},
                          {"name": "Higher deposits", "parameters": {"Deposits": 10}}]}))
        assert scenarios["scenarios"]["Higher deposits"]["Balance"]["final"] > scenarios["scenarios"]["Baseline"]["Balance"]["final"]
        exported = await session.call_tool("export_model_xmile", {"model_json": MODEL})
        assert not exported.isError and "<xmile" in exported.content[0].text
        invalid = await session.call_tool("simulate_model", {"model_json": MODEL, "dt": 0})
        assert invalid.isError
        missing = await session.call_tool("get_model", {"model_id": "does-not-exist"})
        assert missing.isError
        bounded = await session.call_tool("list_models", {"limit": -1})
        assert bounded.isError
        resource = await session.read_resource("systems://guide")
        assert resource.contents
        assert (await session.read_resource('systems://workspace-guide')).contents
        contract = await session.read_resource('systems://engine')
        assert 'random_seed' in contract.contents[0].text
        model_resource = await session.read_resource(f"systems://models/{mid}")
        assert model_resource.contents
        prompts = await session.list_prompts()
        assert prompts.prompts
        prompt = await session.get_prompt("investigate_system", {"question": "Population growth"})
        assert prompt.messages
        if pages:
            created=payload(await session.call_tool('open_workspace',{'model_json':MODEL}))
            key=created['workspace_key']
            state=payload(await session.call_tool('inspect_workspace',{'workspace_key':key}))
            assert state['revision']==1 and not state['browser']['connected']
            changed=payload(await session.call_tool('edit_workspace_elements',{'workspace_key':key,'expected_revision':1,
                'edits':[{'element_type':'stock','element_id':'s','changes':{'units':'people'}}]}))
            assert changed['model']['stocks'][0]['units']=='people'
            run=payload(await session.call_tool('run_workspace',{'workspace_key':key,'expected_revision':2}))
            assert abs(run['statistics']['X']['final']-110.5170918)<.00001
            view=payload(await session.call_tool('set_workspace_view',{'workspace_key':key,'expected_revision':3,'section':'analytics','fit_diagram':True}))
            assert view['revision']==4
            stale=await session.call_tool('update_workspace_model',{'workspace_key':key,'model_json':MODEL,'expected_revision':1})
            assert stale.isError
            assert payload(await session.call_tool('close_workspace',{'workspace_key':key}))['closed']
        else:
            assert (await session.call_tool('open_workspace',{})).isError
        return {"protocol": initialized.protocolVersion, "tools": sorted(names),
                "library_total": listed["total_in_library"], "analytical_check": "passed",
                "errors_resources_prompts": "passed"}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:13250")
    parser.add_argument("--stdio", action="store_true")
    args = parser.parse_args()
    report = {}
    async with streamablehttp_client(args.url.rstrip("/") + "/mcp/") as (read, write, _):
        report["streamable_http"] = await exercise(read, write)
    async with sse_client(args.url.rstrip("/") + "/mcp/sse") as (read, write):
        report["sse"] = await exercise(read, write)
    if args.stdio:
        params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp_server"],
                                       cwd=str(Path(__file__).resolve().parents[1]))
        async with stdio_client(params) as (read, write):
            report["stdio"] = await exercise(read, write, pages=False)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
