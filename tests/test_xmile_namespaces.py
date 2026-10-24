"""Namespace boundaries preserve scalar compatibility and reject silent changes."""
import pytest
from fastapi.testclient import TestClient
from app.core.xmile_parser import parse_xmile, XmileNamespaceError
from app.core.xmile_generator import generate_xmile
from app.core.model import Model
from app.core.simulator import simulate
from app.main import app
from app.storage import models as storage

NS="http://docs.oasis-open.org/xmile/ns/XMILE/v1.0"
SF="https://stockandflow.live/ns/model"
def document(extra="", ns=NS):
    declaration=f' xmlns="{ns}"' if ns else ""
    return f'<xmile{declaration} xmlns:v="urn:foreign"><sim_specs time_units="second"><start>0</start><stop>1</stop><dt>1</dt></sim_specs><model><variables><stock name="X"><eqn>1</eqn>{extra}</stock></variables></model></xmile>'

@pytest.mark.parametrize("ns",[NS,"http://www.systemdynamics.org/XMILE",""])
def test_existing_vocabularies(ns):
    r=simulate(parse_xmile(document(ns=ns)))
    assert r.values["X"]==[1,1]

def test_prefix_aliases_and_attribute_namespace_rules():
    source=document().replace('xmlns="'+NS+'"','xmlns:x="'+NS+'"')
    import re
    source=re.sub(r'<(/?)(xmile|sim_specs|start|stop|dt|model|variables|stock|eqn)(?=[ >])',r'<\1x:\2',source)
    assert simulate(parse_xmile(source)).values["X"]==[1,1]
    with pytest.raises(XmileNamespaceError):parse_xmile(document().replace('name="X"','v:name="X"'))

@pytest.mark.parametrize("extra",["<v:eqn>999</v:eqn>","<eqn xmlns=''>999</eqn>",
 "<eqn xmlns='http://www.systemdynamics.org/XMILE'>999</eqn>",
 "<v:dimensions><v:dim name='A'/></v:dimensions>","<v:annotation/>"])
def test_foreign_material_actionably_rejected(extra):
    source=document(extra)
    with pytest.raises(XmileNamespaceError) as error:parse_xmile(source)
    assert "Unsupported XMILE namespace" in str(error.value)
    assert "original file" in str(error.value) and "/" in str(error.value)
    assert len(str(error.value))<600
    assert extra in source

@pytest.mark.parametrize("tag",["aux","flow","stock","eqn","sim_specs","gf","dimensions","model","variables"])
def test_foreign_lookalikes_never_execute(tag):
    source=document().replace("</variables>",f"<v:{tag} name='Phantom'><v:eqn>7</v:eqn></v:{tag}></variables>")
    with pytest.raises(XmileNamespaceError):parse_xmile(source)

def test_unknown_root_and_foreign_equation_order():
    with pytest.raises(XmileNamespaceError):parse_xmile(document(ns="urn:foreign"))
    for source in [document("<v:eqn>999</v:eqn>"),document().replace("<eqn>1","<v:eqn>999</v:eqn><eqn>1")]:
        with pytest.raises(XmileNamespaceError):parse_xmile(source)

def test_core_array_and_module_rejections_unchanged():
    for source in [document().replace("<model>","<dimensions><dim name='A'/></dimensions><model>"),
                   document().replace("</xmile>","<model/></xmile>")]:
        with pytest.raises(ValueError,match="Nested models and arrays"):parse_xmile(source)

def test_known_empty_preferences_only():
    for extra in ["<i:prefs xmlns:i='http://iseesystems.com/XMILE' show_module_prefix='true' layer='model'/>",
                  "<i:equation_prefs xmlns:i='isee' order_by='module'/>"]:
        assert simulate(parse_xmile(document().replace("<model>",extra+"<model>"))).values["X"]==[1,1]
        with pytest.raises(XmileNamespaceError):parse_xmile(document().replace("<model>",extra.replace("/>"," >evil</i:"+("prefs" if "i:prefs" in extra else "equation_prefs")+">")+"<model>"))

def test_known_provenance_seed_units_and_graphical_functions():
    raw={"format":"vensim_mdl","text":"Original retained MDL","diagnostics":[]}
    m=Model(source_document=raw,description="description",source="source",reference="reference",category="physics",
      stocks=[{"name":"X","initial_value":1}],variables=[{"name":"Noise","equation":"RANDOM_UNIFORM(0,1)"}],
      time_settings={"end":1,"dt":.25,"random_seed":123,"units":"second"})
    out=parse_xmile(generate_xmile(m))
    assert out.source_document.model_dump()==raw
    for key in ["description","source","reference","category"]:assert getattr(out,key)==getattr(m,key)
    assert out.time_settings.random_seed==123 and out.time_settings.units=="second"
    assert simulate(m).values==simulate(out).values
    with pytest.raises(XmileNamespaceError):parse_xmile(generate_xmile(m).replace("</xmile>","<s:extra xmlns:s='"+SF+"'/></xmile>"))

@pytest.mark.parametrize("source",[document("<v:eqn>999</v:eqn>"),document("<v:annotation/>")])
def test_real_upload_errors_never_save(monkeypatch,source):
    def forbidden(*a,**k):raise AssertionError("Invalid XML must not save")
    monkeypatch.setattr(storage,"create_model",forbidden)
    r=TestClient(app).post("/api/models/import/xmile",files={"file":("original.xmile",source,"application/xml")})
    assert r.status_code==400 and "Unsupported XMILE namespace" in r.json()["detail"]
    assert "<v:" in source

def test_valid_upload_still_returns_model_and_saves_once(monkeypatch):
    saved=[]
    def save(m):saved.append(m);return m
    monkeypatch.setattr(storage,"create_model",save)
    r=TestClient(app).post("/api/models/import/xmile",files={"file":("ok.xmile",document(),"application/xml")})
    assert r.status_code==200 and len(saved)==1 and r.json()["stocks"][0]["name"]=="X"

def test_direct_input_and_traversal_budgets():
    with pytest.raises(ValueError,match="2 MiB"):parse_xmile(" "*2097153)
    with pytest.raises(ValueError,match="nesting limits"):parse_xmile("<xmile>"+"<a>"*129+"</a>"*129+"</xmile>")
    with pytest.raises(ValueError,match="element or nesting"):parse_xmile("<xmile>"+"<a/>"*20001+"</xmile>")
    source=document("<v:"+"x"*2000+"/>")
    with pytest.raises(XmileNamespaceError) as e:parse_xmile(source)
    assert len(str(e.value))<600

def test_prefix_rebinding_and_foreign_content_inside_known_profiles_reject():
    source=document().replace("<eqn>1</eqn>","<c:eqn xmlns:c='"+NS+"'>1</c:eqn><c:eqn xmlns:c='urn:rebound'>999</c:eqn>")
    with pytest.raises(XmileNamespaceError):parse_xmile(source)
    source=document().replace("<model>","<i:prefs xmlns:i='http://iseesystems.com/XMILE'><aux name='Phantom'><eqn>7</eqn></aux></i:prefs><model>")
    with pytest.raises(XmileNamespaceError):parse_xmile(source)
    source=document().replace("<model>","<s:provenance xmlns:s='"+SF+"'><s:source><aux name='Phantom'/></s:source></s:provenance><model>")
    with pytest.raises(XmileNamespaceError):parse_xmile(source)

def test_graphical_function_unit_attributes_and_geometry_preserved():
    m=Model(stocks=[{"name":"X","initial_value":1,"position":{"x":321,"y":654}}],
      variables=[{"name":"Y","equation":"LOOKUP('Curve',X)"}],
      tables=[{"name":"Curve","points":[[0,0],[2,4]],"input_units":"second","output_units":"kg"}],
      time_settings={"end":1,"dt":1})
    out=parse_xmile(generate_xmile(m))
    assert out.tables[0].input_units=="second" and out.tables[0].output_units=="kg"
    assert out.stocks[0].position.x==321 and out.stocks[0].position.y==654
    assert simulate(out).values["Y"]==[2,2]

@pytest.mark.parametrize("character",["\u202e","\u0085","\\"])
def test_escaped_namespace_diagnostics_remain_bounded(character):
    with pytest.raises(XmileNamespaceError) as error:
        parse_xmile(document(ns="urn:"+character*1000))
    assert len(str(error.value))<600
    assert "Unsupported XMILE namespace" in str(error.value)
    assert "Keep the original file" in str(error.value)

@pytest.mark.parametrize("attributes",[
 'xml:lang="en" xml:space="preserve"',
 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:test https://example.invalid/never-fetch.xsd"',
 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://example.invalid/never-fetch.xsd"'])
def test_standard_nonexecuting_annotations_preserved_without_fetch(monkeypatch,attributes):
    import urllib.request
    def forbidden(*args,**kwargs):raise AssertionError("Schema hints must not fetch")
    monkeypatch.setattr(urllib.request,"urlopen",forbidden)
    source=document().replace("<xmile ",f"<xmile {attributes} ",1)
    assert simulate(parse_xmile(source)).values["X"]==[1,1]

@pytest.mark.parametrize("attributes",['xml:base="https://example.invalid/"',
 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="vendor:Altered"'])
def test_unimplemented_qualified_behavior_attributes_still_reject(attributes):
    with pytest.raises(XmileNamespaceError):parse_xmile(document().replace("<xmile ",f"<xmile {attributes} ",1))
