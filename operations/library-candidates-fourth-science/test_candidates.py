"""Independent limits, invariant derivatives and analytic full trajectories."""
import copy,json,hashlib
from pathlib import Path
import numpy as np
import pytest
from scipy.linalg import expm
from app.core.model import Model,TimeSettings
from app.core.simulator import simulate
D=Path(__file__).parent

def model(prefix):return Model.model_validate_json(next(D.glob(prefix+'*.json')).read_text())
def change(m,name,value):next(v for v in m.variables if v.name==name).equation=str(value)
def run(m):return simulate(m)

@pytest.mark.parametrize('prefix',['chaplygin-','optical-','foucault-'])
@pytest.mark.parametrize('solver',['euler','rk4','radau'])
def test_all_solver_defaults_are_finite(prefix,solver):
 m=model(prefix);m.time_settings.integration_method=solver;r=run(m)
 assert all(np.isfinite(v).all() for v in r.values.values())

def test_sleigh_exact_speed_angle_and_energy():
 r=run(model('chaplygin-'));t=np.array(r.time);b=1/np.sqrt(2)
 np.testing.assert_allclose(r.values['Forward_Speed'],np.sqrt(2)*np.tanh(b*t),atol=2e-8,rtol=0)
 np.testing.assert_allclose(r.values['Angular_Speed'],1/np.cosh(b*t),atol=2e-8,rtol=0)
 np.testing.assert_allclose(r.values['Heading'],np.sqrt(2)*np.arctan(np.sinh(b*t)),atol=2e-8,rtol=0)
 np.testing.assert_allclose(r.values['Kinetic_Energy'],1,atol=2e-8,rtol=0)
 assert abs(r.values['Forward_Speed'][-1]-np.sqrt(2))<1e-9

def test_sleigh_zero_offset_limit_keeps_spin_and_forward_speed():
 m=model('chaplygin-');change(m,'Offset',0);next(s for s in m.stocks if s.name=='Forward_Speed').initial_value=2;r=run(m)
 assert set(r.values['Forward_Speed'])=={2} and set(r.values['Angular_Speed'])=={1}
 np.testing.assert_allclose(r.values['Center_X'],2*np.sin(r.time),atol=3e-8)
 np.testing.assert_allclose(r.values['Center_Y'],2*(1-np.cos(r.time)),atol=3e-8)

def test_sleigh_energy_vector_field_identity_random_states():
 rng=np.random.default_rng(2524)
 for _ in range(400):
  m,J,a=rng.uniform(.1,4,3);u,w=rng.uniform(-3,3,2);I=J+m*a*a
  assert abs(m*u*a*w*w+I*w*(-m*a*u*w/I))<1e-12

def test_optical_component_rates_match_independent_complex_lindblad_matrix():
 rng=np.random.default_rng(2525)
 for _ in range(300):
  p,x,y=rng.uniform(-1,1,3);O,G,de=rng.uniform(.1,4,3)
  rho=np.array([[1-p,x+1j*y],[x-1j*y,p]]);H=np.array([[-de/2,O/2],[O/2,de/2]])
  C=np.array([[0,np.sqrt(G)],[0,0]]);A=C.conj().T@C
  dr=-1j*(H@rho-rho@H)+C@rho@C.conj().T-(A@rho+rho@A)/2
  np.testing.assert_allclose([dr[1,1].real,dr[0,1].real,dr[0,1].imag],[O*y-G*p,-G*x/2-de*y,de*x-G*y/2+O*(.5-p)],atol=5e-15)

def test_optical_full_affine_exponential_and_density_constraints():
 r=run(model('optical-'));A=np.array([[-1,0,2,0],[0,-.5,-.5,0],[-2,.5,-.5,1],[0,0,0,0.]])
 expected=np.array([expm(A*t)@np.array([0,0,0,1]) for t in r.time])
 for i,k in enumerate(['Excited_Probability','Coherence_Real','Coherence_Imaginary']):np.testing.assert_allclose(r.values[k],expected[:,i],atol=2e-8,rtol=0)
 p=np.array(r.values['Excited_Probability']);det=np.array(r.values['Density_Determinant'])
 assert min(p)>=-1e-12 and max(p)<=1+1e-12 and min(det)>=-1e-8
 assert p[-1]==pytest.approx(4/(1+8+1),abs=1e-5)

def test_optical_no_drive_exact_decay_and_closed_coherent_limit():
 m=model('optical-');change(m,'Rabi_Frequency',0);next(s for s in m.stocks if s.name=='Excited_Probability').initial_value=1;r=run(m)
 np.testing.assert_allclose(r.values['Excited_Probability'],np.exp(-np.array(r.time)),atol=1e-8)
 m=model('optical-');change(m,'Decay_Rate',0);m.time_settings.dt=.01;r=run(m);t=np.array(r.time);freq=np.sqrt(4+.25)
 np.testing.assert_allclose(r.values['Excited_Probability'],4/(4+.25)*np.sin(freq*t/2)**2,atol=8e-8)
 assert min(r.values['Density_Determinant'])>=-1e-7

def test_foucault_exact_all_four_states_and_energy():
 r=run(model('foucault-'));t=np.array(r.time);f=.05;n=np.sqrt(1+f*f);rot=np.exp(-1j*f*t)
 q=rot*(np.cos(n*t)+1j*f/n*np.sin(n*t));v=-rot*np.sin(n*t)/n
 for key,value in [('Displacement_X',q.real),('Displacement_Y',q.imag),('Velocity_X',v.real),('Velocity_Y',v.imag)]:np.testing.assert_allclose(r.values[key],value,atol=1.2e-7,rtol=0)
 np.testing.assert_allclose(r.values['Energy_Per_Mass'],.5,atol=3e-8,rtol=0)

def test_foucault_no_rotation_and_hemisphere_reversal():
 m=model('foucault-');change(m,'Vertical_Rotation',0);r=run(m)
 np.testing.assert_allclose(r.values['Displacement_X'],np.cos(r.time),atol=1e-7)
 assert set(r.values['Displacement_Y'])=={0}
 a=run(model('foucault-'));m=model('foucault-');change(m,'Vertical_Rotation',-.05);b=run(m)
 for k in ['Displacement_X','Velocity_X']:np.testing.assert_allclose(a.values[k],b.values[k],atol=1e-14)
 for k in ['Displacement_Y','Velocity_Y']:np.testing.assert_allclose(a.values[k],-np.array(b.values[k]),atol=1e-14)

@pytest.mark.parametrize('prefix,key',['chaplygin- Kinetic_Energy'.split(),'foucault- Energy_Per_Mass'.split()])
def test_rk4_halving_reduces_invariant_drift(prefix,key):
 m=model(prefix);m.time_settings.dt=.08;a=run(m);m.time_settings.dt=.04;b=run(m)
 ea=max(abs(np.array(a.values[key])-a.values[key][0]));eb=max(abs(np.array(b.values[key])-b.values[key][0]))
 assert eb<ea/8
