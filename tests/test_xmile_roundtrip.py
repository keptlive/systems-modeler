"""Interoperability regressions found by the independent engine review."""
import pytest
from app.core.xmile_parser import parse_xmile
from app.core.xmile_generator import generate_xmile
from app.core.simulator import simulate


def document(variables, dt="<dt reciprocal='true'>4</dt>", namespace="xmlns='http://docs.oasis-open.org/xmile/ns/XMILE/v1.0'"):
    return f"""<xmile {namespace}><header><name>Graph test</name></header>
    <sim_specs method='rk4'><start>0</start><stop>2</stop>{dt}</sim_specs>
    <model><variables>{variables}</variables><views><view>
    <aux name='Graph' x='123' y='456'/></view></views></model></xmile>"""


def test_single_quoted_namespace_and_reciprocal_dt():
    model = parse_xmile(document("<aux name='X'><eqn>TIME</eqn></aux>"))
    assert model.name == "Graph test"
    assert model.time_settings.dt == .25
    assert model.time_settings.integration_method == "rk4"
    assert len(model.variables) == 1


def test_embedded_graph_and_roundtrip_keep_output_type_geometry():
    model = parse_xmile(document("""<aux name='Graph'><eqn>TIME</eqn><gf>
    <xpts>0,1</xpts><ypts>0,10</ypts></gf></aux>
    <aux name='UsesGraph'><eqn>Graph*2</eqn></aux>"""))
    result = simulate(model)
    assert result.values["Graph"][-1] == 10
    assert result.values["UsesGraph"][-1] == 20
    assert model.tables[0].interpolation == "continuous"
    restored = parse_xmile(generate_xmile(model))
    assert restored.time_settings == model.time_settings
    assert restored.variables[0].position == model.variables[0].position
    assert simulate(restored).values == result.values


@pytest.mark.parametrize("kind, expected", [("continuous", 10), ("extrapolate", 20), ("discrete", 10)])
def test_standalone_graphical_function_modes(kind, expected):
    model = parse_xmile(document(f"""<gf name='Curve' type='{kind}'><xpts>0,1</xpts><ypts>0,10</ypts></gf>
    <aux name='Output'><eqn>Curve(TIME)</eqn></aux>"""))
    assert simulate(model).values["Output"][-1] == expected


def test_embedded_flow_graph_is_not_dropped():
    model = parse_xmile(document("""<stock name='X'><eqn>0</eqn><inflow>Input</inflow></stock>
    <flow name='Input'><eqn>TIME</eqn><gf type='extrapolate'><xpts>0,1</xpts><ypts>0,2</ypts></gf></flow>"""))
    result = simulate(model)
    assert result.values["X"][-1] == pytest.approx(4)


def test_empty_wrong_document_is_rejected():
    with pytest.raises(ValueError, match="XMILE"):
        parse_xmile("<anything/>")


def test_unsupported_arrays_do_not_silently_disappear():
    with pytest.raises(ValueError, match="arrays"):
        parse_xmile("<xmile><dimensions/><model><variables/></model></xmile>")


def test_provenance_and_units_survive_native_xmile_roundtrip():
    model = parse_xmile(document("<aux name='X'><eqn>TIME</eqn><units>years</units></aux>"))
    model.source = "https://example.org/source?a=1&b=2"
    model.reference = "A & B (2020)"
    model.description = "Original input assumptions"
    restored = parse_xmile(generate_xmile(model))
    assert restored.source == model.source
    assert restored.reference == model.reference
    assert restored.description == model.description
    assert restored.variables[0].units == "years"


def test_unconnected_flow_is_not_guessed_from_name_on_import():
    from app.core.model import Model
    model = Model(stocks=[{"name": "Population", "initial_value": 10}],
                  flows=[{"name": "Growth estimate", "equation": "Population"}],
                  time_settings={"end": 1, "dt": 1})
    restored = parse_xmile(generate_xmile(model))
    assert restored.flows[0].to_stock is None
    assert simulate(restored).values["Population"] == [10, 10]


def test_embedded_graph_name_does_not_collide_with_other_table():
    from app.core.model import Model
    model = Model(variables=[{"name": "Output", "equation": "LOOKUP('Curve', TIME)"}],
                  tables=[{"name": "Curve", "points": [(0, 0), (1, 10)]},
                          {"name": "Output", "points": [(0, 3), (1, 4)]}],
                  time_settings={"end": 1, "dt": .25})
    restored = parse_xmile(generate_xmile(model))
    assert len({t.name for t in restored.tables}) == len(restored.tables)
    assert simulate(restored).values == simulate(model).values


def test_explicit_flow_link_uses_equation_name_aliases():
    model = parse_xmile(document("""<stock name='X'><eqn>0</eqn><inflow>Net_Change</inflow></stock>
    <flow name='Net Change'><eqn>1</eqn></flow>"""))
    assert simulate(model).values["X"][-1] == pytest.approx(2)


@pytest.mark.parametrize("variables", [
    "<stock name='X'><eqn>0</eqn><inflow>Missing</inflow></stock>",
    "<flow name='Net Change'><eqn>1</eqn></flow><flow name='Net_Change'><eqn>2</eqn></flow>",
    "<stock name='X'><eqn>0</eqn><inflow>F</inflow></stock><stock name='Y'><eqn>0</eqn><inflow>F</inflow></stock><flow name='F'><eqn>1</eqn></flow>",
])
def test_unresolved_or_ambiguous_flow_links_are_rejected(variables):
    with pytest.raises(ValueError):
        parse_xmile(document(variables))


def test_quoted_lookup_input_names_survive_xmile_export():
    from app.core.model import Model
    model = Model(variables=[{"name": "Input amount", "equation": "TIME"},
                            {"name": "Output", "equation": "LOOKUP('Curve', \"Input amount\")"}],
                  tables=[{"name": "Curve", "points": [(0, 0), (1, 10)]}],
                  time_settings={"end": 1, "dt": .25})
    assert simulate(parse_xmile(generate_xmile(model))).values == simulate(model).values


@pytest.mark.parametrize("feature", ["conveyor", "queue", "non_negative", "macros"])
def test_unsupported_simulation_features_do_not_silently_disappear(feature):
    with pytest.raises(ValueError, match="Unsupported XMILE"):
        parse_xmile(document(f"<stock name='X'><eqn>0</eqn><{feature}/></stock>"))


def test_current_draft_export_does_not_save_and_preserves_unsaved_equations(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.storage import models as storage
    monkeypatch.setattr(storage, 'MODELS_DIR', str(tmp_path))
    response = TestClient(app).post('/api/models/export/xmile', json={
        'name':'Δ draft "quoted"', 'variables':[{'name':'X','equation':'2'}],
        'source':'https://example.org/original','time_settings':{'end':1,'dt':1}})
    assert response.status_code == 200
    restored = parse_xmile(response.text)
    assert restored.variables[0].equation == '2'
    assert restored.source == 'https://example.org/original'
    assert not list(tmp_path.iterdir())
