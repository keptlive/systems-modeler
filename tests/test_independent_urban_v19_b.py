"""URBAN audit derived directly from the native MDL, never its generated map."""
import bisect
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pytest

from app.core.model import Model
from app.core.simulator import simulate
from app.core.integration import evaluate
from app.core.equations import SimulationContext, safe_eval

ROOT=Path(__file__).resolve().parents[1]
NATIVE=ROOT/'tests/fixtures/v19_c/URBAN.mdl'
MODEL=ROOT/'models/social/urban-development-feedback-soc.json'


def raw_sections():
    """Read the MDL's equation/unit fields with a line-oriented state machine."""
    text=NATIVE.read_text()
    text=text[:text.index('\\\\\\---///')]
    records=[];fields=[''];field=0
    for character in text:
        if character=='|':
            equation=' '.join(fields[0].replace('\\\n','').split())
            if equation and not equation.startswith(('*','{UTF-8}')):
                records.append((equation,fields[1].strip() if len(fields)>1 else ''))
            fields=[''];field=0
        elif character=='~':
            field+=1;fields.append('')
        else:fields[field]+=character
    equations={};tables={}
    for expression,units in records:
        if '=' in expression:
            name,rhs=expression.split('=',1)
            assert name.strip() not in equations
            equations[name.strip()]=(rhs.strip(),units)
        else:
            name,values=expression.split('(',1)
            flat=[float(v) for v in values[:-1].split(',')]
            assert len(flat)%2==0
            n=len(flat)//2
            tables[name.strip()]=(list(zip(flat[:n],flat[n:])),units)
    return equations,tables


def identifier(name):return re.sub('[^a-zA-Z0-9_]','_',name).strip('_')


def split_integrator(rhs):
    assert rhs.startswith('INTEG(') and rhs.endswith(')')
    expression=rhs[len('INTEG('):-1];depth=0
    for i,c in enumerate(expression):
        if c=='(':depth+=1
        elif c==')':depth-=1
        elif c==',' and depth==0:return expression[:i],expression[i+1:]
    raise AssertionError(rhs)


def interpolate(points,x):
    if x<=points[0][0]:return points[0][1]
    if x>=points[-1][0]:return points[-1][1]
    j=bisect.bisect_right([p[0] for p in points],x)
    a,b=points[j-1],points[j]
    return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])


def native_program():
    equations,tables=raw_sections()
    names={name:identifier(name) for name in [*equations,*tables]}
    assert len(set(n.lower() for n in names.values()))==len(names)
    names_lower={n.lower():v for n,v in names.items()}
    pattern=re.compile('|'.join(r'(?<!\w)'+re.escape(n)+r'(?!\w)' for n in sorted(names,key=len,reverse=True)),re.I)
    def compile_rhs(rhs):
        expression=pattern.sub(lambda m:names_lower[m[0].lower()],rhs)
        expression=re.sub(r'\bTime\b','t',expression,flags=re.I)
        expression=re.sub('IF THEN ELSE','choose',expression,flags=re.I)
        expression=expression.replace('^','**')
        return compile(expression.strip(),'<original URBAN.mdl>','eval')
    auxiliary={};initials={};derivatives={}
    for name,(rhs,units) in equations.items():
        key=names[name]
        if rhs.startswith('INTEG('):
            derivative,initial=split_integrator(rhs)
            derivatives[key]=compile_rhs(derivative);initials[key]=compile_rhs(initial)
        else:auxiliary[key]=compile_rhs(rhs)
    base={'__builtins__':{},'choose':lambda c,a,b:a if c else b,
          'GAME':lambda baseline:baseline,'LN':math.log,'MAX':max,'MIN':min}
    for name,(points,units) in tables.items():
        base[names[name]]=lambda x,points=points:interpolate(points,x)
    def values(stocks,t,initialize=False):
        env={**base,**stocks,'t':t}
        pending={**auxiliary,**(initials if initialize else {})}
        while pending:
            remaining={}
            for name,code in pending.items():
                try:env[name]=float(eval(code,env))
                except NameError:remaining[name]=code
            assert len(remaining)<len(pending),list(remaining)
            pending=remaining
        return env
    def rhs(env):return {name:float(eval(code,env)) for name,code in derivatives.items()}
    return equations,tables,initials,values,rhs


def test_raw_native_coverage_equations_units_initials_and_tables():
    equations,tables,initials,values,rhs=native_program()
    fixture=json.loads((ROOT/'tests/fixtures/v19_c/urban-equation-map.json').read_text())
    model=Model.model_validate_json(MODEL.read_text())
    assert hashlib.sha256(NATIVE.read_bytes()).hexdigest()=='fe7bbd0a26897d2ad2152d6390e3d544dcd861c2ab52eda3922a27a8b49465a4'
    assert len(equations)==255 and len(tables)==53 and len(initials)==20
    assert set(fixture['names'])==set(equations)|set(tables)
    original={row['name']:row for row in fixture['entries']}
    for name,(expression,units) in equations.items():
        assert expression==original[name]['expression']
        assert units==original[name]['units']
    assert {name:float(equations[name][0]) for name in ('INITIAL TIME','FINAL TIME','TIME STEP','SAVEPER')}=={'INITIAL TIME':0,'FINAL TIME':250,'TIME STEP':1,'SAVEPER':5}
    imported={element.name:element for element in [*model.stocks,*model.variables]}
    for name,(expression,units) in equations.items():
        if name in ('INITIAL TIME','FINAL TIME','TIME STEP','SAVEPER'):continue
        element=imported[identifier(name)]
        assert element.units==units
    assert sum(expression.startswith('GAME(') for expression,units in equations.values())==6
    first=values({},0,True)
    assert first['New_Enterprise_Average']==140
    assert first['Premium_Housing_Average']==3500
    assert first['population']==113100
    assert first['Worker_Housing_Average']==pytest.approx(14700,rel=1e-14)
    assert first['Tax_Ratio_Needed_Perc']==first['tax_ratio_needed']
    # Source tables use legacy x-list followed by y-list, not interleaved pairs.
    converted={table.name:table for table in model.tables}
    context=SimulationContext(0,1,{table.name:table.to_list() for table in model.tables},{},{})
    context.table_types={table.name:table.interpolation for table in model.tables}
    for native_name,(points,units) in tables.items():
        name=identifier(native_name);table=converted[name]
        assert table.interpolation=='continuous'
        assert table.points==points
        probes=[points[0][0]-100,points[-1][0]+100]
        probes += [p[0] for p in points]
        probes += [(a[0]+b[0])/2 for a,b in zip(points,points[1:])]
        for x in probes:
            assert safe_eval(f'{name}({x!r})',{},context)==pytest.approx(interpolate(points,x),rel=1e-13)


def test_all20_balances_and250_years_from_raw_native_not_generated_map():
    equations,tables,initials,values,rhs=native_program()
    model=Model.model_validate_json(MODEL.read_text());actual=simulate(model)
    initial=values({},0,True)
    stock_names=list(initials)
    state={name:initial[name] for name in stock_names}
    flows={flow.to_stock:flow for flow in model.flows}
    # Extra non-trajectory states expose symbol substitutions hidden by the baseline.
    for multiplier in (.7,1,1.3):
        candidate={name:value*multiplier for name,value in state.items()}
        source_values=values(candidate,17)
        derivative=rhs(source_values)
        calculated=evaluate(model,candidate,17,1,{}, {})
        for stock in model.stocks:
            assert calculated[flows[stock.id].name]==pytest.approx(derivative[stock.name],rel=2e-12,abs=1e-9)
    for i,t in enumerate(actual.time):
        for name,value in state.items():
            assert actual.values[name][i]==pytest.approx(value,rel=3e-12,abs=1e-7)
        env=values(state,t);derivative=rhs(env)
        state={name:value+derivative[name] for name,value in state.items()}
    assert actual.time[0]==0 and actual.time[-1]==250 and len(actual.time)==251
    by_id={v.id:v for v in model.variables}
    assert by_id['s1'].equation=='Premium_Housing + Worker_Housing + Underemp_Housing'
    assert by_id['s2'].equation=='labor_jobs + Manager_Prof_Jobs + underemployed_jobs'
    assert by_id['s3'].name=='population'
    # Population is persons, not the unweighted sum of worker-category counts.
    np.testing.assert_allclose(actual.values['population'],
                              5*np.array(actual.values['Manager_Professional'])+
                              6*np.array(actual.values['Labor'])+
                              8*np.array(actual.values['Underemployed']),rtol=2e-14)
