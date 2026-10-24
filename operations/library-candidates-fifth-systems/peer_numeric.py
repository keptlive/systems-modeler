"""Independent review: explicit ODE references, not imported author helpers."""
import hashlib,json
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from app.core.model import Model
from app.core.simulator import simulate
D=Path(__file__).parent
rng=np.random.default_rng(2961)
results=[]
for kind in ("holt","three-stage"):
 for case in range(8):
  path=next(D.glob(kind+"*.json"));m=Model.model_validate_json(path.read_text())
  m.time_settings.end=4;m.time_settings.dt=.01
  params={v.name:float(v.equation) for v in m.variables if v.equation.replace(".","",1).isdigit()}
  for v in m.variables:
   if v.name in params:
    params[v.name]*=float(rng.uniform(.3,1.7))
    v.equation=str(params[v.name])
  if kind=="holt":
   y=rng.uniform(.05,1.2,3)
   def rhs(t,y):
    a,b,p=y
    return [params["Growth_1"]*a*(1-a/params["Capacity_1"])-params["Capture_1"]*a*p,
            params["Growth_2"]*b*(1-b/params["Capacity_2"])-params["Capture_2"]*b*p,
            params["Conversion"]*p*(params["Capture_1"]*params["Food_Value_1"]*a+params["Capture_2"]*params["Food_Value_2"]*b-params["Maintenance"])]
  else:
   y=rng.uniform(.0,.8,7);y[1:6:2]*=params["Solid_Mass"]*params["Capacity"];y[6]=0
   def rhs(t,y):
    z=np.zeros(7);prev=params["Feed_Concentration"]
    for j in range(3):
     a,q=y[2*j:2*j+2];c=a/params["Liquid_Volume"]
     uptake=params["Kinetic_Rate"]*(params["Solid_Mass"]*params["Capacity"]*params["Affinity"]*c/(1+params["Affinity"]*c)-q)
     z[2*j]=params["Flow_Rate"]*(prev-c)-uptake;z[2*j+1]=uptake;prev=c
    z[6]=params["Flow_Rate"]*prev
    return z
  for s,value in zip(m.stocks,y):s.initial_value=float(value)
  r=simulate(m);want=solve_ivp(rhs,(0,4),y,t_eval=r.time,method="DOP853",rtol=2e-12,atol=2e-13).y
  got=np.array([r.values[s.name] for s in m.stocks]);error=float(abs(got-want).max())
  np.testing.assert_allclose(got,want,atol=2e-8,rtol=2e-8)
  assert got.min()>-1e-10
  if kind!="holt":
   np.testing.assert_allclose(got.sum(axis=0),y.sum()+params["Flow_Rate"]*params["Feed_Concentration"]*np.array(r.time),atol=1e-11,rtol=0)
  results.append({"model":kind,"case":case,"max_absolute_error":error})
out={"seed":2961,"cases":results,"scope":"Independent explicit DOP853 full-series references; author helpers not imported."}
(D/"PEER-NUMERICAL.json").write_text(json.dumps(out,indent=2)+"\n")
print(len(results),"cases passed",max(x["max_absolute_error"] for x in results))
