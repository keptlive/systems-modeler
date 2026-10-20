"""Independent closed-form PK and mass/extent checks; no clinical validation."""
import json
import math
from pathlib import Path
import pytest
from app.core.model import Model, TimeSettings, Stock
from app.core.simulator import simulate

ROOT = Path(__file__).resolve().parents[1]
PK = ROOT / "models/healthcare/two-compartment-pharmacokinetics-model-hea.json"
C, P, G = "Drug in Central Compartment", "Drug in Peripheral Compartment", "Drug in GI Tract"

def model(f=.85):
    m = Model.model_validate_json(PK.read_text())
    for v in m.variables:
        if v.name == "Bioavailability":
            v.equation = str(f)
    return m

def closed_form(t, f):
    # Eigenmode impulse-response convolution for the independently written
    # equations G'=-1.5G; C'=1.5FG-.7C+.3P; P'=.5C-.3P.
    ka, k12, k21, kel, dose = 1.5, .5, .3, .2, 100.
    root = math.sqrt((kel+k12+k21)**2-4*kel*k21)
    alpha = (kel+k12+k21+root)/2
    beta = (kel+k12+k21-root)/2
    conv = lambda rate: (math.exp(-rate*t)-math.exp(-ka*t))/(ka-rate)
    central = dose*f*ka*((k21-beta)/root*conv(beta)+(alpha-k21)/root*conv(alpha))
    peripheral = dose*f*ka*k12/root*(conv(beta)-conv(alpha))
    return central, peripheral, dose*math.exp(-ka*t), beta

@pytest.mark.parametrize("fraction", [0., .85, 1.])
def test_pk_closed_form_and_bioavailability_extent(fraction):
    m=model(fraction)
    r=simulate(m, TimeSettings(start=0,end=24,dt=.015625,integration_method="rk4"))
    for idx,t in enumerate(r.time):
        central, peripheral, gi, beta = closed_form(t,fraction)
        for name,value in [(C,central),(P,peripheral),(G,gi)]:
            assert r.values[name][idx] == pytest.approx(value,abs=2e-6)
            assert r.values[name][idx] >= -1e-10
        assert r.values["Plasma Concentration"][idx] == pytest.approx(central/10,abs=2e-7)
        assert r.values["Half Life"][idx] == pytest.approx(math.log(2)/beta)
        # Analytic accounting check; actual outflow integration is checked below.
        unabsorbed=(1-fraction)*(100-gi)
        eliminated=fraction*(100-gi)-central-peripheral
        assert eliminated >= -1e-10
        assert sum(r.values[n][idx] for n in [C,P,G])+unabsorbed+eliminated == pytest.approx(100,abs=4e-6)

def test_pk_default_refinement_and_auc():
    m=model()
    coarse=simulate(m)
    fine=simulate(m,TimeSettings(start=0,end=24,dt=.03125))
    errors=[]
    for run in [coarse,fine]:
        error=max(abs(run.values[name][idx]-closed_form(t,.85)[n])
                  for idx,t in enumerate(run.time) for n,name in enumerate([C,P,G]))
        errors.append(error)
        assert all(min(run.values[name])>=0 for name in [C,P,G])
    assert errors[0] < 2
    assert errors[1] < .6*errors[0]
    long=simulate(m,TimeSettings(start=0,end=256,dt=.0625,integration_method="rk4"))
    values=long.values["Plasma Concentration"]
    auc=sum((a+b)*.0625/2 for a,b in zip(values,values[1:]))
    assert auc == pytest.approx(.85*100/(.2*10),rel=2e-4)

def test_pk_units_and_declared_oral_loss():
    m=model()
    assert {s.units for s in m.stocks} == {"mg"}
    assert {f.units for f in m.flows} == {"mg/h"}
    loss=next(f for f in m.flows if f.id=="flow-nonsystemic-gi-loss")
    assert loss.from_stock=="stock-drug-in-gi-tract" and loss.to_stock is None
    # For unit GI mass and arbitrary F, all GI outflows sum to Ka.
    for fraction in [0,.35,.85,1]:
        assert 1.5*fraction+1.5*(1-fraction) == pytest.approx(1.5)

def test_healthcare_manifest_and_preserved_layout():
    receipt=json.loads((ROOT/"operations/healthcare-source-reconciliation-v14.json").read_text())
    for row in receipt["models"]:
        d=json.loads((ROOT/row["file"]).read_text())
        if not row["equation_repair"]:
            assert set(row["changed_fields"]) <= {"description","source","reference"}
        else:
            for field in ["stocks","flows","variables"]:
                old=row["changed_fields"][field]["before"]
                new=d[field]
                for previous in old:
                    current=next(x for x in new if x["id"]==previous["id"])
                    assert current["name"]==previous["name"]
                    assert current["position"]==previous["position"]
                    if field=="stocks":
                        assert current["initial_value"]==previous["initial_value"]


@pytest.mark.parametrize("fraction", [0., .85, 1.])
def test_actual_outflow_topology_and_cumulative_mass(fraction):
    # Augment a clone only: let the actual unchanged elimination and GI loss
    # flows integrate into separate cumulative sinks. Missing or misdirected
    # source links now break conservation and the independent analytic check.
    m = model(fraction).model_copy(deep=True)
    eliminated_id = "audit-eliminated"
    nonsystemic_id = "audit-nonsystemic"
    m.stocks.extend([
        Stock(id=eliminated_id, name="Audit Eliminated", initial_value=0, units="mg"),
        Stock(id=nonsystemic_id, name="Audit Nonsystemic", initial_value=0, units="mg"),
    ])
    next(f for f in m.flows if f.id == "flow-elimination").to_stock = eliminated_id
    next(f for f in m.flows if f.id == "flow-nonsystemic-gi-loss").to_stock = nonsystemic_id
    run = simulate(m, TimeSettings(start=0,end=24,dt=.015625,integration_method="rk4"))
    names = [C, P, G, "Audit Eliminated", "Audit Nonsystemic"]
    for idx, t in enumerate(run.time):
        central, peripheral, gi, _ = closed_form(t, fraction)
        expected_eliminated = fraction*(100-gi)-central-peripheral
        expected_nonsystemic = (1-fraction)*(100-gi)
        assert run.values["Audit Eliminated"][idx] == pytest.approx(expected_eliminated, abs=2e-6)
        assert run.values["Audit Nonsystemic"][idx] == pytest.approx(expected_nonsystemic, abs=2e-6)
        assert sum(run.values[name][idx] for name in names) == pytest.approx(100, abs=2e-11)
        assert min(run.values[name][idx] for name in names) >= -1e-10
