"""Original isolated candidates; never writes active model definitions."""
from pathlib import Path
import ast,json
D=Path(__file__).parent

def model(mid,name,description,category,source,reference,end,dt,unit):
 return dict(id=mid,name=name,description=description,category=category,source=source,reference=reference,stocks=[],flows=[],variables=[],connectors=[],tables=[],time_settings=dict(start=0,end=end,dt=dt,integration_method='rk4',units=unit),created_at='2026-10-24T12:00:00',updated_at='2026-10-24T12:00:00')
def stock(m,n,val,u,x,y):m['stocks'].append(dict(id=m['id']+':'+n,name=n,initial_value=val,equation='',units=u,position=dict(x=x,y=y)))
def variable(m,n,eq,u):
 i=len(m['variables']);m['variables'].append(dict(id=m['id']+':'+n,name=n,equation=str(eq),units=u,position=dict(x=80+(i%6)*220,y=60+(i//6)*95)))
def flow(m,n,eq,u,fr=None,to=None):
 i=len(m['flows']);m['flows'].append(dict(id=m['id']+':'+n,name=n,equation=eq,units=u,from_stock=m['id']+':'+fr if fr else None,to_stock=m['id']+':'+to if to else None,position=dict(x=100+(i%5)*220,y=720+(i//5)*110)))
def finish(m):
 names={e['name'] for k in ('stocks','flows','variables') for e in m[k]};edges=[]
 for e in m['variables']+m['flows']:
  refs={n.id for n in ast.walk(ast.parse(e['equation'].replace('^','**'),mode='eval')) if isinstance(n,ast.Name)}
  for n in sorted(refs&names):edges.append(dict(id=m['id']+':c'+str(len(edges)),from_element=n,to_element=e['name']))
 m['connectors']=edges;(D/(m['id']+'.json')).write_text(json.dumps(m,indent=2)+'\n')


m=model('finite-source-machine-repair-sixth-control','Finite-source machine repair with a shared repairer','Original four-state probability model for three identical machines sharing one repairer. Each operating machine fails independently at exponential rate Failure_Rate; one busy repairer completes repairs at exponential rate Repair_Rate. Probability stocks describe an ensemble distribution, not a sampled failure path or a continuous number of broken machines. Three-machine topology is fixed: changing population requires rebuilding states, not editing a population parameter. Nonnegative rates and probability initial conditions summing to one. No spares, common-cause failures, aging, travel time, repairer vacations or empirical calibration. Defaults illustrative. Coarse numerical steps can violate probability positivity; no clipping or renormalization.','engineering','https://www.kent.ac.uk/smsas/personal/lb209/files/sp14.pdf','Lothar Breuer, Introduction to Stochastic Processes, section3.3.6 printed pp53-54, finite-source transition rates and machine-repair interpretation. Original JSON/equation implementation, no source text/code/figures copied.',30,.02,'hour')
for n in range(4):stock(m,f'Probability_{n}_Down',1 if n==0 else 0,'1',200+270*n,400)
variable(m,'Failure_Rate',.2,'1/hour');variable(m,'Repair_Rate',1,'1/hour')
for n in range(3):
 flow(m,f'Failure_{n}_to_{n+1}',f'{3-n} * Failure_Rate * Probability_{n}_Down','1/hour',fr=f'Probability_{n}_Down',to=f'Probability_{n+1}_Down')
 flow(m,f'Repair_{n+1}_to_{n}',f'Repair_Rate * Probability_{n+1}_Down','1/hour',fr=f'Probability_{n+1}_Down',to=f'Probability_{n}_Down')
variable(m,'Probability_Total','Probability_0_Down + Probability_1_Down + Probability_2_Down + Probability_3_Down','1')
variable(m,'Expected_Down','Probability_1_Down + 2 * Probability_2_Down + 3 * Probability_3_Down','1')
variable(m,'Expected_Operating','3 - Expected_Down','1')
variable(m,'Repairer_Busy','Probability_1_Down + Probability_2_Down + Probability_3_Down','1')
variable(m,'Expected_Waiting','Probability_2_Down + 2 * Probability_3_Down','1')
finish(m)

m=model('pi-back-calculation-sixth-control','PI control with actuator saturation and back-calculation','Original normalized first-order plant with PI controller and finite-gain back-calculation anti-windup. Integral_Output is the signed integral contribution to actuator command; it is not accumulated error and can be negative. Command=Proportional_Gain*(Setpoint-Output)+Integral_Output; actual actuator is explicitly bounded. Integral derivative adds Integral_Gain*error and Tracking_Rate*(Actuator-Command). Time seconds; output, reference, actuator and integral contribution normalized dimensionless. Positive Plant_Time; nonnegative plant gain, proportional/integral/tracking gains; Actuator_Min < Actuator_Max. Original illustrative defaults, no delay, derivative control, rate limit, noise, feedforward or tuning/stability guarantee. Tracking_Rate=0 disables anti-windup. Numerical steps must resolve plant and tracking time scales.','engineering','https://cse.lab.imtlucca.it/~bemporad/teaching/controllodigitale/pdf/Astrom-ACC89.pdf','Astrom,K.J. and Rundqwist,L.(1989), Integrator Windup and How to Avoid It, American Control Conference pp1693-1698, doi:10.23919/ACC.1989.4790464, printed p1694 Figure2. Original normalized plant/defaults; PI specialization of back-calculation, no paper text/code/figures redistributed.',20,.01,'second')
stock(m,'Output',0,'1',320,430);stock(m,'Integral_Output',0,'1',760,430)
for n,v,u in [('Setpoint',.8,'1'),('Proportional_Gain',3,'1'),('Integral_Gain',1,'1/second'),('Tracking_Rate',2,'1/second'),('Plant_Gain',1,'1'),('Plant_Time',2,'second'),('Actuator_Min',0,'1'),('Actuator_Max',1,'1')]:variable(m,n,v,u)
variable(m,'Error','Setpoint - Output','1')
variable(m,'Command','Proportional_Gain * Error + Integral_Output','1')
variable(m,'Actuator','MIN(Actuator_Max, MAX(Actuator_Min, Command))','1')
flow(m,'Plant_Response','(Plant_Gain * Actuator - Output) / Plant_Time','1/second',to='Output')
flow(m,'Error_Integration','Integral_Gain * Error','1/second',to='Integral_Output')
flow(m,'Tracking_Correction','Tracking_Rate * (Actuator - Command)','1/second',to='Integral_Output')
finish(m)
