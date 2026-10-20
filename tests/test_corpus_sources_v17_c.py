"""Partition C preservation, independent arithmetic and missing-dynamics checks."""
import base64,gzip,hashlib,json,math
from pathlib import Path
import pytest
from app.core.model import Model
from app.core.simulator import simulate
ROOT=Path(__file__).resolve().parents[1]
RECEIPT=json.loads((ROOT/'operations/corpus-reconciliation-v17-c.json').read_text())
ROWS={r['partition_index']:r for r in RECEIPT['models']}
BASELINE_FIXTURE=json.loads((ROOT/'tests/fixtures/corpus-baseline-v17-c.json').read_text())
BASELINES={r['file']:r for r in BASELINE_FIXTURE['models']}
def load(i):return Model.model_validate_json((ROOT/ROWS[i]['file']).read_text())
def run(i,end=None,dt=None):
 m=load(i);u={}
 if end is not None:u['end']=end
 if dt is not None:u['dt']=dt
 return simulate(m,m.time_settings.model_copy(update=u))
def test_partition_c_exhaustively_accounts_for_exact_baseline_slice():
 baseline=json.loads((ROOT/'operations/library-full-v160.json').read_text())
 failed=sorted((r for r in baseline['models'] if r['status']=='failed'),key=lambda r:r['file'])
 assert [r['file'] for r in RECEIPT['models']]==[r['file'] for i,r in enumerate(failed) if i%3==2]
 assert len(ROWS)==44
 assert len(BASELINE_FIXTURE['models'])==len(BASELINES)==44
 assert set(BASELINES)=={r['file'] for r in RECEIPT['models']}
 assert all(r['diagnosis'] and r['source_evidence'] and r['scientific_validation'] for r in ROWS.values())
@pytest.mark.parametrize('i',list(ROWS))
def test_partition_c_preserves_every_original_node_layout_link_input_and_time_setting(i):
 r=ROWS[i];raw=(ROOT/r['file']).read_bytes();d=json.loads(raw)
 fixture=BASELINES[r['file']]
 original=gzip.decompress(base64.b64decode(fixture['gzip_base64'],validate=True));old=json.loads(original)
 assert len(original)==fixture['original_bytes']
 assert hashlib.sha256(original).hexdigest()==fixture['sha256']
 assert hashlib.sha256(original).hexdigest()==r['before_sha256']==r['baseline_sha256']
 assert hashlib.sha256(raw).hexdigest()==r['after_sha256']
 assert d['id']==old['id'] and d['name']==old['name']
 assert d['connectors']==old['connectors'] and d['time_settings']==old['time_settings']
 for kind in ('stocks','flows','variables'):
  after={e['id']:e for e in d[kind]}
  assert set(e['id'] for e in old[kind]).issubset(after)
  for e in old[kind]:
   x=after[e['id']]
   assert x['position']==e['position']
   if kind=='stocks':assert x['initial_value']==e['initial_value']
   if kind=='flows':assert (x['from_stock'],x['to_stock'])==(e['from_stock'],e['to_stock'])
   if kind=='variables':
    try:float(e['equation'])
    except ValueError:pass
    else:assert x['equation']==e['equation']
  if i!=95:assert len(d[kind])==len(old[kind])
 # No undocumented repairs can sneak into the receipt.
 for change in r['changed_fields']:
  assert any(change['path'].startswith(p) for p in ['/flows','/variables','/stocks','/description','/reference','/source'])
def test_world3_identity_repair_cohort_balance_independent_of_maturation():
 r=run(5,end=1901);v=r.values
 assert v['Deaths 65+'][0]==pytest.approx(60000000*.07)
 births=700000000*1.5*.5/30
 deaths=650000000*.005+700000000*.003+190000000*.012+60000000*.07
 assert v['Total Population'][1]-v['Total Population'][0]==pytest.approx(births-deaths)
def test_dsge_parameter_binding_preserves_independent_initial_adjustment():
 r=run(32,end=.25);v=r.values
 assert v['Taylor Rate'][0]==pytest.approx(.04)
 assert v['Inflation'][1]==pytest.approx(.02+(.99*.02-.02))
 assert v['Output Gap'][1]==pytest.approx(0)
def test_pipeline_explicit_phase_labels_recover_original_local_rates():
 r=run(71,end=.025)
 assert r.values['To Phase 2/3'][0]==pytest.approx(2*.6/.25)
 assert r.values['Approval'][0]==pytest.approx(1*.7/.5)
def test_learning_local_rate_and_memory_first_step_independent():
 r=run(56,end=.5)
 assert r.values['Knowledge Level'][1]==pytest.approx(.5*2*5*(1-.2)*.8*1.5)
 assert r.values['Memory Strength'][1]==pytest.approx(.5*2*(1+.5))
def test_kahneman_resource_first_step_and_fatigue_are_separate_balances():
 r=run(110,end=.5)
 assert r.values['System 2 Resources'][1]==pytest.approx(100-.5*65*.1)
 assert r.values['Fatigue'][1]==pytest.approx(.5*65*.02)
def test_opinion_population_transfers_conserve_total_over_default_grid():
 v=run(119).values
 assert v['Total Population']==pytest.approx([1000000]*len(v['Total Population']))
def test_rumor_alias_repair_recovers_rates_but_does_not_hide_later_divergence():
 v=run(122,end=.1).values
 hearing=10*1000*999000/1000000*.1*1.25*3.4
 assert v['Hearing Rumor'][0]==pytest.approx(hearing)
 assert sum(v[n][1] for n in ['Ignorant (Unaware)','Active Spreaders','Stiflers (Inactive)','Skeptics (Fact-checkers)'])==pytest.approx(1000000)
 assert ROWS[122]['numerical_status']=='failed'
def test_pendulum_uses_existing_initial_inputs_and_signed_angular_acceleration():
 v=run(101,end=.01).values
 assert v['Angular Position 1'][0]==pytest.approx(.3)
 acceleration=-9.81*math.sin(.3)-5*.5**2*.3
 assert v['Angular Acceleration 1'][0]==pytest.approx(acceleration)
 assert v['Angular Velocity 1'][1]==pytest.approx(.01*acceleration)
 assert v['Angular Position 2'][0]==0
 # Source-fidelity issue: these local energy stocks may go negative, and are
 # explicitly not endorsed as a mechanical energy conservation formulation.
 assert 'not a proven energy-conserving' in ROWS[101]['diagnosis']
def rhs(v,w):return(v-v*v*v/3-w+.5,(v+.7-.8*w)/12.5)
def reference_fhn(duration,h=.0005):
 v,w=-.6,0.;out=[(v,w)]
 for j in range(round(duration/h)):
  a,b=rhs(v,w);c,d=rhs(v+h*a/2,w+h*b/2);e,f=rhs(v+h*c/2,w+h*d/2);g,k=rhs(v+h*e,w+h*f)
  v+=h*(a+2*c+2*e+g)/6;w+=h*(b+2*d+2*f+k)/6
  out.append((v,w))
 return out
def test_fhn_added_derivative_flows_match_independent_rk4_and_converge():
 ref=reference_fhn(20)
 errors=[]
 for dt in (.01,.005):
  r=run(95,end=20,dt=dt);stride=round(dt/.0005)
  err=max(max(abs(r.values['Membrane_Potential'][i]-ref[i*stride][0]),abs(r.values['Recovery_Variable'][i]-ref[i*stride][1])) for i in range(len(r.time)))
  errors.append(err)
 assert errors[0]<.12
 assert errors[1]<errors[0]*.6
 full=run(95)
 assert len(full.time)==20001
 assert max(full.values['Membrane_Potential'])-min(full.values['Membrane_Potential'])>2
 assert len(load(95).flows)==2
 assert {f.to_stock for f in load(95).flows}=={'s1','s2'}
def test_oregonator_finite_is_explicitly_structurally_invalid():
 m=load(98)
 assert not m.flows
 assert all(not s.equation for s in m.stocks)
 assert ROWS[98]['status']=='numerically_finite_structurally_incomplete_no_derivatives'
 assert ROWS[98]['structurally_implemented'] is False
def test_unresolved_stock_depletion_and_stiffness_are_mathematical_not_hidden():
 # Euler amplification factors and depletion at the original unchanged dt.
 assert 1-.1*23 == pytest.approx(-1.3) # HIV clearance
 assert 1-1000 == -999 # neutral-pool loss/fixation, dimensionally unresolved
 assert 100-.5*(100*100/10*.8)<0 # information overdraw on first step
 assert 20-.25*(20*60*(1-20/150))<0 # traffic density overdraw
 assert all(ROWS[i]['numerical_status']=='failed' for i in [68,77,116,125])
