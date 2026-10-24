from app.core.model import Model, Stock, Flow, Variable
from app.core.units import analyze_units, parse_units


def report(variables=(), stocks=(), flows=(), time='year'):
    return analyze_units(Model(variables=list(variables), stocks=list(stocks), flows=list(flows)), time)


def test_stock_flow_and_signed_initializer():
    stock = Stock(id='s', name='Capital', units='dollars', equation='-10')
    good = Flow(name='income', units='dollar/year', equation='2', to_stock='s')
    assert report(stocks=[stock], flows=[good])['status'] == 'consistent'
    bad = good.model_copy(update={'units':'quality/year'})
    assert report(stocks=[stock], flows=[bad])['errors']


def test_expression_checks_independent_of_finite_values():
    values = [Variable(name='money', units='dollar', equation='1'),
              Variable(name='quality', units='quality', equation='2'),
              Variable(name='result', units='quality', equation='money+quality')]
    assert report(values)['status'] == 'inconsistent'
    values[-1].equation = 'money > quality'
    assert report(values)['errors']


def test_dimensionless_fractions_and_powers():
    values = [Variable(name='length', units='meter', equation='3'),
              Variable(name='area', units='meter^2', equation='length^2'),
              Variable(name='ratio', units='dimensionless', equation='length/length')]
    assert report(values)['status'] == 'consistent'
    values[-1].equation = 'LOG(length)'
    assert report(values)['errors']
    values[-1].equation = 'SIN(length)'
    assert report(values)['errors']
    values[-1].equation = 'area^ratio'
    assert report(values)['errors']


def test_missing_units_and_cautious_inference():
    values = [Variable(name='length', units='meter', equation='3'),
              Variable(name='inferred', equation='length*length')]
    result = report(values)
    assert result['status'] == 'incomplete'
    assert result['inferred'][0]['units'] == {'meter':'2'}
    assert values[-1].units is None
    assert report([], time=None)['status'] == 'incomplete'


def test_quoted_aliases_and_static_lazy_branches():
    values = [Variable(name='A Length', units='meter', equation='3'),
              Variable(name='result', units='meter', equation='IF_THEN_ELSE(1, a_length, "A Length")')]
    assert report(values)['status'] == 'consistent'
    values[-1].equation = 'IF_THEN_ELSE(1, a_length, LOG(a_length))'
    assert report(values)['errors']  # Static checks never evaluate either branch.


def test_initial_conditions_and_delay_units():
    values = [Variable(name='money', units='dollar', equation='1'),
              Variable(name='duration', units='year', equation='2'),
              Variable(name='delayed', units='dollar', equation='DELAY1(money,duration,0)')]
    assert report(values)['status'] == 'consistent'
    values[1].units = 'meter'
    assert report(values)['errors']
    stock = Stock(name='Quality', units='quality', equation='money')
    assert report(values[:1], stocks=[stock])['errors']


def test_bounded_grammar_and_no_scale_equivalence():
    assert parse_units('dollars/year') == parse_units('usd/years')
    assert parse_units('hour') != parse_units('second')
    assert report([Variable(name='x', units='meter**999999', equation='1')])['unknown']

def test_n_stage_order_is_dimensionless_and_alias_supported():
    values = [Variable(name='money', units='dollar', equation='1'),
              Variable(name='duration', units='year', equation='2'),
              Variable(name='out', units='dollar', equation='SMTHN(money,duration,3,0)')]
    assert report(values)['status'] == 'consistent'
    values[-1].equation = 'SMTHN(money,duration,money,0)'
    assert report(values)['errors']


def test_lookup_units_remain_unknown_and_parser_failure_is_diagnostic():
    from app.core.model import LookupTable
    model = Model(variables=[Variable(name='out', units='dollar', equation='curve(1)')],
                  tables=[LookupTable(name='curve', points=[(0,0),(1,1)])])
    result = analyze_units(model, 'year')
    assert result['status'] == 'incomplete'
    assert any(item['code'] == 'lookup_axis_units' for item in result['unknown'])
    model.variables[0].equation = '1' * 10001
    assert analyze_units(model, 'year')['unknown']

def test_boolean_is_dimensionless_and_not_a_contextual_number():
    result = report([Variable(name='flag', units='meter', equation='TRUE')])
    assert result['status'] == 'inconsistent'
    assert report([Variable(name='flag', units='meter', equation='1')])['status']=='consistent'


def test_lookup_declared_axes_and_both_call_styles():
    from app.core.model import LookupTable
    model=Model(variables=[Variable(name='x', units='year',equation='1'),
                           Variable(name='y',units='dollar',equation='curve(x)')],
                tables=[LookupTable(name='curve',points=[(0,0),(1,1)],input_units='year',output_units='dollar')])
    assert analyze_units(model,'year')['status']=='consistent'
    model.variables[-1].equation='LOOKUP(curve,x)'
    assert analyze_units(model,'year')['status']=='consistent'
    model.variables[0].units='meter'
    assert analyze_units(model,'year')['errors']
    model.tables[0].output_units=None
    assert analyze_units(model,'year')['unknown']


def test_function_signatures_pow_mod_and_round_precision():
    values=[Variable(name='x',units='meter',equation='1'),
            Variable(name='out',units='meter^2',equation='POW(x,2)')]
    assert report(values)['status']=='consistent'
    values[-1].units='meter'
    values[-1].equation='MOD(x,x)'
    assert report(values)['status']=='consistent'
    values[-1].equation='ROUND(x,x)'
    assert report(values)['errors']
    values[-1].equation='SIN()'
    assert report(values)['status']=='incomplete'
    values[-1].equation='RANDOM_BINOMIAL(x,0.5)'
    assert report(values)['errors']


def test_ambiguous_alias_duplicate_ids_and_missing_equations_never_pass():
    values=[Variable(id='same',name='X',units='meter',equation='1'),
            Variable(id='same',name='x',units='meter',equation='1')]
    assert report(values)['unknown']
    assert report([Variable(name='x',units='meter',equation='')])['status']=='incomplete'


def test_units_arithmetic_limit_is_reported_even_for_stock_time_constraint():
    stock=Stock(id='s',name='x',units='year^-64',equation='1')
    flow=Flow(name='f',units='year^-64',equation='1',to_stock='s')
    assert report(stocks=[stock],flows=[flow])['unknown']
    from pytest import raises
    with raises(ValueError,match='500'):
        report([Variable(name=f'v{i}',units='meter',equation='1') for i in range(501)])

def test_non_ascii_unit_symbols_do_not_silently_nfkc_fold():
    result=report([Variable(name='x',units='ｍ',equation='1')])
    assert result['status']=='incomplete'


def test_clock_units_follow_evaluator_reserved_symbol_precedence():
    values=[Variable(name='TIME',units='meter',equation='1'),
            Variable(name='clock',units='year',equation='TIME')]
    assert report(values)['status']=='consistent'
