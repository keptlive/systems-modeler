from tests.model_history import v18_bytes
"""v1.8 C: portable preservation, primary-source balances and independent ODEs."""
import hashlib,json,math
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from app.core.model import Model
from app.core.simulator import simulate
ROOT=Path(__file__).resolve().parents[1]
RECEIPT=json.loads((ROOT/'operations/corpus-repairs-v18-c.json').read_text())
ROWS={r['index']:r for r in RECEIPT['models']}
def load(i):return Model.model_validate_json(v18_bytes(ROOT,ROWS[i]['file']).decode())
def run(i,end=None,dt=None,**updates):
 m=load(i)
 if i in [72,77,84]:
  # Preserve v1.8 source/geometry receipts above; execute the reviewed solver
  # revision only after confirming these source equations/parameters are equal.
  current=Model.model_validate_json((ROOT/ROWS[i]['file']).read_text())
  for field in ['stocks','flows','variables','tables','connectors']:
   assert getattr(current,field)==getattr(m,field)
  assert (current.time_settings.start,current.time_settings.end)==(m.time_settings.start,m.time_settings.end)
  m=current
 if end is not None:updates['end']=end
 if dt is not None:updates['dt']=dt
 return simulate(m,m.time_settings.model_copy(update=updates))
def independent_rhs(i):
 """Literal mathematics, independent of safe_eval, expression ASTs and engine RHS."""
 if i==43:
  def f(t,y):
   s,n,v,u=y;infection=2.4e-5*s*v
   return [10-.01*s-infection,infection-.7*n,900*n-23*v,0]
  return f
 if i==44:
  def f(t,y):
   s,n,ms,me,mi=y;total=s+n;inf=.5*mi*s/total*.3*(1-.5*.3);vinf=.5*ms*n/total*.5;death=.1*(1+.7*.2)
   return [-inf+n/200,inf-n/200-.0001*n,.1*(ms+me+mi)*(1+.5*np.sin(2*np.pi*t/365))-vinf-death*ms,vinf-me/10-death*me,me/10-death*mi]
  return f
 if i==45:
  def f(t,y):
   s,v,e,n,r=y;total=sum(y);a=15*.125*s*n/total;b=.03*15*.125*v*n/total
   return [-a,-b,a+b-.125*e,.125*e-.125*n,.125*n]
  return f
 if i==47:
  def f(t,y):
   s,e,l,n,r=y;inf=10*s*n/sum(y)
   return [-inf,inf-.5*e,.95*.5*e-.001*l,.05*.5*e+.001*l-2.15*n,2*n]
  return f
 if i==54:
  def f(t,y):
   core,skin,heat=y;e=core-37;vaso=1+max(0,e)
   return [(heat/27-core)/5,(33+2*e*vaso-skin)/2,100+max(0,-50*e)-5*(skin-25)*vaso-3*(skin-25)-2.4*max(0,10*e)]
  return f
 if i==64:
  def f(t,y):
   x,v,z=y;return [2*v-1e6*x*v+10*x-2000*x*x,-2*v-1e6*x*v+.5*z,10*x-.5*z]
  return f
 if i==71:
  def f(t,y):
   x,p,a=y;processing=.08*x*a
   return [.05*x-processing,processing,-.0002*a*x+.1*(100-a)]
  return f
 if i==74:
  def f(t,y):
   unaware,spread,stifle,skeptic,viral=y;n=sum(y[:4]);stop=.2+10*(stifle+skeptic)/n*.1
   hear=10*spread*unaware/n*.1*1.25*viral/100*3.4
   become=spread*.05*(10*skeptic/n+.2);fact=unaware*skeptic/n
   return [-hear-fact,hear-spread*stop-become,spread*stop,become+fact,.8*np.exp(-t/3)*spread*.5-viral*(.1+.5*skeptic/n)]
  return f
 if i==75:
  def f(t,y):
   u,e,g,s,d,q,b=y;n=u+e+g+s+d;eng=e*.1*q/80;sharing=g*.2*1.44
   exposure=u*(s/n*500+.001*(g+s)/1000)*b
   return [-exposure,exposure-eng-.9*e,eng-sharing-g/2,sharing-s,s+g/2+.9*e,-q*.1,(1+2*(eng+sharing)/1000-b)/.5]
  return f
 if i==77:
  def f(t,y):
   d,q,c=y;flow=d*60*(1-d/150)
   return [50*(1+.4*np.sin(t/12*3.14159))-flow,max(0,d-50)*.1-q*.2*(1 if d<50 else .2),flow]
  return f
 if i==79:
  def f(t,y):
   a,b,c,q,d=y;v=[x*60*(1-x/200) for x in [a,b,c]]
   return [500*(1+.5*np.sin((t-8)*3.14159/4))-v[0],v[0]-v[1],v[1]-v[2],max(0,v[1]-400)-min(q/.1,400),q/400*v[1]]
  # QueueDischarge explicitly divides by saved DT; independent reference must
  # use the original .1 output step, not treat step-dependent queue law as PDE.
  return f
 if i==80:
  def f(t,y):
   r,c,n,u,a=y;x=r*.03*a/100;z=c*.01*(a/100)**2;train=u*.1*(1+.01*t)
   return [-x,-z,a*.5*1.02+train,x+z-train,a*.1*1.5]
  return f
 if i==82:
  def f(t,y):
   v,p,c,r,a=y;attack=v*.001*a/100;hard=v*.002
   return [-attack+c/4-hard,hard,attack-c/4,c*.4*250000,r*.3/1e7]
  return f
 if i==83:
  def f(t,y):
   a,p,q,r=y;adopt=p*.01*(1+q/50)*(1+.1*np.log(a/5+1))
   return [adopt-.02*a,-adopt,r*.1*np.log(r/10+1)*(1-q/100),a*.5]
  return f
 if i==84:
  def f(t,y):
   d,q=y;arrival=1500+500*np.sin(t*.5);flow=min(d*60*(1-d/150),2250)
   return [arrival-flow,arrival-2250 if d>120 else 0]
  return f
 raise KeyError(i)
REFERENCE_CASES=[43,44,45,47,54,64,71,74,75,77,80,82,83,84]
def reference(i,times):
 m=load(i);init=[s.initial_value for s in m.stocks]
 method='LSODA' if i in [64,80,83] else 'DOP853'
 # DOP853 is deliberately distinct from the shipped RK4/Radau code.
 if i in [44,75,82]:method='LSODA'
 s=solve_ivp(independent_rhs(i),(m.time_settings.start,float(times[-1])),init,t_eval=times,method=method,rtol=2e-10,atol=1e-11)
 if not s.success:raise AssertionError(s.message)
 return s.y
@pytest.mark.parametrize('i',list(ROWS))
def test_sha_bound_complete_baselines_and_original_identity_geometry_preserved(i):
 row=ROWS[i];before=row['before_text'].encode();old=json.loads(before);d=json.loads(v18_bytes(ROOT,row['file']).decode())
 assert hashlib.sha256(before).hexdigest()==row['before_sha256']==row['baseline_sha256']
 assert hashlib.sha256(v18_bytes(ROOT,row['file'])).hexdigest()==row['after_sha256']
 assert d['id']==old['id'] and d['name']==old['name']
 assert d['connectors']==old['connectors']
 assert {k:v for k,v in d['time_settings'].items() if k!='integration_method'}=={k:v for k,v in old['time_settings'].items() if k!='integration_method'}
 for kind in ['stocks','flows','variables']:
  after={e['id']:e for e in d[kind]} if i!=63 else {e['id']:e for category in ['stocks','flows','variables'] for e in d[category]}
  for e in old[kind]:
   a=after[e['id']];assert a['position']==e['position']
   if kind=='stocks':assert a['initial_value']==e['initial_value']
   if kind=='variables':
    try:float(e['equation'])
    except ValueError:pass
    else:assert a['equation']==e['equation']
  if i not in [45,47,63]:assert len(d[kind])==len(old[kind])
def test_all43_cases_accounted_for_with_no_git_dependency():
 baseline=json.loads((ROOT/'operations/library-full-v170.json').read_text())
 failures=sorted([r for r in baseline['models'] if r['status']=='failed'],key=lambda r:r['file'])
 assert len(ROWS)==43
 assert [r['file'] for r in RECEIPT['models']]==[r['file'] for r in failures[43:86]]
@pytest.mark.parametrize('i',REFERENCE_CASES)
def test_corrected_dynamics_against_independently_written_rhs_and_distinct_solver(i):
 # These old accuracy bounds are tighter than the new explicit defaults.
 # Check their independently reviewed quarter grids, without claiming the
 # defaults meet adaptive-era thresholds (default errors live in v19 B tests).
 dt=Model.model_validate_json((ROOT/ROWS[i]['file']).read_text()).time_settings.dt/4 if i in [77,84] else None
 out=run(i,dt=dt);ref=reference(i,out.time);actual=np.array([out.values[s.name] for s in load(i).stocks])
 scale=1+np.max(np.abs(ref),axis=1,keepdims=True)
 error=np.max(np.abs(actual-ref)/scale)
 # Euler cases are checked for convergence separately; all adaptive/RK4
 # cases must be close to a separately solved RHS, not just finite.
 tolerance=.012 if i in [45,47] else (3e-5 if i==43 else 5e-5)
 assert error<tolerance,(i,error)
 assert np.min(actual)>=-1e-6
 if i==71:assert np.min(actual[2])>=0 and np.max(actual[2])<=100.000001
 if i==83:assert np.max(actual[2])<=100*(1+2*load(i).time_settings.rtol)
@pytest.mark.parametrize('i', [45,47,74,75,76,82])
def test_population_partitions_conserve_original_population(i):
 out=run(i);m=load(i)
 names={45:['Susceptible','Vaccinated','Exposed','Infectious','Recovered'],47:['Susceptible','Latent_Early','Latent_Late','Active_TB','Recovered'],74:['Ignorant (Unaware)','Active Spreaders','Stiflers (Inactive)','Skeptics (Fact-checkers)'],75:['Unaware Users','Exposed Users','Engaged Users','Active Sharers','Disengaged Users'],76:['Potential Users','Active Users','Churned Users','Competitor Users'],82:['Vulnerable Organizations','Protected Organizations','Compromised Organizations']}[i]
 sums=np.sum([out.values[n] for n in names],axis=0)
 if i!=47:assert sums==pytest.approx(np.repeat(sums[0],len(sums)),rel=2e-8,abs=1e-7)
 else:
  assert np.all(np.diff(sums)<=1e-7) # only TB death leaves the population
  assert np.min(sums)>0
@pytest.mark.parametrize('i,onset,low,high,label',[(61,50,1000,1200,'Actual_Demand'),(65,10,0,1,'External_Lactose')])
def test_unit_step_has_authored_amplitude_and_onset(i,onset,low,high,label):
 v=run(i).values[label];t=run(i).time
 assert all(x==low for x,at in zip(v,t) if at<onset)
 assert all(x==high for x,at in zip(v,t) if at>=onset)
def test_vaccine_metric_uses_mathematical_right_hand_limit_and_retains_undefined_cases():
 o=run(57)
 assert o.values['Deaths per Million Vaccines'][0]==pytest.approx(55359)
 tiny=run(57,end=1e-5,dt=1e-5)
 assert tiny.values['Deaths per Million Vaccines'][1]==pytest.approx(o.values['Deaths per Million Vaccines'][0])
 m=load(57)
 for v in m.variables:
  if v.name=='Weekly Supply':v.equation='0'
 for s in m.stocks:
  if s.name=='Available Vaccines':s.initial_value=0
 with pytest.raises(Exception,match='zero'):
  simulate(m)
def test_cyert_elimination_preserves_implicit_condition_and_errors_if_no_fixed_point():
 o=run(58).values
 for k in range(len(o['Search Effort'])):
  expected=1 if o['Profit'][k]<o['Profit Target'][k] or o['Actual Sales'][k]<o['Sales Target'][k] else .2
  assert o['Search Effort'][k]==expected
 m=load(58)
 for s in m.stocks:
  if s.name=='Sales Target':s.initial_value=150
  if s.name=='Profit Target':s.initial_value=0
 with pytest.raises(Exception,match='zero'):simulate(m)
def test_project_quadratic_solves_original_residual_without_certifying_negative_work_stocks():
 o=run(60).values
 for j,p in enumerate(o['Schedule_Pressure']):
  original=max(0,(o['Time_Remaining'][j]-o['Work_Remaining'][j]/(o['Staff'][j]*o['Productivity'][j]))/o['Time_Remaining'][j])
  assert p==pytest.approx(original,abs=1e-10)
 assert min(o['Tasks_To_Do'])<0 and min(o['Staff'])<0

def test_exact_wright_fisher_lattice_absorption_and_independent_pcg64_binomial_draws():
 o=run(49,random_seed=42);p=.5
 stream_seed=int.from_bytes(hashlib.sha256(b'42:drift_increment:1:0:binomial').digest(),'big')
 rng=np.random.Generator(np.random.PCG64(stream_seed));expected=[p]
 for k in range(200):p=float(np.sum(rng.random(200)<p))/200;expected.append(p)
 assert o.values['Allele_Frequency']==pytest.approx(expected,abs=2e-15)
 assert all(0<=x<=1 and abs(200*x-round(200*x))<1e-9 for x in o.values['Allele_Frequency'])
 for initial in [0,1]:
  m=load(49);m.stocks[0].initial_value=initial
  assert simulate(m,m.time_settings.model_copy(update={'random_seed':42})).values['Allele_Frequency']==[initial]*201

def test_kimura_linear_mutation_pool_exact_analytic_solution_on_original_million_horizon():
 o=run(48);t=np.array(o.time);n=30*(1-np.exp(-t));fixed=.00005*(30*t-n)
 assert o.values['Neutral_Mutations']==pytest.approx(n,rel=2e-7,abs=1e-8)
 assert o.values['Fixed_Mutations']==pytest.approx(fixed,rel=2e-7,abs=1e-6)
 assert np.array(o.values['Neutral_Mutations'])+o.values['Fixed_Mutations']+o.values['Lost_Mutations']==pytest.approx(30*t,rel=2e-9,abs=1e-6)
def test_milgram_logistic_exact_solution_cannot_overshoot_population():
 # Retain the stringent v1.8 analytic bound on the reviewed quarter grid;
 # default/half/quarter errors and the counter phase error are tested in v19 B.
 dt=Model.model_validate_json((ROOT/ROWS[72]['file']).read_text()).time_settings.dt/4
 o=run(72,dt=dt);t=np.array(o.time);expected=3e8/(1+(3e8-1)*np.exp(-50*t))
 assert o.values['People_Reached']==pytest.approx(expected,rel=2e-7,abs=1e-5)
 assert max(o.values['People_Reached'])<=3e8*(1+1e-8)
def test_ai_job_population_balance_and_exponential_capability_are_independent_invariants():
 o=run(80);t=np.array(o.time);a=20*np.exp(.15*t)
 assert o.values['AI_Capability']==pytest.approx(a,rel=2e-6)
 total=sum(np.array(o.values[n]) for n in ['Routine_Jobs','Cognitive_Jobs','New_Tech_Jobs','Technological_Unemployment'])
 assert total==pytest.approx(850+.51*(a-20)/.15,rel=2e-6)
def test_reactor_partial_repair_restores_one_precursor_loss_and_negative_doppler_sign():
 m=load(67);by={e.name:e for e in [*m.flows,*m.variables]}
 assert by['Precursor Decay'].from_stock is None
 assert by['Delayed Neutron Release'].from_stock=='stock-delayed-precursors'
 assert by['Temperature Feedback'].equation=='(Fuel_Temperature - Reference_Temperature) * Doppler_Coefficient'
 # Full default still needs an output/work and thermal/fission-unit design;
 # this correct derivative identity does not claim a validated reactor model.


def test_full_beer_all18_original_integrators_match_independent_source_euler_step_scenario():
 m=load(63)
 for v in m.variables:
  if v.name=='R_Customer_Orders':v.equation='100 + STEP(20, 10)'
 out=simulate(m,m.time_settings.model_copy(update={'end':15}))
 # Each of the six source blocks has three INTEG levels. The A FUNCTION OF
 # declarations do not create actual inter-block demand equations.
 for prefix,suffix in [('D_',''),('F_',''),('R_',''),('W_',''),('W_','_0'),('','')]:
  expected,inventory,supply=100.,400.,400.;series=[[expected],[inventory],[supply]]
  for t in out.time[:-1]:
   demand=120 if prefix=='R_' and t>=10 else 100
   acquisition=supply/4;shipment=min(demand,inventory)
   order=max(0,(400-inventory)+expected+.05*(4*expected-supply))
   expected,inventory,supply=expected+.125*(demand-expected),inventory+.125*(acquisition-shipment),supply+.125*(order-acquisition)
   for values,value in zip(series,[expected,inventory,supply]):values.append(value)
  for name,values in zip(['Expected_Customer_Orders','Stock','Supply_Line'],series):
   assert out.values[prefix+name+suffix]==pytest.approx(values,rel=2e-12,abs=1e-9)
 # Both phantom flow declarations are auxiliary aliases with preserved IDs.
 old=json.loads(ROWS[63]['before_text'])
 phantom={f['id'] for f in old['flows'] if 'A FUNCTION OF' in f['equation']}
 assert len(phantom)==2
 assert phantom.issubset({v.id for v in m.variables})
 assert not phantom.intersection({f.id for f in m.flows})

def test_wright_fisher_expected_heterozygosity_matches_exact_discrete_generation_law():
 values=[]
 for seed in range(128):
  p=run(49,end=20,random_seed=seed).values['Allele_Frequency'][-1]
  values.append(2*p*(1-p))
 expected=.5*(1-1/200)**20
 standard_error=np.std(values,ddof=1)/np.sqrt(len(values))
 assert abs(np.mean(values)-expected)<6*standard_error

def test_convection_exact_log_amplitude_exceeds_float_range_independently_of_grid():
 from scipy.optimize import brentq
 coefficient=.0002*9.81*.1**3/(.00014*.00001)
 def log_amplitude(t):
  return math.log(.1)+.1*((coefficient/1708)*(100*t+5*t*t-200*(1-math.exp(-.1*t)))-t)
 limit=math.log(np.finfo(float).max)
 crossing=brentq(lambda t:log_amplitude(t)-limit,0,200)
 assert 33<crossing<34
 assert log_amplitude(200)>limit
 assert ROWS[68]['numerical_status']=='failed'

def test_quantum_log_coordinate_reference_still_exceeds_representable_qubits():
 def f(t,y):
  logq,algorithms,commercial,investment=y
  loge=math.log(.01)-.75*(logq-math.log(100))
  logloss=loge if loge<-30 else math.log(-math.log1p(-math.exp(loge)))
  loss=math.exp(logq+logloss-math.log(10))
  logutility=logq-loss
  utility=math.exp(logutility) if logutility>-745 else 0
  return [.0004*investment,.5*utility*(1+.1*t),.15*algorithms if utility>50 else 0,.15*investment*(1+.1*commercial)]
 def limit(t,y):return y[0]-math.log(np.finfo(float).max)
 limit.terminal=True;limit.direction=1
 s=solve_ivp(f,(0,20),[math.log(100),10,1,1000],method='Radau',rtol=1e-9,atol=1e-10,events=limit)
 assert s.success and len(s.t_events[0])==1
 assert 4<s.t_events[0][0]<5
 assert ROWS[81]['numerical_status']=='failed'
