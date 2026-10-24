"""Independent analytic limits and domain budgets; no finite-only validity claim."""
import ast,json,math,importlib.util
from pathlib import Path
import numpy as np
import pytest
from app.core.model import Model
from app.core.simulator import simulate
from app.core.units import analyze_units
D=Path(__file__).parent;ROOT=D.parents[1]
def model(prefix):return Model.model_validate_json(next(D.glob(prefix+'*.json')).read_text())
def param(m,name,value):next(v for v in m.variables if v.name==name).equation=str(value)
def initial(m,name,value):next(s for s in m.stocks if s.name==name).initial_value=value

@pytest.mark.parametrize('prefix',['holt-','three-stage-'])
@pytest.mark.parametrize('solver',['euler','rk4','radau'])
def test_default_finite_and_domain(prefix,solver):
 m=model(prefix);m.time_settings.integration_method=solver;r=simulate(m)
 assert len(r.time)>1 and all(np.isfinite(v).all() for v in r.values.values())
 for s in m.stocks:assert min(r.values[s.name])>=-1e-9
 if prefix=='three-stage-':
  for j in (1,2,3):assert max(r.values[f'Sorbed_Mass_{j}'])<=2+1e-8
  np.testing.assert_allclose(r.values['Tracked_Mass'],.5*np.array(r.time),atol=3e-8 if solver=='radau' else 2e-10,rtol=0)

@pytest.mark.parametrize('prefix',['holt-','three-stage-'])
def test_symbolic_units_consistent(prefix):assert analyze_units(model(prefix))['status']=='consistent'

def test_holt_no_predator_logistic_both_independent_prey():
 m=model('holt-');initial(m,'Predator',0);r=simulate(m);t=np.array(r.time)
 for n,r0,K,rate in [('Prey_1',.9,1.5,1),('Prey_2',.6,1.2,.8)]:
  want=K/(1+(K/r0-1)*np.exp(-rate*t));np.testing.assert_allclose(r.values[n],want,atol=2e-9,rtol=0)
 assert set(r.values['Predator'])=={0}

def test_holt_empty_prey_predator_exponential_decay():
 m=model('holt-');initial(m,'Prey_1',0);initial(m,'Prey_2',0);r=simulate(m)
 np.testing.assert_allclose(r.values['Predator'],.2*np.exp(-.25*np.array(r.time)),atol=2e-11,rtol=0)
 assert set(r.values['Prey_1'])==set(r.values['Prey_2'])=={0}

def test_holt_solved_equilibrium_and_shared_enemy_comparison():
 m=model('holt-');equilibrium={'Prey_1':.4,'Prey_2':.375,'Predator':11/12}
 for name,v in equilibrium.items():initial(m,name,v)
 r=simulate(m)
 for name,v in equilibrium.items():np.testing.assert_allclose(r.values[name],v,atol=2e-14,rtol=0)
 # Equilibrium with prey2 absent has prey1=.625 and predator=35/48.
 initial(m,'Prey_1',.625);initial(m,'Prey_2',0);initial(m,'Predator',35/48);r=simulate(m)
 np.testing.assert_allclose(r.values['Prey_1'],.625,atol=2e-14,rtol=0)
 np.testing.assert_allclose(r.values['Predator'],35/48,atol=2e-14,rtol=0)
 assert .4<.625 and 11/12>35/48

def test_holt_symmetric_species_and_zero_conversion_limits():
 m=model('holt-')
 for a,b in [('Growth_2',1),('Capacity_2',1.5),('Capture_2',.8),('Food_Value_2',1)]:param(m,a,b)
 initial(m,'Prey_2',.9);r=simulate(m);assert r.values['Prey_1']==r.values['Prey_2']
 m=model('holt-');param(m,'Conversion',0);r=simulate(m);assert set(r.values['Predator'])=={.2}
 for name,start,rate,capacity in [('Prey_1',.9,.84,1.26),('Prey_2',.6,.68,1.02)]:
  want=capacity/(1+(capacity/start-1)*np.exp(-rate*np.array(r.time)));np.testing.assert_allclose(r.values[name],want,atol=2e-9,rtol=0)

def test_adsorption_kinetic_zero_exact_three_tank_step_front():
 m=model('three-stage-');param(m,'Kinetic_Rate',0);r=simulate(m);t=np.array(r.time);z=.5*t
 for j in (1,2,3):
  want=1-np.exp(-z)*sum(z**k/math.factorial(k) for k in range(j))
  np.testing.assert_allclose(r.values[f'Concentration_{j}'],want,atol=3e-10,rtol=0)
  assert set(r.values[f'Sorbed_Mass_{j}'])=={0}
 np.testing.assert_allclose(r.values['Effluent_Mass'],.5*t-sum(np.array(r.values[f'Aqueous_Mass_{j}']) for j in (1,2,3)),atol=2e-11,rtol=0)


def test_closed_adsorber_mass_budget_implicit_transient_and_equilibrium():
 m=model('three-stage-');param(m,'Flow_Rate',0);initial(m,'Aqueous_Mass_1',3);m.time_settings.end=10;m.time_settings.dt=.01;r=simulate(m);a=np.array(r.values['Aqueous_Mass_1']);s=np.array(r.values['Sorbed_Mass_1']);t=np.array(r.time)
 np.testing.assert_allclose(a+s,3,atol=2e-13,rtol=0)
 root=np.sqrt(3)
 def integral(x):return .5*np.log(x*x-3)+np.log((x-root)/(x+root))/(2*root)
 np.testing.assert_allclose(integral(a)-integral(3),-.5*t,atol=3e-8,rtol=0)
 m.time_settings.end=60;m.time_settings.dt=.02;r=simulate(m);assert abs(r.values['Aqueous_Mass_1'][-1]-root)<2e-12
 for j in (2,3):assert set(r.values[f'Aqueous_Mass_{j}'])==set(r.values[f'Sorbed_Mass_{j}'])=={0}
 assert set(r.values['Effluent_Mass'])=={0}

@pytest.mark.parametrize('zero',['Capacity','Affinity','Solid_Mass'])
def test_adsorber_zero_binding_parameters_reduce_to_unretarded_front(zero):
 m=model('three-stage-');param(m,zero,0);r=simulate(m);t=np.array(r.time);z=.5*t
 np.testing.assert_allclose(r.values['Concentration_3'],1-np.exp(-z)*(1+z+z*z/2),atol=3e-10,rtol=0)
 for j in (1,2,3):assert set(r.values[f'Sorbed_Mass_{j}'])=={0}


def test_actual_euler_mass_transfer_matches_independent_random_rhs():
 rng=np.random.default_rng(8019)
 for _ in range(60):
  m=model('three-stage-');m.time_settings.end=m.time_settings.dt=1e-6;m.time_settings.integration_method='euler'
  a=rng.uniform(0,4,3);V=float(rng.uniform(.5,2));solid=float(rng.uniform(.5,2));capacity=float(rng.uniform(.5,3));feed=float(rng.uniform(.1,2));s=rng.uniform(0,solid*capacity,3);eff=float(rng.uniform(0,2));Q=float(rng.uniform(0,2));kin=float(rng.uniform(0,2));aff=float(rng.uniform(0,2))
  for j in (1,2,3):initial(m,f'Aqueous_Mass_{j}',float(a[j-1]));initial(m,f'Sorbed_Mass_{j}',float(s[j-1]))
  initial(m,'Effluent_Mass',eff);param(m,'Flow_Rate',Q);param(m,'Kinetic_Rate',kin);param(m,'Affinity',aff)
  for name,value in [('Liquid_Volume',V),('Solid_Mass',solid),('Capacity',capacity),('Feed_Concentration',feed)]:param(m,name,value)
  c=a/V;uptake=kin*(solid*capacity*aff*c/(1+aff*c)-s);advect=Q*c;da=np.array([Q*feed,advect[0],advect[1]])-advect-uptake;r=simulate(m)
  for j in (1,2,3):
   assert r.values[f'Aqueous_Mass_{j}'][-1]==pytest.approx(a[j-1]+1e-6*da[j-1],abs=2e-14,rel=0)
   assert r.values[f'Sorbed_Mass_{j}'][-1]==pytest.approx(s[j-1]+1e-6*uptake[j-1],abs=2e-14,rel=0)
  assert r.values['Effluent_Mass'][-1]==pytest.approx(eff+1e-6*advect[-1],abs=2e-14,rel=0)
  np.testing.assert_allclose(r.values['Tracked_Mass'],sum(a)+sum(s)+eff+Q*feed*np.array(r.time),atol=4e-14,rtol=0)


def test_connectors_cover_every_declared_equation_dependency():
 for prefix in ('holt-','three-stage-'):
  raw=json.loads(next(D.glob(prefix+'*.json')).read_text());names={e['name'] for k in ('stocks','flows','variables') for e in raw[k]};expected=set()
  for e in raw['flows']+raw['variables']:
   refs={n.id for n in ast.walk(ast.parse(e['equation'].replace('^','**'),mode='eval')) if isinstance(n,ast.Name)}
   expected|={(n,e['name']) for n in refs&names}
  assert {(c['from_element'],c['to_element']) for c in raw['connectors']}==expected
  stocks={s['id'] for s in raw['stocks']}
  for flow in raw['flows']:
   for end in ('from_stock','to_stock'):assert flow[end] is None or flow[end] in stocks


def test_holt_actual_euler_rhs_matches_independent_random_states():
 rng=np.random.default_rng(8020)
 for _ in range(60):
  m=model('holt-');m.time_settings.end=m.time_settings.dt=1e-6;m.time_settings.integration_method='euler';a,b,p=rng.uniform(0,3,3)
  for name,v in [('Prey_1',a),('Prey_2',b),('Predator',p)]:initial(m,name,float(v))
  rates=[a*(1-a/1.5-.8*p),b*(.8*(1-b/1.2)-.6*p),.5*p*(.8*a+.48*b-.5)];r=simulate(m)
  for name,v,rate in zip(['Prey_1','Prey_2','Predator'],[a,b,p],rates):assert r.values[name][-1]==pytest.approx(v+1e-6*rate,abs=2e-14,rel=0)


def test_closed_loaded_sorbent_desorbs_reversibly_to_exact_equilibrium():
 m=model('three-stage-');param(m,'Flow_Rate',0);initial(m,'Sorbed_Mass_1',1);m.time_settings.end=40;r=simulate(m)
 assert r.values['Reversible_Uptake_1'][0]==-.5 and r.values['Aqueous_Mass_1'][1]>0
 np.testing.assert_allclose(np.array(r.values['Aqueous_Mass_1'])+np.array(r.values['Sorbed_Mass_1']),1,atol=2e-13,rtol=0)
 assert abs(r.values['Aqueous_Mass_1'][-1]-(np.sqrt(2)-1))<2e-12


def test_holt_no_regeneration_no_maintenance_weighted_food_budget():
 m=model('holt-');param(m,'Growth_1',0);param(m,'Growth_2',0);param(m,'Maintenance',0);m.time_settings.end=20;r=simulate(m)
 budget=np.array(r.values['Prey_1'])+.8*np.array(r.values['Prey_2'])+2*np.array(r.values['Predator'])
 np.testing.assert_allclose(budget,1.78,atol=3e-13,rtol=0)
 assert max(r.values['Predator'])<=.89+1e-12 and r.values['Predator'][-1]>.2


def test_expanded_and_constant_abstracted_rhs_are_distinct_from_catalog_and_prior_candidates():
 spec=importlib.util.spec_from_file_location('screen',ROOT/'operations/library-candidates-third-engineering/duplicate_screen.py');screen=importlib.util.module_from_spec(spec);spec.loader.exec_module(screen)
 evidence=json.loads((D/'DEDUPE-BASELINE.json').read_text());assert evidence['baseline_count']==996
 candidates=[json.loads(next(D.glob(prefix+'*.json')).read_text()) for prefix in ('holt-','three-stage-')]
 targets={screen.fingerprint(x) for x in candidates};shapes={screen.fingerprint(x,True) for x in candidates};assert len(targets)==len(shapes)==2
 paths=[ROOT/p for p in evidence['all_tracked_hashes']]+[p for p in (ROOT/'operations').glob('library-candidates*/*.json') if p.parent!=D]
 for path in paths:
  raw=json.loads(path.read_text())
  if not isinstance(raw,dict) or not raw.get('stocks') or not raw.get('flows'):continue
  try:exact=screen.fingerprint(raw);shape=screen.fingerprint(raw,True)
  except (ValueError,SyntaxError,RecursionError,TypeError):continue
  assert exact not in targets and shape not in shapes,str(path)
