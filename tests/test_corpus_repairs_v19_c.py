from tests.model_history import model_path, find_model_path
"""Primary-source v1.9-C reconstructions, with portable independent references."""
import copy,functools,hashlib,json,math,re
from pathlib import Path
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from app.core.model import Model
from app.core.simulator import simulate
ROOT=Path(__file__).resolve().parents[1]
FILES={
 'options':'models/finance/real-options-investment-timing-fin.json',
 'workforce':'models/management/workforce-overtime-morale-man.json',
 'pipe':'models/physics/navier-stokes-pipe-flow-phy.json',
 'reactor':'models/physics/nuclear-power-plant-operations-phy.json',
 'lorenz':'models/physics/rayleigh-benard-convection-phy.json',
 'urban':'models/social/urban-development-feedback-soc.json'}
def load(key):return Model.model_validate_json(model_path(ROOT,FILES[key]).read_text())
@functools.lru_cache(None)
def run(key,level=0):
 m=load(key)
 # Radau DT controls retained output spacing, not its internal accuracy. Refine
 # tolerances on the original full-horizon grid; retries count toward real work.
 if key in ['reactor','pipe']:update={'rtol':m.time_settings.rtol/10**level,'atol':m.time_settings.atol/10**level}
 else:update={'dt':m.time_settings.dt/2**level}
 return simulate(m,m.time_settings.model_copy(update=update))
def matrix(result,names):return np.array([result.values[n] for n in names])

def workforce_rhs(t,y):
 w,h=y;s=120 if t>20 else 100
 morale=np.interp(h/40,[0,.326284,.495468,.682779,.839879,1,1.14804,1.3716,1.66767,2],[1.5,1.4386,1.40351,1.32018,1.18421,1,.833333,.640351,.526316,.5])
 productivity=np.interp(morale,[0,1,2,2.63444,3.29909,3.97583],[0,1,2,2.36842,2.52632,2.57895])
 return np.array([(s/productivity-w)/6,(s/(w*productivity)*40-h)/3])
def independent_euler(rhs,initial,time):
 y=np.array(initial,dtype=float);out=[y.copy()]
 for a,b in zip(time[:-1],time[1:]):y=y+(b-a)*rhs(a,y);out.append(y.copy())
 return np.array(out).T

def lorenz_rhs(t,y):
 x,v,z=y;return np.array([10*(v-x),28*x-v-x*z,x*v-8*z/3])
def independent_rk4(rhs,initial,end,dt):
 y=np.array(initial,dtype=float);out=[y.copy()]
 for i in range(round(end/dt)):
  t=i*dt;a=rhs(t,y);b=rhs(t+dt/2,y+dt*a/2);c=rhs(t+dt/2,y+dt*b/2);d=rhs(t+dt,y+dt*c)
  y=y+dt*(a+2*b+2*c+d)/6;out.append(y.copy())
 return np.array(out).T

def reactor_rhs(t,y):
 n,c,tf,tc=y;rho=.0022-1e-5*(tf-921.875)-5e-5*(tc-571.875);heat=4e6*(tf-tc)
 return np.array([(rho-.0075)*n/.001+.1*c,.0075*n/.001-.1*c,(7e6*n-heat)/8e6,(heat-64e6*(tc-550))/28e6])
def reactor_scilab_normalized_rhs(t,z):
 # Literal transcription of PDModel, printed pp.78-79; density/temperature excesses.
 x,tf,tc,c=z;rho=.0022-1e-5*921.875*tf-5e-5*571.875*tc
 return np.array([(-.0075*x+.0075*c+rho+rho*x)/.001,
 (7e6*200*x/921.875-4e6*tf+4e6*571.875*tc/921.875)/8e6,
 (4e6*921.875*tf/571.875-(64e6+4e6)*tc)/28e6,
 .1*(x-c)])

def pipe_loss(q):
 area=3.14159*.05**2;v=q/area;re=abs(v)*.1/1e-6
 if re<=2000:return 32*1e-6*10*v/(9.81*.1**2)
 f4=.25/math.log10(5.74/4000**.9)**2
 f=.032+(re-2000)*(f4-.032)/2000 if re<4000 else .25/math.log10(5.74/re**.9)**2
 return f*100*v*abs(v)/(2*9.81)
def pipe_rhs(t,y):return [9.81*(3.14159*.05**2)/10*(100-pipe_loss(y[0]))]

@pytest.mark.parametrize('key',list(FILES))
def test_source_reconstructed_defaults_finish_with_real_dynamics(key):
 r=run(key);m=load(key)
 assert r.time[-1]==m.time_settings.end
 assert all(math.isfinite(v) for series in r.values.values() for v in series)
 assert any(np.ptp(r.values[s.name])>1e-5 for s in m.stocks)

def test_workforce_native_equations_and_every_saved_euler_sample():
 r=run('workforce');ref=independent_euler(workforce_rhs,[100,40],r.time)
 np.testing.assert_allclose(matrix(r,['Workforce','Average_Worker_Hours']),ref,rtol=3e-13,atol=3e-11)
 assert min(r.values['Workforce'])>=100 and min(r.values['Morale'])>.5
 assert abs(r.values['Workforce'][-1]-120)<.01
 assert len(load('workforce').tables)==2

def test_workforce_full_horizon_step_convergence():
 rs=[run('workforce',i) for i in range(3)];fine=independent_euler(workforce_rhs,[100,40],np.arange(0,200+.03125,.03125))
 errors=[np.max(np.abs(matrix(r,['Workforce','Average_Worker_Hours'])-fine[:,::round((r.time[1]-r.time[0])/.03125)])) for r in rs]
 assert errors[2]<errors[1]<errors[0]

def test_lorenz_source_table_and_independent_rk4():
 # Source Table1, p.136, printed tenths (table suppresses additional digits), double-approximation method dt.01.
 y=np.array([0.,1.,0.]);rows={0:y.copy()}
 for i in range(45):
  a=lorenz_rhs(i*.01,y);b=lorenz_rhs((i+1)*.01,y+.01*a);y=y+.005*(a+b);rows[i+1]=y.copy()
 np.testing.assert_allclose(rows[5],[.4,1.2,0],atol=.1)
 np.testing.assert_allclose(rows[45],[17.4,5.5,48.3],atol=.1)
 r=run('lorenz');ref=independent_rk4(lorenz_rhs,[0,1,0],10,.01)
 np.testing.assert_allclose(matrix(r,['Convection_Amplitude','Horizontal_Temperature_Amplitude','Vertical_Profile_Amplitude'])[:,:1001],ref,rtol=2e-12,atol=2e-11)

def test_lorenz_full_horizon_invariant_and_refinement_limits():
 names=['Convection_Amplitude','Horizontal_Temperature_Amplitude','Vertical_Profile_Amplitude'];r=run('lorenz');x,y,z=matrix(r,names)
 # V=x²/sigma+y²+(z-r-1)², V'<=-2V+b(r+1)².
 assert np.max(x*x/10+y*y+(z-29)**2)<(8/3)*29**2/2+.1
 # Refined full-horizon independent literal RK4, uncharged by production budgets.
 for dt in [.005,.0025]:
  ref=independent_rk4(lorenz_rhs,[0,1,0],200,dt);a,b,c=ref
  assert np.max(a*a/10+b*b+(c-29)**2)<1121.5
  short=solve_ivp(lorenz_rhs,[0,1],[0,1,0],method='DOP853',t_eval=np.arange(0,1+.0001,dt),rtol=1e-12,atol=1e-13)
  assert short.success
  assert np.max(np.abs(ref[:,:round(1/dt)+1]-short.y))<2e-4
 # Chaotic full200 paths diverge despite converged short-time integration; no
 # pointwise long-time identity is claimed. Native engine correctly caps dt/2.
 from app.core.equations import EquationError
 with pytest.raises(EquationError) as failure:run('lorenz',1)
 assert failure.value.code=='capacity_exceeded'
 assert failure.value.details['resource']=='work_units'

def test_reactor_thermal_energy_and_precursor_equilibrium():
 m=load('reactor');r=run('reactor');n,c,tf,tc=matrix(r,['Neutron_Density','Delayed_Neutron_Precursors','Fuel_Temperature','Coolant_Temperature'])
 assert c[0]==15000 and .0075*n[0]/.001==.1*c[0]
 for state in [[200,15000,921.875,571.875],[250,19000,1000,580]]:
  d=reactor_rhs(0,state)
  assert 8e6*d[2]+28e6*d[3]==pytest.approx(7e6*state[0]-64e6*(state[3]-550),rel=2e-14,abs=1e-6)
  normalized=[state[0]/200-1,state[2]/921.875-1,state[3]/571.875-1,state[1]/15000-1]
  expected=reactor_scilab_normalized_rhs(0,normalized)
  np.testing.assert_allclose([d[0]/200,d[2]/921.875,d[3]/571.875,d[1]/15000],expected,rtol=1e-12,atol=2e-14)
 assert min(n)>=200 and min(tf)>0 and min(tc)>550
 assert n[-1]==pytest.approx(291.4285714285714,rel=1e-8)
 assert tf[-1]==pytest.approx(1091.875,abs=2e-6)

def test_reactor_full1000_independent_lsoda_and_tolerance_refinement():
 names=['Neutron_Density','Delayed_Neutron_Precursors','Fuel_Temperature','Coolant_Temperature']
 for i in range(3):
  r=run('reactor',i);ref=solve_ivp(reactor_rhs,[0,1000],[200,15000,921.875,571.875],method='LSODA',t_eval=r.time,rtol=1e-11,atol=1e-10)
  assert r.time==run('reactor').time and r.time[-1]==1000
  assert ref.success
  np.testing.assert_allclose(matrix(r,names),ref.y,rtol=8e-7/10**i,atol=2e-6/10**i)
  assert r.integration_diagnostics['work_units']<=1000000

def test_pipe_momentum_force_area_factor_and_laminar_rest_limit():
 r=run('pipe');q=np.array(r.values['Flow Rate']);area=3.14159*.05**2
 assert r.values['Acceleration'][0]==pytest.approx(area*9.81*100/10)
 assert r.values['Friction Force'][0]==0 and r.values['Pressure Loss'][0]==0
 equilibrium=brentq(lambda x:pipe_loss(x)-100,.001,1)
 assert min(q)>=0 and max(q)<=equilibrium+2e-9
 assert q[-1]==pytest.approx(equilibrium,rel=1e-8)
 assert r.report_values['Friction Factor'][0].startswith('Undefined at rest')
 assert r.report_values['Diffusion Length Growth'][0].startswith('Singular')
 assert r.values['Viscous Diffusion Length'][-1]==pytest.approx(math.sqrt(1e-6*10))

def test_pipe_full10_independent_dop853_and_tolerance_refinement():
 for i in range(3):
  r=run('pipe',i);ref=solve_ivp(pipe_rhs,[0,10],[0],method='DOP853',t_eval=r.time,rtol=1e-12,atol=1e-13,max_step=.01)
  assert r.time==run('pipe').time and r.time[-1]==10
  assert ref.success
  np.testing.assert_allclose(r.values['Flow Rate'],ref.y[0],rtol=3e-7/10**i,atol=3e-10/10**i)

def test_option_zero_opportunity_cost_is_correct_limit_and_reports():
 r=run('options')
 assert r.values['beta'][0]==1
 assert set(r.report_values['Trigger_Value'])=={'No finite exercise threshold'}
 assert set(r.values['Invested'])=={0}
 np.testing.assert_array_equal(r.values['Option_Value'],r.values['Asset_Value'])
 assert 'Trigger_Value' not in r.values

def test_option_finite_boundary_value_matching_smooth_pasting_and_pde():
 m=load('options')
 for v in m.variables:
  if v.name=='r':v.equation='.08'
 r=simulate(m);beta=.5-.05/.2**2+math.sqrt((.05/.2**2-.5)**2+2*.08/.2**2);trigger=80*beta/(beta-1)
 assert r.report_values['Trigger_Value'][0]==pytest.approx(trigger)
 value=r.values['Option_Value'][0];delta=r.values['Option_Delta'][0]
 second=beta*(beta-1)*value/100**2
 assert .5*.2**2*100**2*second+.05*100*delta-.08*value==pytest.approx(0,abs=1e-12)
 assert (trigger-80)*(trigger/trigger)**beta==pytest.approx(trigger-80)
 assert beta*(trigger-80)/trigger==pytest.approx(1)
 assert set(r.values['Invested'])=={0.,1.}

def test_option_full50_asset_analytic_solution_and_euler_convergence():
 errors=[]
 for i in range(3):
  r=run('options',i);t=np.array(r.time);exact=100*np.exp(.05*t+.2*.05*((1-np.cos(17.3*t))/17.3+np.sin(23.1*t)/23.1))
  errors.append(np.max(np.abs(np.array(r.values['Asset_Value'])-exact)/exact))
 assert errors[2]<errors[1]<errors[0]<.03

# The balances below were independently transcribed from all20 native INTEG
# declarations, not generated from the importer's derivative strings.
URBAN_BALANCES={
'Declining_Industry':lambda v:v['mature_business_decline']-v['declining_industry_demise'],
'New_Enterprise':lambda v:v['new_enterprise_Construction']-v['new_enterprise_decline'],
'New_Enterprise_Average':lambda v:(v['New_Enterprise']-v['New_Enterprise_Average'])/v['new_enterprise_average_time'],
'Labor_Ratio_Perc':lambda v:(v['labor_ratio']-v['Labor_Ratio_Perc'])/v['labor_ratio_perception_time'],
'Labor':lambda v:v['underemp_to_labor']+v['labor_birth']-v['labor_to_manager']+v['labor_arrival']-v['labor_departure']-v['labor_to_underemp'],
'Labor_Arrival_Mult_Perc':lambda v:(v['labor_arrival_mult']-v['Labor_Arrival_Mult_Perc'])/v['labor_arrival_mult_perc_tab'],
'Labor_Mob_Mult_Perc':lambda v:(v['labor_mob_mult']-v['Labor_Mob_Mult_Perc'])/v['labor_mob_mult_perc_time'],
'Underemp_Mob_Mult_Perc':lambda v:(v['underemp_mob_mult']-v['Underemp_Mob_Mult_Perc'])/v['underemp_mob_mult_perc_time'],
'Underemp_to_Labor_Perc':lambda v:(v['underemp_to_labor']-v['Underemp_to_Labor_Perc'])/v['underemp_to_labor_perc_time'],
'Manager_Prof_Arriv_Mult_Perc':lambda v:(v['manager_prof_arriv_mult']-v['Manager_Prof_Arriv_Mult_Perc'])/v['manager_prof_arriv_mult_perc_time'],
'Manager_Professional':lambda v:v['labor_to_manager']+v['manager_prof_birth']+v['manager_prof_arrivals']-v['manager_prof_depart'],
'Mature_Business':lambda v:v['new_enterprise_decline']-v['mature_business_decline'],
'Premium_Housing':lambda v:v['premium_housing_contruction']-v['premium_housing_obsolescence'],
'Premium_Housing_Average':lambda v:(v['Premium_Housing']-v['Premium_Housing_Average'])/v['premium_housing_averate_time'],
'Tax_Ratio_Needed_Perc':lambda v:(v['tax_ratio_needed']-v['Tax_Ratio_Needed_Perc'])/v['tax_ratio_needed_perception_time'],
'Attract_Migr_Mult_Perc':lambda v:(v['attract_migr_mult']-v['Attract_Migr_Mult_Perc'])/v['attract_migr_mult_perc_table'],
'Underemployed':lambda v:v['underemployed_arrivals']+v['underemp_births']+v['labor_to_underemp']-v['underemp_departures']-v['underemp_to_labor'],
'Underemp_Housing':lambda v:v['worker_housing_obsolescence']+v['low_cost_hous_prog']-v['slum_housing_demolition'],
'Worker_Housing':lambda v:v['premium_housing_obsolescence']+v['worker_housing_construction']-v['worker_housing_obsolescence'],
'Worker_Housing_Average':lambda v:(v['Worker_Housing']-v['Worker_Housing_Average'])/v['worker_housing_average_time']}
@functools.lru_cache(None)
def urban_source_program():
 d=json.loads((ROOT/'tests/fixtures/v19_c/urban-equation-map.json').read_text());names=d['names'];bylower={n.lower():x for n,x in names.items()};pat=re.compile('|'.join(r'(?<![\w])'+re.escape(n)+r'(?![\w])' for n in sorted(names,key=len,reverse=True)),re.I)
 def source_compile(e):
  e=pat.sub(lambda m:bylower[m.group().lower()],e);e=re.sub('IF THEN ELSE','IF',e,flags=re.I);e=re.sub(r'GAME\(0\)','0',e);e=re.sub(r'\bTime\b','t',e,flags=re.I);return compile(e.replace('^','**').strip(),'<native URBAN source>','eval')
 initials={names[r['name']]:source_compile(r['initial']) for r in d['entries'] if 'initial' in r};aux={names[r['name']]:source_compile(r['expression']) for r in d['entries'] if 'initial' not in r and r['name'].upper() not in d['settings']}
 tables={names[t['name']]:(lambda x,p=np.array(t['points']):float(np.interp(x,p[:,0],p[:,1]))) for t in d['tables']}
 return initials,aux,tables
@functools.lru_cache(None)
def urban_reference(dt):
 initials,aux,tables=urban_source_program();base={'__builtins__':{},'LN':math.log,'MIN':min,'MAX':max,'IF':lambda a,b,c:b if a else c,**tables}
 def evaluate(state,t,initial=False):
  env={**base,**state,'t':t};pending={**aux,**(initials if initial else {})}
  while pending:
   progress=False
   for name,code in list(pending.items()):
    try:env[name]=float(eval(code,env))
    except NameError:continue
    del pending[name];progress=True
   if not progress:raise AssertionError(list(pending))
  return env
 values=evaluate({},0,True);state={k:values[k] for k in initials};out=[list(state.values())]
 for i in range(round(250/dt)):
  values=evaluate(state,i*dt);state={k:x+dt*URBAN_BALANCES[k](values) for k,x in state.items()};out.append(list(state.values()))
 return list(initials),np.array(out).T

def test_urban_all20_source_balances_and_full250_every_saved_sample():
 r=run('urban');names,ref=urban_reference(1)
 assert len(names)==20 and len(load('urban').tables)==53
 np.testing.assert_allclose(matrix(r,names),ref,rtol=3e-12,atol=1e-7)
 assert np.min(ref)>0
 assert r.values['population'][0]==pytest.approx(3900*5+14000*6+1200*8)
 assert r.values['New_Enterprise_Average'][0]==140
 assert r.values['Premium_Housing_Average'][0]==3500

def test_urban_full250_half_quarter_step_and_positive_domains():
 names,ref=urban_reference(.125);errors=[]
 for i in range(3):
  r=run('urban',i);a=matrix(r,names);assert np.min(a)>0
  assert all(0<=x<=1.000001 for x in r.values['land_fraction_occupied'])
  _,own=urban_reference(1/2**i);np.testing.assert_allclose(a,own,rtol=5e-12,atol=1e-7)
  errors.append(np.max(np.abs(a-ref[:,::round((1/2**i)/.125)])/np.maximum(1,ref[:,::round((1/2**i)/.125)])))
 assert errors[2]<errors[1]<errors[0]

def test_receipt_before_after_hashes_and_complete_field_diffs():
 receipt=json.loads((ROOT/'operations/corpus-repairs-v19-c.json').read_text())
 assert len(receipt['models'])==15
 for row in receipt['models']:
  assert hashlib.sha256(row['before_text'].encode()).hexdigest()==row['before_sha256']
  after=model_path(ROOT,row['file']).read_bytes();assert hashlib.sha256(after).hexdigest()==row['after_sha256']
  assert row['source_evidence'] and row['root_cause_chain'] and row['missing_evidence'] is not None

def test_native_fixtures_are_hash_bound_and_urban_declaration_coverage_complete():
 fixture=ROOT/'tests/fixtures/v19_c'
 assert hashlib.sha256((fixture/'INTRO.mdl').read_bytes()).hexdigest()=='7c6453f0c0346d0694f7305decf81978331dbc24630c4d55f697c53cec31efad'
 assert hashlib.sha256((fixture/'URBAN.mdl').read_bytes()).hexdigest()=='fe7bbd0a26897d2ad2152d6390e3d544dcd861c2ab52eda3922a27a8b49465a4'
 source=json.loads((fixture/'urban-equation-map.json').read_text());m=load('urban')
 assert source['settings']=={'FINAL TIME':250,'INITIAL TIME':0,'SAVEPER':5,'TIME STEP':1}
 assert len(source['entries'])==255 and len(source['tables'])==53
 native={source['names'][r['name']] for r in source['entries'] if r['name'].upper() not in source['settings']}
 assert native<={x.name for x in [*m.stocks,*m.variables]}
 assert len(native)==251 and len(m.stocks)==20 and len(m.flows)==20 and len(m.variables)==233
 actual={t.name:t for t in m.tables}
 for t in source['tables']:
  a=actual[source['names'][t['name']]]
  assert a.interpolation=='continuous'
  assert a.points==[tuple(p) for p in t['points']]

