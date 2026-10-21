from tests.model_history import v18_bytes
"""Portable receipts and independent equation/math checks for corpus partition B, v1.8."""
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import solve_ivp
from app.core.model import Model
from app.core.simulator import simulate
from app.core.integration import evaluate

ROOT = Path(__file__).resolve().parents[1]
LEDGER = json.loads((ROOT / "operations/corpus-repairs-v18-b.json").read_text())
ROWS = LEDGER["models"]

@lru_cache(None)
def run(index):
    model = Model.model_validate_json(v18_bytes(ROOT, ROWS[index]["file"]).decode())
    if index == 1:
        # The historical receipt remains bound to v1.8. Numerical checks use
        # the reviewed explicit solver; its source equations/tables are equal.
        current = Model.model_validate_json((ROOT / ROWS[index]["file"]).read_text())
        for field in ("stocks", "flows", "variables", "tables", "connectors"):
            assert getattr(current,field) == getattr(model,field)
        assert (current.time_settings.start,current.time_settings.end) == (model.time_settings.start,model.time_settings.end)
        model = current
    return model, simulate(model)


def test_portable_receipts_and_preserved_product_elements():
    assert [row["index"] for row in ROWS] == list(range(43))
    for row in ROWS:
        assert row["diagnosis"] and row["missing_evidence"] and row["sources"]
        assert all(k in row["current_probes"] for k in ("default", "half_dt", "quarter_dt", "ode_reference"))
        before = row["before_text"].encode()
        assert hashlib.sha256(before).hexdigest() == row["before_sha256"]
        after = v18_bytes(ROOT, row["file"])
        assert hashlib.sha256(after).hexdigest() == row["after_sha256"]
        old, new = json.loads(before), json.loads(after)
        assert old["id"] == new["id"]
        for kind in ("stocks", "flows", "variables", "connectors"):
            assert len(old.get(kind, [])) == len(new.get(kind, []))
            for a, b in zip(old.get(kind, []), new.get(kind, [])):
                assert a.get("id") == b.get("id")
                assert a.get("position") == b.get("position")
        for field in ("start", "end", "dt"):
            assert old["time_settings"][field] == new["time_settings"][field]


@pytest.mark.parametrize("index", [1,3,5,11,12,20,22,23,25,27,33,39,40,41])
def test_repaired_defaults_finish_and_have_finite_stocks(index):
    model, result = run(index)
    assert result.time[-1] == model.time_settings.end
    assert all(math.isfinite(v) for stock in model.stocks for v in result.values[stock.name])
    if index not in (5,20):  # Temperature anomaly and monetary profit may be signed.
        assert all(min(result.values[stock.name]) >= -1e-6 for stock in model.stocks)


def test_source_quantity_corrections_and_counterexamples():
    # SI radiation already W/m²; the previous million divisor produced an energy imbalance.
    model, _ = run(11)
    v = evaluate(model, {s.name:s.initial_value for s in model.stocks}, 0, model.time_settings.dt, {}, {})
    assert v["Outgoing Radiation"] == pytest.approx(v["Emissivity"] * 5.67e-8 * (15+273.15)**4)
    assert v["Outgoing Radiation"] > 200
    # The absolute birth count P/(70*365) must not be multiplied by P again.
    model, _ = run(40)
    v = evaluate(model, {s.name:s.initial_value for s in model.stocks}, 0, model.time_settings.dt, {}, {})
    assert v["Births"] == pytest.approx(v["Population"]/(70*365))
    assert v["Births"] < v["Population"] / 1000
    # Profit/Cost already has units vessels: duplicating Fleet causes an erroneous quadratic exit.
    model, _ = run(25)
    values = {s.name:s.initial_value for s in model.stocks}
    v = evaluate(model, values, 0, model.time_settings.dt, {}, {})
    assert v["Fleet_Exit"] == pytest.approx(v["Exit_Rate"] * abs(v["Profit"]) / v["Cost"])
    assert v["Fleet_Exit"] * model.time_settings.dt < values["Fishing_Fleet"]
    for i in (5,12):
        model,_ = run(i)
        assert next(s for s in model.stocks if s.name in ("Atmospheric CO2","Atmospheric_CO2")).units == "GtC"
    model,_ = run(12)
    at_equilibrium={s.name:(588 if s.name == "Atmospheric_CO2" else s.initial_value) for s in model.stocks}
    assert evaluate(model, at_equilibrium, 2015, 5, {}, {})["Forcing"] == pytest.approx(0)


def test_unique_zero_limit_and_algebraic_elimination():
    model,_ = run(22)
    for a,d in [(0,0),(1e-12,0),(0,1e-12),(2,3)]:
        stocks={s.name:s.initial_value for s in model.stocks}
        stocks.update(Active_Threats=a, Defense_Capability=d)
        val=evaluate(model, stocks, 0, model.time_settings.dt, {}, {})
        attack=val["Successful_Attacks"]
        assert 0 <= attack <= val["Attack_Success_Rate"]*a
        if a+d: assert attack == pytest.approx(val["Attack_Success_Rate"]*a*a/(a+d))
    model,_ = run(33)
    for inventory in (.1,1,10,100,10000):
        stocks={s.name:s.initial_value for s in model.stocks}
        stocks["Inventory"]=inventory
        val=evaluate(model, stocks, 0, model.time_settings.dt, {}, {})
        assert val["Demand"] == pytest.approx(100*(val["Reference_Price"]/val["Market_Price"])**val["Price_Elasticity_Demand"])


def independent_rhs(index):
    # Handwritten equations, independent of parsing/evaluation/model flows.
    if index==20:
        def rhs(t,y):
            b,w,p,e=y; true=50+10*math.sin(t/20); signal=true+5*math.sin(t/3)
            return [(signal-b)*.3*(1+e/100),(b*(1+.2/1.5)-w)*.5,true-w,-p*.1 if p<0 else p*.05]
        return rhs
    if index==23:
        def rhs(t,y):
            u,v=y; match=.7*math.sqrt(u)*math.sqrt(v)
            return [.03*(1-u)-match, .5*((1-.7)/(.03+.05))-match]
        return rhs
    if index==27:
        def rhs(t,y):
            n,p,z=y; uptake=2*n*p/(1+n); grazing=.6*z*p/(1+p)
            return [-uptake+.1*p+.2*z,uptake-grazing-.1*p,.3*grazing-.2*z]
        return rhs
    if index==39:
        def rhs(t,y):
            s,i,r,a,j,q=y; nc=s+i+r; na=a+j+q
            f=.3*(15*i/nc+5*j/na)*s; g=.3*(5*i/nc+10*j/na)*a
            return [-f,f-i/7,i/7,-g,g-j/7,j/7]
        return rhs
    if index==41:
        def rhs(t,y):
            target,infected,virus,immune=y; inf=1e-8*target*virus
            return [-inf,inf-(.5+.01*immune)*infected,100*infected-5*virus,.001*infected]
        return rhs
    raise AssertionError(index)


@pytest.mark.parametrize("index", [20,23,27,39,41])
def test_opt_in_radau_against_independent_equations(index):
    model,result=run(index)
    assert model.time_settings.integration_method == "radau"
    ts=model.time_settings
    times=np.linspace(ts.start,ts.end,17)
    reference=solve_ivp(independent_rhs(index),(ts.start,ts.end),[s.initial_value for s in model.stocks],method="Radau",rtol=1e-10,atol=1e-11,t_eval=times)
    assert reference.success
    for k,stock in enumerate(model.stocks):
        actual=np.interp(times,result.time,result.values[stock.name])
        # Compare at common saved grid points, not interpolation through sharp peaks.
        saved=np.searchsorted(result.time,times)
        mask=np.abs(np.asarray(result.time)[saved]-times)<1e-9
        np.testing.assert_allclose(actual[mask],reference.y[k,mask],rtol=2e-5,atol=1e-5)
    if index==39:
        values=result.values
        np.testing.assert_allclose(np.array(values["S_Children"])+values["I_Children"]+values["R_Children"],2010,atol=1e-7)
        np.testing.assert_allclose(np.array(values["S_Adults"])+values["I_Adults"]+values["R_Adults"],6005,atol=1e-7)
    if index==27:
        # This authored model is open: unassimilated grazing is an unresolved export, not fabricated recycling.
        rhs=independent_rhs(27); n,p,z=10,1,.5
        assert sum(rhs(0,[n,p,z])) == pytest.approx(-.7*.6*z*p/(1+p))


WORLD2_SOURCE_TABLES = {'BRMM': [1, [1.2, 1, 0.85, 0.75, 0.7, 0.7]], 'BRCM': [1, [1, 0.95, 0.8, 0.7, 0.65, 0.65]], 'BRFM': [1, [0, 1, 1.6, 1.9, 2]], 'BRPM': [5, [1, 0.97, 0.92, 0.82, 0.72, 0.6, 0.4]], 'DRMM': [0.5, [2, 1.4, 1, 0.8, 0.7, 0.6, 0.53, 0.5, 0.5, 0.5, 0.5]], 'DRCM': [1, [1, 1.1, 1.3, 1.6, 2.1, 3]], 'DRFM': [0.25, [30, 3, 2, 1.4, 1, 0.7, 0.6, 0.5, 0.5]], 'DRPM': [5, [0.98, 1.1, 1.3, 1.6, 2.1, 2.8, 4]], 'NREM': [0.25, [0, 0.15, 0.5, 0.85, 1]], 'NRMM': [1, [0, 1, 1.8, 2.4, 2.9, 3.3, 3.6, 3.8, 3.9, 3.95, 4]], 'FPCI': [1, [0.5, 1, 1.4, 1.7, 1.9, 2.05, 2.2]], 'FCM': [1, [2.4, 1, 0.6, 0.4, 0.3, 0.2]], 'FPM': [5, [1, 0.95, 0.87, 0.77, 0.65, 0.5, 0.32]], 'CIM': [1, [0.1, 1, 1.8, 2.4, 2.8, 3]], 'POLCM': [1, [0.05, 1, 3, 5.4, 7.4, 8]], 'POLAT': [5, [1, 1.4, 2.4, 3.6, 5.2, 7.2, 10]], 'CFIFR': [0.5, [1, 0.6, 0.3, 0.15, 0.1]], 'CIQR': [0.5, [0.7, 0.8, 1, 1.5, 2]], 'QLM': [1, [0.2, 1, 1.7, 2.3, 2.7, 2.9]], 'QLC': [0.5, [2, 1.3, 1, 0.75, 0.55, 0.45, 0.38, 0.3, 0.25, 0.22, 0.2]], 'QLF': [1, [0, 1, 1.8, 2.4, 2.7]], 'QLP': [5, [1.1, 1, 0.88, 0.71, 0.55, 0.35, 0.12]]}

def test_world2_primary_documentor_independent_rhs():
    model,result=run(1)
    # Preserve the old pointwise tolerance on the reviewed quarter grid. The
    # current default is documented/tested separately with trajectory-max scaling.
    result=simulate(model,model.time_settings.model_copy(update={"dt":model.time_settings.dt/4}))
    def table(name,x):
        dx,ys=WORLD2_SOURCE_TABLES[name]
        return float(np.interp(x,np.arange(len(ys))*dx,ys))
    assert len(model.tables)==22
    for t in model.tables:
        dx,ys=WORLD2_SOURCE_TABLES[t.name.removeprefix("World2_")]
        np.testing.assert_allclose(t.points,[(i*dx,y) for i,y in enumerate(ys)])
    def rhs(t,y):
        p,c,n,pol,a=y; cir=c/p; crowd=p/(135e6*26.5); pollution=pol/3.6e9
        m=cir*(1-a)*table("NREM",n/900e9)/.7
        food=table("FPCI",cir*a/.3)*table("FCM",crowd)*table("FPM",pollution)
        births=p*.045*table("BRMM",m)*table("BRCM",crowd)*table("BRFM",food)*table("BRPM",pollution)
        deaths=p*.025*table("DRMM",m)*table("DRCM",crowd)*table("DRFM",food)*table("DRPM",pollution)
        desired=table("CFIFR",food)*table("CIQR",table("QLM",m)/table("QLF",food))
        return [births-deaths,p*.05*table("CIM",m)-c*.025,-p*table("NRMM",m),p*table("POLCM",cir)-pol/table("POLAT",pollution),(desired-a)/15]
    ref=solve_ivp(rhs,(1900,2100),[1650e6,400e6,900e9,200e6,.3],method="Radau",rtol=1e-10,atol=1e-10,t_eval=result.time)
    assert ref.success
    for k,stock in enumerate(model.stocks):
        np.testing.assert_allclose(result.values[stock.name],ref.y[k],rtol=1e-5,atol=1e-6)
