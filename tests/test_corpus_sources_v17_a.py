"""Independent literal native-source recurrences; no application-generated oracle."""
from tests.model_history import v17_bytes
import hashlib
import json
import math
from pathlib import Path
import pytest
from app.core.model import Model
from app.core.simulator import simulate

ROOT=Path(__file__).resolve().parents[1]


def load(path):
    return Model.model_validate_json(v17_bytes(ROOT,path).decode())


def linear(x):
    points=[(-1,0),(-.25,0),(0,2.5),(.5,15),(1,20),(2,25),(3,25)]
    if x<=-1:return 0.
    for (a,b),(c,d) in zip(points,points[1:]):
        if x<=c:return b+(d-b)*(x-a)/(c-a)
    return 25.


def test_workforce_all_4801_source_grid_points_and_rates():
    result=simulate(load("models/economics/workforce-model-eco.json"))
    r,e,b=5.,50.,500.
    assert result.time==[i/32 for i in range(4801)]
    for i in range(4801):
        hiring=linear((b-500)/500)
        maturation=r/15
        departure=e/35
        completion=min((40*e-20*r)/10+40*r/30,b)
        for name,value in [("Rookies",r),("Experts",e),("Task Backlog",b),("Hiring",hiring),("Task Completion",completion)]:
            assert result.values[name][i]==pytest.approx(value,rel=2e-11,abs=2e-8)
        r,e,b=r+(hiring-maturation)/32,e+(maturation-departure)/32,b+(230-completion)/32
    # Actual dynamics: this cannot pass by omitting stock derivatives.
    assert result.values["Experts"][-1]>3*result.values["Experts"][0]


def test_double_pendulum_all_12801_points_against_literal_source_euler():
    result=simulate(load("models/physics/double-pendulum-phy.json"))
    a,b,u,v=1.,1.,0.,0.
    g,m1,m2,L1,L2=-9.8,10.,10.,10.,10.
    assert result.time==[i/128 for i in range(12801)]
    for i in range(12801):
        for name,value in [("Angular Position",a),("Angular Position 2",b),("Angular Velocity",u),("Angular Velocity 2",v)]:
            assert result.values[name][i]==pytest.approx(value,rel=5e-10,abs=2e-8)
        du=(g*(2*m1+m2)*math.sin(a)-m2*g*math.sin(a-2*b)-2*math.sin(a-b)*m2*(v**2*L2+u**2*L1*math.cos(a-b)))/(L1*(2*m1+m2-m2*math.cos(2*a-2*b)))
        dv=(2*math.sin(a-b)*(u**2*L1*(m1+m2)+g*(m1+m2)*math.cos(a)+v**2*L2*m2*math.cos(a-b)))/(L2*(2*m1+m2-m2*math.cos(2*a-2*b)))
        a,b,u,v=a+u/128,b+v/128,u+du/128,v+dv/128
    assert max(result.values["Angular Position"])-min(result.values["Angular Position"])>1


def test_source_pendulum_euler_drift_is_not_mistaken_for_physical_validation():
    result=simulate(load("models/physics/double-pendulum-phy.json"))
    energies=[]
    for a,b,u,v in zip(*(result.values[n] for n in ["Angular Position","Angular Position 2","Angular Velocity","Angular Velocity 2"])):
        energies.append(1000*u*u+500*v*v+1000*u*v*math.cos(a-b)-1960*math.cos(a)-980*math.cos(b))
    # Explicit Euler has substantial energy drift over this chaotic100s source
    # demonstration. Matching its recurrence is source fidelity, not accuracy.
    assert abs(energies[-1]-energies[0])>100


def test_repair_receipt_preserves_every_existing_identity_layout_input_and_time_setting():
    receipt=json.loads((ROOT/"operations/corpus-reconciliation-v17-a.json").read_text())
    for row in receipt["models"]:
        if not row["changed_fields"]:continue
        current=json.loads(v17_bytes(ROOT,row["file"]).decode())
        raw=v17_bytes(ROOT,row["file"])
        assert hashlib.sha256(raw).hexdigest()==row["after_sha256"]
        for field in ["id","name","connectors","time_settings"]:
            if field in row["preserved_fields"]:assert current.get(field)==row["preserved_fields"][field]
        for kind in ["stocks","flows","variables"]:
            assert [{k:v for k,v in e.items() if k!="equation"} for e in current[kind]]==row["preserved_fields"][kind]

def test_treatment_identifier_repair_matches_independent_authored_compartment_rhs():
    # These are the saved illustrative coefficients, not a claim that the book
    # calibrated this capacity-limited treatment extension.
    result=simulate(load("models/epidemiology/sir-treatment-dynamics-epi.json"))
    s,i,j,r=9990.,10.,0.,0.
    for n in range(len(result.time)):
        for name,value in [("Susceptible",s),("Infected Untreated",i),("Infected Treated",j),("Recovered",r)]:
            assert result.values[name][n]==pytest.approx(value,abs=2e-9)
        assert s+i+j+r==pytest.approx(10000,abs=2e-8)
        infection=.5*s*(i+j)/10000
        treatment=min(50,.3*i)
        recovery_i,recovery_j=.1*i,.2*j
        s,i,j,r=s-.125*infection,i+.125*(infection-treatment-recovery_i),j+.125*(treatment-recovery_j),r+.125*(recovery_i+recovery_j)


def test_cholera_human_population_identity_and_full_authored_rhs():
    result=simulate(load("models/epidemiology/cholera-sirw-model-epi.json"))
    s,i,r,w=9990.,10.,0.,0.
    for n in range(len(result.time)):
        for name,value in [("Susceptible",s),("Infected",i),("Recovered",r),("Water_Bacteria",w)]:
            assert result.values[name][n]==pytest.approx(value,rel=2e-10,abs=2e-7)
        assert s+i+r==pytest.approx(10000,abs=2e-7)
        infection=.2*s*i/(s+i+r)+s*w/(1000000+w)
        recovery,waning,shedding,decay=.2*i,.003*r,10*i,.5*w
        if n+1<len(result.time):
            h=result.time[n+1]-result.time[n]
            s,i,r,w=s+h*(waning-infection),i+h*(infection-recovery),r+h*(recovery-waning),w+h*(shedding-decay)
