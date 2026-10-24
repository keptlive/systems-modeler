import pytest
from app.core.model import Model, Stock, Flow, Variable, SimulationResult
from app.core.feedback_analysis import analyze_feedback


def linear(rate):
    return Model(stocks=[Stock(id='s',name='Population',initial_value=10)],
                 flows=[Flow(name='change',to_stock='s',equation=f'{rate}*Population')])


def states(**values):
    return SimulationResult(time=[0,1], values=values)


def test_growth_and_decay_are_quantitative_not_graph_labels():
    for rate, label in [(0.2,'locally_amplifying'),(-0.3,'locally_contracting')]:
        out = analyze_feedback(linear(rate),states(Population=[10,12]))
        assert out['dominance'] == 'not_computed'
        assert out['samples'][0]['jacobian'][0][0] == pytest.approx(rate)
        assert out['samples'][0]['indication'] == label
        assert out['scientific_validity'] == 'not_established'


def test_logistic_changes_local_feedback_sign():
    model = linear(.2)
    model.flows[0].equation = '0.2*Population*(1-Population/100)'
    out = analyze_feedback(model,states(Population=[10,90]))
    assert out['samples'][0]['jacobian'][0][0] == pytest.approx(.16)
    assert out['samples'][1]['jacobian'][0][0] == pytest.approx(-.16)


def test_two_stock_oscillator_eigenvalues_and_algebraic_paths():
    model = Model(stocks=[Stock(id='x',name='x'),Stock(id='y',name='y')],
                  variables=[Variable(name='twice_y',equation='2*y')],
                  flows=[Flow(name='dx',to_stock='x',equation='twice_y'),
                         Flow(name='dy',to_stock='y',equation='-2*x')])
    out = analyze_feedback(model,states(x=[1,2],y=[2,1]))
    sample = out['samples'][0]
    assert sample['jacobian'][0][1] == pytest.approx(2)
    assert sample['jacobian'][1][0] == pytest.approx(-2)
    assert sorted(e['imag'] for e in sample['eigenvalues']) == pytest.approx([-2,2])
    assert sample['indication'] == 'marginal_or_neutral'


def test_cusp_is_unresolved_and_does_not_mutate_model():
    model = linear(1)
    model.flows[0].equation = 'ABS(Population)'
    before = model.model_dump()
    result = analyze_feedback(model,states(Population=[0,0]))
    assert result['samples'][0]['indication'] == 'unresolved'
    assert model.model_dump() == before


def test_delay_and_random_and_discrete_are_explicitly_unsupported():
    model = linear(1)
    for equation in ['DELAY1(Population,1)', 'RANDOM_UNIFORM(0,1)']:
        model.flows[0].equation = equation
        with pytest.raises(ValueError,match='Hidden-state'):
            analyze_feedback(model, states(Population=[1,2]))


def test_budget_limits_and_trajectory_shape():
    with pytest.raises(ValueError,match='sample_count'):
        analyze_feedback(linear(1),states(Population=[1,2]),sample_count=17)
    with pytest.raises(ValueError,match='series'):
        analyze_feedback(linear(1),states(Population=[1]))


def test_physical_boundary_failure_reports_partial():
    model=linear(1)
    model.flows[0].equation='SQRT(Population)'
    result=analyze_feedback(model,states(Population=[0,1]))
    assert result['status']=='partial'
    assert result['samples'][0]['status']=='unresolved'

def test_provenance_unverified_and_hash_mismatch_and_stale_equations():
    model=linear(.2)
    result=states(Population=[10,12])
    assert analyze_feedback(model,result)['provenance']['status']=='unverified'
    result.integration_diagnostics={'normalized_model_sha256':'incorrect'}
    with pytest.raises(ValueError,match='provenance hash'):
        analyze_feedback(model,result)
    result.integration_diagnostics=None
    result.values['change']=[99,99]
    report=analyze_feedback(model,result)
    assert report['status']=='partial'
    assert 'disagrees' in report['samples'][0]['reason']


def test_report_text_is_excluded_from_numeric_rates():
    model=linear(.2)
    model.variables=[Variable(name='label',role='report',equation='"hello"')]
    assert analyze_feedback(model,states(Population=[10,12]))['samples'][0]['indication']=='locally_amplifying'


def test_http_requires_explicit_result_and_never_runs_a_simulation(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    import app.api.simulate as route
    def forbidden(*args,**kwargs):
        raise AssertionError('Analysis must not run a simulation')
    monkeypatch.setattr(route,'simulate',forbidden)
    client=TestClient(app)
    model=linear(.2).model_dump(mode='json')
    assert client.post('/api/feedback',json={'model':model}).status_code==422
    response=client.post('/api/feedback',json={'model':model,'result':states(Population=[10,12]).model_dump(mode='json')})
    assert response.status_code==200,response.text
    assert response.json()['dominance']=='not_computed'
    assert response.json()['samples'][0]['jacobian'][0][0]==pytest.approx(.2)
    response=client.post('/api/feedback',json={'model':model,'result':states(Population=[10,12]).model_dump(mode='json'),'sample_count':17})
    assert response.status_code==422


def test_http_structured_feedback_and_units_are_read_only():
    from copy import deepcopy
    from fastapi.testclient import TestClient
    from app.main import app
    raw={'dimensions':[{'name':'Region','elements':['A','B']}],
         'stocks':[{'name':'Population','dimensions':['Region'],'units':'person','initial_value':10}],
         'variables':[{'name':'rate','units':'1/year','equation':'0.2'}],
         'flows':[{'name':'births','dimensions':['Region'],'units':'person/year','to_stock':'Population[Region]','equation':'Population[Region]*rate'}],
         'time_settings':{'units':'year','end':1,'dt':1}}
    before=deepcopy(raw)
    client=TestClient(app)
    units=client.post('/api/units',json={'model':raw})
    assert units.status_code==200,units.text
    assert units.json()['status']=='consistent',units.text
    result={'time':[0,1],'values':{'Population[A]':[10,12],'Population[B]':[10,12]}}
    response=client.post('/api/feedback',json={'model':raw,'result':result})
    assert response.status_code==200,response.text
    assert response.json()['samples'][0]['jacobian'][0][0]==pytest.approx(.2)
    assert raw==before
