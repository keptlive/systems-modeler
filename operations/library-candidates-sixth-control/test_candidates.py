"""Independent finite-state/linear/piecewise reference solutions, not finiteness alone."""
import ast,importlib.util,json,math
from pathlib import Path
import numpy as np
import pytest
from scipy.linalg import expm
from scipy.integrate import solve_ivp
from app.core.model import Model
from app.core.simulator import simulate
from app.core.units import analyze_units
D=Path(__file__).parent;ROOT=D.parents[1]
def model(prefix):return Model.model_validate_json(next(D.glob(prefix+'*.json')).read_text())
def param(m,name,value):next(v for v in m.variables if v.name==name).equation=str(value)
def initial(m,name,value):next(s for s in m.stocks if s.name==name).initial_value=float(value)
def probs(r):return np.array([r.values[f'Probability_{n}_Down'] for n in range(4)]).T

def generator(failure,repair):
 # Independent generator assembled from event semantics in column convention.
 g=np.zeros((4,4))
 for n in range(4):
  if n<3:g[n+1,n]=(3-n)*failure
  if n>0:g[n-1,n]=repair
  g[n,n]=-sum(g[:,n])
 return g

@pytest.mark.parametrize('prefix',['finite-source-','pi-'])
@pytest.mark.parametrize('solver',['euler','rk4','radau'])
def test_defaults_domain_and_units(prefix,solver):
 m=model(prefix);m.time_settings.integration_method=solver;r=simulate(m)
 assert analyze_units(m)['status']=='consistent'
 assert all(np.isfinite(v).all() for v in r.values.values())
 if prefix=='finite-source-':
  p=probs(r);assert p.min()>=-1e-10 and p.max()<=1+1e-10
  np.testing.assert_allclose(p.sum(axis=1),1,atol=3e-9 if solver=='radau' else 1e-12,rtol=0)
  assert min(r.values['Expected_Down'])>=-1e-10 and max(r.values['Expected_Down'])<=3+1e-10
 else:
  assert min(r.values['Actuator'])>=0 and max(r.values['Actuator'])<=1
  assert min(r.values['Output'])>=0 and max(r.values['Output'])<=1

@pytest.mark.parametrize('case',range(12))
def test_repair_full_transient_against_matrix_exponential(case):
 rng=np.random.default_rng(712+case);lam,mu=rng.uniform(.05,1.5,2);p0=rng.dirichlet(np.ones(4))
 m=model('finite-source-');param(m,'Failure_Rate',lam);param(m,'Repair_Rate',mu)
 for n,v in enumerate(p0):initial(m,f'Probability_{n}_Down',v)
 m.time_settings.end=3;m.time_settings.dt=.01;r=simulate(m);g=generator(lam,mu)
 wanted=np.array([expm(g*t)@p0 for t in r.time]);np.testing.assert_allclose(probs(r),wanted,atol=1.5e-8,rtol=0)
 # Exact event-balance identity for expected unavailable machines, independent of stationarity.
 wanted_rate=lam*(3-wanted@np.arange(4))-mu*(1-wanted[:,0])
 actual_rate=lam*np.array(r.values['Expected_Operating'])-mu*np.array(r.values['Repairer_Busy'])
 np.testing.assert_allclose(actual_rate,wanted_rate,atol=8e-8,rtol=0)


def test_repair_stationary_distribution_and_throughput_balance():
 m=model('finite-source-');rho=.2;w=np.array([math.factorial(3)/math.factorial(3-n)*rho**n for n in range(4)]);pi=w/sum(w)
 for n,v in enumerate(pi):initial(m,f'Probability_{n}_Down',v)
 r=simulate(m);np.testing.assert_allclose(probs(r),np.tile(pi,(len(r.time),1)),atol=1e-14,rtol=0)
 assert .2*(3-pi@np.arange(4))==pytest.approx(1-pi[0],abs=1e-15,rel=0)
 assert pi[3]>0 and pi[2]>0 # explicit queue waiting states, no rejected failures.


def test_repair_pure_failure_exact_binomial():
 m=model('finite-source-');param(m,'Repair_Rate',0);m.time_settings.dt=.005;r=simulate(m);p=1-np.exp(-.2*np.array(r.time))
 wanted=np.array([math.comb(3,n)*p**n*(1-p)**(3-n) for n in range(4)]).T
 np.testing.assert_allclose(probs(r),wanted,atol=6e-12,rtol=0)


def test_repair_pure_repair_exact_erlang_cascade():
 m=model('finite-source-');param(m,'Failure_Rate',0);m.time_settings.dt=.005
 initial(m,'Probability_0_Down',0);initial(m,'Probability_3_Down',1);r=simulate(m);t=np.array(r.time);e=np.exp(-t)
 wanted=np.array([1-e*(1+t+t*t/2),e*t*t/2,e*t,e]).T
 np.testing.assert_allclose(probs(r),wanted,atol=6e-10,rtol=0)


def test_repair_zero_rates_preserve_arbitrary_distribution():
 m=model('finite-source-');param(m,'Failure_Rate',0);param(m,'Repair_Rate',0);p0=[.1,.2,.3,.4]
 for n,v in enumerate(p0):initial(m,f'Probability_{n}_Down',v)
 r=simulate(m);assert np.array_equal(probs(r),np.tile(p0,(len(r.time),1)))


def test_pi_unsaturated_full_linear_solution_and_no_tracking_effect():
 m=model('pi-')
 for n,v in [('Setpoint',.5),('Proportional_Gain',.7),('Integral_Gain',.4),('Actuator_Min',-100),('Actuator_Max',100)]:param(m,n,v)
 r=simulate(m);A=np.array([[-.85,.5],[-.4,0]]);equilibrium=np.array([.5,.5]);wanted=np.array([equilibrium+expm(A*t)@(-equilibrium) for t in r.time])
 np.testing.assert_allclose(np.array([r.values['Output'],r.values['Integral_Output']]).T,wanted,atol=3e-11,rtol=0)
 assert r.values['Actuator']==r.values['Command']
 param(m,'Tracking_Rate',0);r0=simulate(m);assert r0.values['Output']==r.values['Output'] and r0.values['Integral_Output']==r.values['Integral_Output']

@pytest.mark.parametrize('reference,y0,limit',[(2,0,1),(-1,.5,0)])
def test_pi_permanently_saturated_exact_piecewise_solution(reference,y0,limit):
 m=model('pi-');param(m,'Setpoint',reference);initial(m,'Output',y0);m.time_settings.dt=.005;r=simulate(m);t=np.array(r.time)
 # a=1/Plant_Time=.5, b=Tracking_Rate=2; I' + b I=A+B exp(-a t).
 a=.5;b=2;coeff=1-b*3;A=coeff*(reference-limit)+b*limit;B=-coeff*(y0-limit)
 y=limit+(y0-limit)*np.exp(-a*t);integral=A/b*(1-np.exp(-b*t))+B*(np.exp(-a*t)-np.exp(-b*t))/(b-a)
 np.testing.assert_allclose(r.values['Output'],y,atol=3e-12,rtol=0)
 np.testing.assert_allclose(r.values['Integral_Output'],integral,atol=2e-9,rtol=0)
 assert set(r.values['Actuator'])=={limit}


def test_pi_without_tracking_unreachable_target_integrates_unbounded():
 m=model('pi-');param(m,'Setpoint',2);param(m,'Tracking_Rate',0);r=simulate(m);t=np.array(r.time)
 np.testing.assert_allclose(r.values['Integral_Output'],t+2*(1-np.exp(-t/2)),atol=5e-12,rtol=0)
 assert r.values['Integral_Output'][-1]>20
 param(m,'Tracking_Rate',2);ra=simulate(m);assert abs(ra.values['Integral_Output'][-1]+1.5)<.001
 assert min(ra.values['Integral_Output'])<0 # signed state is required, no positivity clamp.


def test_pi_default_switching_against_independent_tight_dop853():
 m=model('pi-');r=simulate(m)
 def rhs(t,state):
  y,i=state;e=.8-y;v=3*e+i;u=np.clip(v,0,1)
  return [(u-y)/2,e+2*(u-v)]
 ref=solve_ivp(rhs,(0,20),[0,0],method='DOP853',rtol=2e-12,atol=2e-13,t_eval=r.time,max_step=.02)
 assert ref.success;np.testing.assert_allclose(np.array([r.values['Output'],r.values['Integral_Output']]),ref.y,atol=3e-6,rtol=0)
 assert max(r.values['Command'])>1 and r.values['Actuator'][-1]<1


def test_pi_symmetric_actuator_odd_symmetry():
 m=model('pi-');param(m,'Actuator_Min',-1);r=simulate(m);param(m,'Setpoint',-.8);rn=simulate(m)
 for n in ['Output','Integral_Output','Actuator','Command','Error']:np.testing.assert_allclose(rn.values[n],-np.array(r.values[n]),atol=2e-14,rtol=0)


def test_connectors_and_endpoints_complete():
 for prefix in ('finite-source-','pi-'):
  m=model(prefix);all_elements=[*m.stocks,*m.flows,*m.variables];names={e.name for e in all_elements};ids={s.id for s in m.stocks};edges={(c.from_element,c.to_element) for c in m.connectors}
  for e in [*m.flows,*m.variables]:
   refs={n.id for n in ast.walk(ast.parse(e.equation.replace('^','**'),mode='eval')) if isinstance(n,ast.Name)}&names
   assert all((n,e.name) in edges for n in refs)
  for f in m.flows:assert f.from_stock in ids|{None} and f.to_stock in ids|{None}


def test_no_expanded_or_parameter_abstracted_duplicate():
 spec=importlib.util.spec_from_file_location('screen',ROOT/'operations/library-candidates-third-engineering/duplicate_screen.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
 import subprocess
 paths=[ROOT/n for n in subprocess.check_output(['git','ls-files','models'],cwd=ROOT,text=True).splitlines() if n.endswith('.json')]
 paths += [p for p in (ROOT/'operations').glob('library-candidates*/*.json') if p.parent!=D]
 known=[set(),set()]
 for p in paths:
  raw=json.loads(p.read_text())
  if not isinstance(raw,dict) or not raw.get('stocks') or not raw.get('flows'):continue
  for abstract in (False,True):
   try:known[int(abstract)].add(s.fingerprint(raw,abstract))
   except (ValueError,SyntaxError,RecursionError,TypeError):pass
 for prefix in ('finite-source-','pi-'):
  raw=json.loads(next(D.glob(prefix+'*.json')).read_text())
  for abstract in (False,True):assert s.fingerprint(raw,abstract) not in known[int(abstract)]


@pytest.mark.parametrize('case',range(12))
def test_pi_random_parameters_full_series_independent_dop853(case):
 rng=np.random.default_rng(991+case);kp,ki,kb,G,tau,ref=rng.uniform([.2,.1,0,.5,.5,-1],[4,2,3,2,3,2]);y0,i0=rng.uniform([-.3,-1],[.5,1]);lo=-.5;hi=1.2
 m=model('pi-')
 for n,v in [('Setpoint',ref),('Proportional_Gain',kp),('Integral_Gain',ki),('Tracking_Rate',kb),('Plant_Gain',G),('Plant_Time',tau),('Actuator_Min',lo),('Actuator_Max',hi)]:param(m,n,v)
 initial(m,'Output',y0);initial(m,'Integral_Output',i0);m.time_settings.end=3;m.time_settings.dt=.002;r=simulate(m)
 def rhs(t,state):
  y,i=state;e=ref-y;v=kp*e+i;u=np.clip(v,lo,hi)
  return [(G*u-y)/tau,ki*e+kb*(u-v)]
 want=solve_ivp(rhs,(0,3),[y0,i0],t_eval=r.time,method='DOP853',rtol=2e-12,atol=2e-13,max_step=.01)
 assert want.success;np.testing.assert_allclose(np.array([r.values['Output'],r.values['Integral_Output']]),want.y,atol=2e-6,rtol=0)


def test_pi_default_step_refinement_resolves_switch():
 m=model('pi-');errors=[]
 def rhs(t,state):
  y,i=state;e=.8-y;v=3*e+i;u=min(1,max(0,v))
  return [(u-y)/2,e+2*(u-v)]
 for step in (.02,.01,.005):
  m.time_settings.dt=step;r=simulate(m);ref=solve_ivp(rhs,(0,20),[0,0],method='DOP853',rtol=2e-12,atol=2e-13,t_eval=r.time,max_step=.01)
  errors.append(float(np.max(np.abs(np.array([r.values['Output'],r.values['Integral_Output']])-ref.y))))
 assert errors[-1]<errors[0]/4 and errors[-1]<5e-7
