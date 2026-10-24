"""Independent proposed regressions; local only, no filesystem model storage."""
import pytest
import xml.etree.ElementTree as ET
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.model import Model, generate_connectors_from_equations
from app.core.simulator import simulate
from app.core.xmile_generator import generate_xmile
from app.core.xmile_parser import parse_xmile
from app.api import models as routes

PAIRS=[("A-B","A_B"),("A\u2002B","A_B"),("Cash$Balance","Other")]

def authored(first,second):
    equation=f'"{first}"+"{second}"' if "$" not in first else f'{first}+"{second}"'
    return Model(name="Identifier review", stocks=[{"id":"stock","name":"Stored$Total","initial_value":0}],
        flows=[{"name":"Accrual$Rate","equation":equation,"to_stock":"stock"}],
        variables=[{"name":first,"equation":"1"},{"name":second,"equation":"2"},
                   {"name":"Output","equation":equation}],
        time_settings={"start":0,"end":2,"dt":.25})

def verify(model,first,second):
    result=simulate(model)
    assert result.values["Output"]==[3]*9
    assert result.values["Stored$Total"]==pytest.approx([3*t for t in result.time])
    edges={(c.from_element,c.to_element) for c in generate_connectors_from_equations(model)}
    for target in ("Output","Accrual$Rate"):
        assert {(first,target),(second,target)} <= edges
    stock=next(s for s in model.stocks if s.name=="Stored$Total")
    flow=next(f for f in model.flows if f.name=="Accrual$Rate")
    assert flow.to_stock in (stock.id,stock.name)

@pytest.mark.parametrize("first,second",PAIRS)
def test_json_roundtrip(first,second):
    model=authored(first,second)
    restored=Model.model_validate_json(model.model_dump_json())
    assert restored.model_dump()==model.model_dump()
    verify(restored,first,second)

@pytest.mark.parametrize("first,second",PAIRS)
def test_xml_export_import_roundtrip(first,second):
    model=authored(first,second)
    parsed=parse_xmile(generate_xmile(model))
    assert [(v.name,v.equation) for v in parsed.variables]==[(v.name,v.equation) for v in model.variables]
    verify(parsed,first,second)

@pytest.mark.parametrize("first,second",PAIRS)
def test_actual_import_api_in_memory_only(monkeypatch,first,second):
    calls=[]
    def create(model):
        calls.append(model)
        return model
    monkeypatch.setattr(routes.storage,"create_model",create)
    app=FastAPI()
    app.include_router(routes.router,prefix="/api/models")
    model=authored(first,second)
    root=ET.Element("xmile",version="1.0")
    specs=ET.SubElement(root,"sim_specs")
    for tag,value in (("start","0"),("stop","2"),("dt",".25")):
        ET.SubElement(specs,tag).text=value
    variables=ET.SubElement(ET.SubElement(root,"model"),"variables")
    stock=ET.SubElement(variables,"stock",name="Stored$Total")
    ET.SubElement(stock,"eqn").text="0"
    ET.SubElement(stock,"inflow").text="Accrual$Rate"
    flow=ET.SubElement(variables,"flow",name="Accrual$Rate")
    ET.SubElement(flow,"eqn").text=model.flows[0].equation
    for variable in model.variables:
        node=ET.SubElement(variables,"aux",name=variable.name)
        ET.SubElement(node,"eqn").text=variable.equation
    xml=ET.tostring(root,encoding="unicode")
    with TestClient(app) as client:
        response=client.post("/api/models/import/xmile",files={"file":("review.xmile",xml,"application/xml")})
    assert response.status_code==200,response.text
    assert len(calls)==1
    verify(Model.model_validate(response.json()),first,second)

@pytest.mark.parametrize("first,second",PAIRS)
def test_source_dependency_graph_distinct_bindings(first,second):
    model=authored(first,second)
    before=[(v.name,v.equation) for v in model.variables]
    edges={(c.from_element,c.to_element) for c in generate_connectors_from_equations(model)}
    assert [(v.name,v.equation) for v in model.variables]==before
    for target in ("Output","Accrual$Rate"):
        assert {(first,target),(second,target)} <= edges

@pytest.mark.parametrize("reverse",[False,True])
def test_unresolved_exact_declaration_cannot_take_computed_legacy_alias(reverse):
    # A-B is deliberately after its alias: dependency planning must wait for9.
    variables=[{"name":"A_B","equation":"2"},{"name":"Output","equation":'"A-B"'},
               {"name":"A-B","equation":"Later"},{"name":"Later","equation":"9"}]
    if reverse: variables.reverse()
    model=Model(variables=variables,time_settings={"start":0,"end":1,"dt":.25})
    for candidate in (model,Model.model_validate_json(model.model_dump_json()),parse_xmile(generate_xmile(model))):
        assert simulate(candidate).values["Output"]==[9]*5


def test_punctuation_stock_ids_and_distinct_flow_links_survive_xml():
    model=Model(stocks=[{"id":"id-1","name":"Store-A","initial_value":10},
                         {"id":"id_1","name":"Store_A","initial_value":20}],
        flows=[{"name":"Flow-A","equation":"1","from_stock":"id-1","to_stock":"id_1"},
               {"name":"Flow_A","equation":"2","from_stock":"id_1","to_stock":"id-1"}],
        time_settings={"start":0,"end":1,"dt":.25})
    for candidate in (model,parse_xmile(generate_xmile(model))):
        result=simulate(candidate)
        assert result.values["Store-A"]==pytest.approx([10+t for t in result.time])
        assert result.values["Store_A"]==pytest.approx([20-t for t in result.time])
        assert set(f.name for f in candidate.flows)=={"Flow-A","Flow_A"}


def test_distinct_punctuation_lookup_tables_survive_xml():
    model=Model(tables=[{"name":"Curve-A","points":[[0,1],[1,1]]},
                        {"name":"Curve_A","points":[[0,2],[1,2]]}],
        variables=[{"name":"Output","equation":'"Curve-A"(TIME)+"Curve_A"(TIME)'}],
        time_settings={"start":0,"end":1,"dt":.25})
    for candidate in (model,Model.model_validate_json(model.model_dump_json()),parse_xmile(generate_xmile(model))):
        assert {t.name for t in candidate.tables}=={"Curve-A","Curve_A"}
        assert simulate(candidate).values["Output"]==[3]*5

def test_independent_xml_flow_names_do_not_collapse():
    xml="""<xmile version="1.0"><sim_specs><start>0</start><stop>1</stop><dt>.25</dt></sim_specs>
    <model><variables>
    <stock name="Store-A"><eqn>10</eqn><outflow>Flow-A</outflow><inflow>Flow_A</inflow></stock>
    <stock name="Store_A"><eqn>20</eqn><inflow>Flow-A</inflow><outflow>Flow_A</outflow></stock>
    <flow name="Flow-A"><eqn>1</eqn></flow><flow name="Flow_A"><eqn>2</eqn></flow>
    </variables></model></xmile>"""
    model=parse_xmile(xml)
    byname={f.name:f for f in model.flows}
    assert byname["Flow-A"].from_stock != byname["Flow_A"].from_stock
    result=simulate(model)
    assert result.values["Store-A"]==pytest.approx([10+t for t in result.time])
    assert result.values["Store_A"]==pytest.approx([20-t for t in result.time])
