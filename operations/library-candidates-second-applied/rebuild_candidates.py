"""Original mathematical transcriptions; writes candidate files only."""
import json, math, hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import root
D=Path(__file__).parent
E=[]
def add(key,name,names,initial,eq,params,end,dt,url,citation,scenario,aux=None,method='rk4',unit='second',data=None):
    r=dict(id='candidate-second-applied-'+key,name=name,category='engineering',description=scenario+' Teaching reconstruction; not calibrated equipment or a certified controller. Missing dimensional annotations remain unknown.',source=url,reference=citation,stocks=[],flows=[],variables=[],tables=[],connectors=[],time_settings=dict(start=0,end=end,dt=dt,integration_method=method,units=unit))
    for i,(n,x,f) in enumerate(zip(names,initial,eq)):
        r['stocks'].append(dict(id=f's{i}',name=n,initial_value=float(x),position=dict(x=220+180*(i%5),y=150+150*(i//5))))
        r['flows'].append(dict(id=f'f{i}',name='Change_'+n,equation=f,to_stock=f's{i}',position=dict(x=130+180*(i%5),y=150+150*(i//5))))
    for i,(n,v) in enumerate([*params.items(),*(aux or {}).items()]):
        r['variables'].append(dict(id=f'p{i}',name=n,equation=str(v),position=dict(x=100+170*(i%6),y=750+100*(i//6))))
    p=D/(key+'.json');p.write_text(json.dumps(r,indent=2)+'\n')
    E.append(dict(file=p.name,id=r['id'],candidate_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source=url,citation=citation,scenario=scenario,parameters=params,initials=dict(zip(names,map(float,initial))),equations=dict(zip(names,eq)),settings=r['time_settings'],reference_data=data or {},status='candidate only; independent admission required'))

C='https://github.com/python-control/python-control/blob/b4cf7360138985f84afe299337ef9ee6c25e9c38/examples/'
add('planar-vtol-coupled-flight','Planar VTOL Coupled Translation and Attitude',['X','Y','Angle','VX','VY','Spin'],[0,0,.05,0,0,0],['VX','VY','Spin','(Fside*cos(Angle)-Lift*sin(Angle)-Drag*VX)/Mass','(Fside*sin(Angle)+Lift*cos(Angle)-Mass*Gravity-Drag*VY)/Mass','Arm*Fside/Inertia'],dict(Mass=4,Inertia=.0475,Arm=.25,Gravity=9.8,Drag=.05),8,.005,C+'pvtol.py','Murray, python-control planar VTOL model, BSD3, pinned b4cf7360138985f84afe299337ef9ee6c25e9c38','Exact source physical parameters and force limits; authored small-angle recovery feedback, constant hover lift and8-second experiment. Not the source optimal controller.',aux=dict(Lift='Mass*Gravity',Fside='min(max(-0.12*Angle-0.08*Spin,-0.1*Lift),0.1*Lift)'))
add('dc-motor-armature-speed','DC Motor Armature and Rotor Energy Exchange',['Speed','Current'],[0,0],['(TorqueConstant*Current-Friction*Speed)/Inertia','(Voltage-Resistance*Current-TorqueConstant*Speed)/Inductance'],dict(TorqueConstant=.01,Friction=.1,Inertia=.01,Voltage=1,Resistance=1,Inductance=.5),3,.005,'https://www.ece.ualberta.ca/~tchen/ctm/examples/motor/motor.html','Control Tutorials for MATLAB, DC Motor Speed Modeling, university mirror','Source physical constants, zero state and1-volt step; authored finer grid. Torque and back-EMF exchange electrical and mechanical energy.')
add('quarter-car-road-suspension','Quarter-Car Suspension with Smooth Road Rise',['Body','Wheel','BodySpeed','WheelSpeed'],[0,0,0,0],['BodySpeed','WheelSpeed','(-Spring*(Body-Wheel)-Damper*(BodySpeed-WheelSpeed))/BodyMass','(Spring*(Body-Wheel)+Damper*(BodySpeed-WheelSpeed)-TireSpring*(Wheel-Road)-TireDamper*(WheelSpeed-RoadSpeed))/WheelMass'],dict(BodyMass=2500,WheelMass=320,Spring=80000,TireSpring=500000,Damper=350,TireDamper=15020,Rise=.1,RiseTime=.2),10,.002,'https://www.ece.ualberta.ca/~tchen/ctm/examples/susp/susp.html','Control Tutorials for MATLAB, Bus Suspension Modeling','Exact source quarter-bus parameters, zero actuator force. Authored10-cm half-cosine road rise over0.2s avoids discontinuous road velocity; tire damping includes road velocity. Full10-second ring-down.',aux=dict(Road='IF(TIME<RiseTime,Rise*(1-cos(pi*TIME/RiseTime))/2,Rise)',RoadSpeed='IF(TIME<RiseTime,Rise*pi*sin(pi*TIME/RiseTime)/(2*RiseTime),0)'))
add('exothermic-cstr-cooling','Exothermic CSTR Cooling and Conversion',['Concentration','Temperature'],[.87725294608097,324.475443431599],['FeedRate/Volume*(FeedConcentration-Concentration)-Reaction','FeedRate/Volume*(FeedTemperature-Temperature)+HeatRelease/(Density*HeatCapacity)*Reaction+Conductance/(Volume*Density*HeatCapacity)*(Coolant-Temperature)'],dict(FeedRate=100,Volume=100,FeedConcentration=1,FeedTemperature=350,HeatRelease=50000,Density=1000,HeatCapacity=.239,Conductance=50000,Coolant=295,Preexponential=7.2e10,Activation=8750),10,.005,'https://apmonitor.com/pdc/index.php/Main/StirredReactor','Hedengren, APMonitor Process Dynamics and Control, Stirred Reactor','Source equations/constants and initial coolant300K equilibrium; authored time origin is coolant295K cooling step. Consistent interpretation: litre, gram, mole, joule, kelvin, minute; source comments mix unit conventions.',aux=dict(Reaction='Preexponential*exp(-Activation/Temperature)*Concentration'),unit='minute')
def column(u,rr):
    y=1.6*u/(1+.6*u);l=rr;v=l+1;fl=2+l
    z=np.empty(32);z[0]=v*(y[1]-u[0])/.5
    z[1:16]=(l*(u[:15]-u[1:16])-v*(y[1:16]-y[2:17]))/.25
    z[16]=(1+l*u[15]-fl*u[16]-v*(y[16]-y[17]))/.25
    z[17:31]=(fl*(u[16:30]-u[17:31])-v*(y[17:31]-y[18:32]))/.25
    z[31]=(fl*u[30]-u[31]-v*y[31])/.1
    return z
from scipy.integrate import solve_ivp
steady=solve_ivp(lambda t,u:column(u,.7),(0,600),np.full(32,.3),method='BDF',rtol=1e-11,atol=1e-12)
sol=root(lambda u:column(u,.7),steady.y[:,-1])
assert sol.success and max(abs(column(sol.x,.7)))<1e-10 and min(sol.x)>0
names=[f'Liquid{i}' for i in range(32)]
aux={f'Vapor{i}':f'Volatility*Liquid{i}/(1+(Volatility-1)*Liquid{i})' for i in range(32)}
eq=['VaporFlow*(Vapor1-Liquid0)/CondenserHold']
eq += [f'(Reflux*(Liquid{i-1}-Liquid{i})-VaporFlow*(Vapor{i}-Vapor{i+1}))/TrayHold' for i in range(1,16)]
eq += ['(Feed*FeedFraction+Reflux*Liquid15-FeedLiquid*Liquid16-VaporFlow*(Vapor16-Vapor17))/TrayHold']
eq += [f'(FeedLiquid*(Liquid{i-1}-Liquid{i})-VaporFlow*(Vapor{i}-Vapor{i+1}))/TrayHold' for i in range(17,31)]
eq += ['(FeedLiquid*Liquid30-(Feed-Distillate)*Liquid31-VaporFlow*Vapor31)/ReboilerHold']
aux.update(Distillate='Feed/2',Reflux='Ratio*Distillate',VaporFlow='Reflux+Distillate',FeedLiquid='Feed+Reflux')
add('binary-distillation-thirty-two','Binary Distillation: 32 Liquid Holdups',names,sol.x,eq,dict(Volatility=1.6,Feed=2,FeedFraction=.5,Ratio=3,CondenserHold=.5,TrayHold=.25,ReboilerHold=.1),60,.1,'https://apmonitor.com/wiki/index.php/Apps/DistillationColumn','Hahn and Edgar (2002), Computers and Chemical Engineering26:1379–1397; APMonitor GEKKO example','Exact GEKKO balances/holdups; source steady solve at ratio0.7 independently reproduced, then time shifted to ratio3 step. Legacy APM branch has different holdups/initials and is not mixed in. Constant relative volatility/equimolar flows; no tray energy/pressure dynamics.',aux=aux,method='radau',unit='minute',data=dict(steady_ratio=.7,steady_residual=float(max(abs(column(sol.x,.7))))))
add('averaged-boost-duty-response','Averaged Boost Converter Inverse Voltage Response',['InductorCurrent','OutputVoltage'],[4,20],['(InputVoltage-(1-Duty)*OutputVoltage)/Inductance','((1-Duty)*InductorCurrent-OutputVoltage/Load)/Capacitance'],dict(InputVoltage=10,Inductance=.01,Capacitance=.001,Load=10,Duty=.6),.5,.0001,'https://ctms.engin.umich.edu/CTMS/index.php?aux=Activities_BoostcircuitA','Control Tutorials for MATLAB and Simulink, Boost Circuit Activity5(a)','Authored continuous-conduction ideal-switch period-averaged closure of source ON/OFF Kirchhoff balances including capacitor. Authored L10mH,C1mF,R10ohm,10V; start at duty0.5 equilibrium then change to0.6. Not a switching-ripple or discontinuous-conduction model.')
names=[f'A{i}' for i in range(3)]+[f'B{i}' for i in range(3)]+[f'Wall{i}' for i in range(3)]
aux={};eq=[]
for i in range(3):
    a='ColdInlet' if i==0 else f'A{i-1}';b='HotInlet' if i==2 else f'B{i+1}'
    aux[f'HeatA{i}']=f'ConductanceA*(Wall{i}-({a}+A{i})/2)'
    aux[f'HeatB{i}']=f'ConductanceB*(({b}+B{i})/2-Wall{i})'
    eq.append(f'(ColdCapacityFlow*({a}-A{i})+HeatA{i})/FluidCapacity')
for i in range(3):
    b='HotInlet' if i==2 else f'B{i+1}';eq.append(f'(HotCapacityFlow*({b}-B{i})-HeatB{i})/FluidCapacity')
for i in range(3):eq.append(f'(HeatB{i}-HeatA{i})/WallCapacity')
add('countercurrent-exchanger-wall-storage','Countercurrent Exchanger with Distributed Wall Storage',names,[300]*9,eq,dict(ColdInlet=300,HotInlet=310,ColdCapacityFlow=4000,HotCapacityFlow=4000,ConductanceA=2000,ConductanceB=2000,FluidCapacity=4000,WallCapacity=1000),20,.01,'https://github.com/casella/ScalableTestSuite/blob/2e288e71eb0a7834310827144462726180d10500/ScalableTestSuite/Thermal/HeatExchanger.mo','Politecnico di Milano, ScalableTestSuite countercurrent heat-exchanger equations, BSD3, pinned2e288e71eb0a7834310827144462726180d10500','Source N4 upwind fluid balances, midpoint film temperatures,3 dynamic wall sections; authored constant flows/inlets and thermal capacities. WallCapacity is effective J/K per section, resolving source cpW dimension label. Existing two-temperature exchanger lacks spatial counterflow and wall storage. No claim of spatial grid convergence.',aux=aux)
add('kalman-bucy-riccati-tracker','Kalman-Bucy Tracker and Riccati Covariance',['Position','Velocity','EstimatePosition','EstimateVelocity','P11','P12','P22'],[0,1,-1,0,1,0,1],['Velocity','Acceleration','EstimateVelocity+P11/Noise*(Measurement-EstimatePosition)','Acceleration+P12/Noise*(Measurement-EstimatePosition)','2*P12-P11*P11/Noise','P22-P11*P12/Noise','Process-P12*P12/Noise'],dict(Noise=1,Process=.1),30,.01,'https://hankyang.seas.harvard.edu/OptimalControlEstimation/output-feedback.html','Hank Yang, Harvard Optimal Control and Estimation, equations6.31–6.32','Source continuous estimator/Riccati laws specialized to constant velocity. All numerical choices and deterministic multisine measurement error are authored. P is design covariance under assumed stochastic model, not an empirical uncertainty interval or proof of stochastic optimality.',aux=dict(Acceleration='0.1*sin(0.4*TIME)',Measurement='Position+0.2*sin(5*TIME)+0.1*sin(13*TIME)'))
k1=1.287e12*math.exp(-9758.3/403.15);k3=9.043e9*math.exp(-8560/403.15)
add('van-de-vusse-selectivity','Van de Vusse CSTR Competing Reaction Selectivity',['Reactant','Product','Byproduct','Dimer'],[5.1,0,0,0],['Dilution*(Feed-Reactant)-Rate1*Reactant-Rate3*Reactant^2','Rate1*Reactant-(Dilution+Rate2)*Product','Rate2*Product-Dilution*Byproduct','0.5*Rate3*Reactant^2-Dilution*Dimer'],dict(Dilution=20,Feed=5.1,Rate1=k1,Rate2=k1,Rate3=k3),1,.001,'https://github.com/do-mpc/do-mpc/blob/9d5a8df0e4d6acac899bf0a65ffd4c30a6e2e4cc/examples/CSTR/template_model.py','do-mpc CSTR benchmark, pinned9d5a8df0e4d6acac899bf0a65ffd4c30a6e2e4cc; Klatt and Engell mechanism','Authored isothermal130C specialization of source Arrhenius rates and feed5.1mol/L. Dilution20/hour and initially pure feed authored. Added C/dimer balances close source untracked products: Rate3 is A disappearance, dimer production half that rate. Not source thermal/jacket controller.',unit='hour',data=dict(temperature_kelvin=403.15))
add('three-tank-nonlinear-hydraulics','Three-Tank Communicating Nonlinear Hydraulics',['Height1','Height2','Height3'],[2,2.8,2.7],['(Inflow1-Flow13)/Area','(Inflow2+Flow32-Outflow)/Area','(Flow13-Flow32)/Area'],dict(Area=.00154,Gravity=9.81,Orifice=.00005,Discharge1=1,Discharge2=.8,Discharge3=1,Inflow1=.0001,Inflow2=.0001),200,1,'https://github.com/do-mpc/do-mpc/blob/9d5a8df0e4d6acac899bf0a65ffd4c30a6e2e4cc/examples/triple_tank_ekf/template_model.py','do-mpc triple-tank EKF source, pinned9d5a8df0e4d6acac899bf0a65ffd4c30a6e2e4cc','Exact source synchronous1-second Euler plant map, hydraulic parameters, initial true state and inflows. Source drain modifiers fixed1; estimator and noise omitted. Signed square-root communication permits reversal; no positivity clamps.',aux=dict(Flow13='Discharge1*Orifice*IF(Height1>=Height3,1,-1)*sqrt(2*Gravity*abs(Height1-Height3))',Flow32='Discharge3*Orifice*IF(Height3>=Height2,1,-1)*sqrt(2*Gravity*abs(Height3-Height2))',Outflow='Discharge2*Orifice*sqrt(2*Gravity*Height2)'),method='euler')
p=D/'three-tank-nonlinear-hydraulics.json';r=json.loads(p.read_text());r['time_settings']['discrete_period']=1;p.write_text(json.dumps(r,indent=2)+'\n');E[-1]['settings']=r['time_settings'];E[-1]['candidate_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
for e in E:
    p=D/e['file'];r=json.loads(p.read_text())
    if e['file']=='kalman-bucy-riccati-tracker.json':
        for v in r['variables']:
            if v['name']=='Acceleration':v['equation']='0.1*sin(AccelerationFrequency*TIME)'
            if v['name']=='Measurement':v['equation']='Position+0.2*sin(NoiseFrequency1*TIME)+0.1*sin(NoiseFrequency2*TIME)'
        for i,(name,value) in enumerate([('AccelerationFrequency',.4),('NoiseFrequency1',5),('NoiseFrequency2',13)]):
            r['variables'].append(dict(id='frequency'+str(i),name=name,equation=str(value),units='1/second',position=dict(x=100+150*i,y=950)))
    if e['file']=='three-tank-nonlinear-hydraulics.json':
        su={n:'meter' for n in ['Height1','Height2','Height3']};pu=dict(Area='meter^2',Gravity='meter/second^2',Orifice='meter^2',Discharge1='1',Discharge2='1',Discharge3='1',Inflow1='meter^3/second',Inflow2='meter^3/second',Flow13='meter^3/second',Flow32='meter^3/second',Outflow='meter^3/second')
    elif e['file']=='averaged-boost-duty-response.json':
        su=dict(InductorCurrent='ampere',OutputVoltage='volt');pu=dict(InputVoltage='volt',Inductance='volt*second/ampere',Capacitance='ampere*second/volt',Load='volt/ampere',Duty='1')
    elif e['file']=='countercurrent-exchanger-wall-storage.json':
        su={s['name']:'kelvin' for s in r['stocks']};pu=dict(ColdInlet='kelvin',HotInlet='kelvin',ColdCapacityFlow='joule/(second*kelvin)',HotCapacityFlow='joule/(second*kelvin)',ConductanceA='joule/(second*kelvin)',ConductanceB='joule/(second*kelvin)',FluidCapacity='joule/kelvin',WallCapacity='joule/kelvin')
        pu.update({v['name']:'joule/second' for v in r['variables'] if v['name'].startswith('Heat')})
    elif e['file']=='quarter-car-road-suspension.json':
        su=dict(Body='meter',Wheel='meter',BodySpeed='meter/second',WheelSpeed='meter/second');pu=dict(BodyMass='kg',WheelMass='kg',Spring='kg/second^2',TireSpring='kg/second^2',Damper='kg/second',TireDamper='kg/second',Rise='meter',RiseTime='second',Road='meter',RoadSpeed='meter/second')
    elif e['file']=='exothermic-cstr-cooling.json':
        su=dict(Concentration='mole/litre',Temperature='kelvin');pu=dict(FeedRate='litre/minute',Volume='litre',FeedConcentration='mole/litre',FeedTemperature='kelvin',HeatRelease='joule/mole',Density='gram/litre',HeatCapacity='joule/(gram*kelvin)',Conductance='joule/(minute*kelvin)',Coolant='kelvin',Preexponential='1/minute',Activation='kelvin',Reaction='mole/(litre*minute)')
    elif e['file']=='van-de-vusse-selectivity.json':
        su={s['name']:'mole/litre' for s in r['stocks']};pu=dict(Dilution='1/hour',Feed='mole/litre',Rate1='1/hour',Rate2='1/hour',Rate3='litre/(mole*hour)')
    elif e['file']=='binary-distillation-thirty-two.json':
        su={s['name']:'1' for s in r['stocks']};pu=dict(Volatility='1',Feed='mole/minute',FeedFraction='1',Ratio='1',CondenserHold='mole',TrayHold='mole',ReboilerHold='mole',Distillate='mole/minute',Reflux='mole/minute',VaporFlow='mole/minute',FeedLiquid='mole/minute')
        pu.update({v['name']:'1' for v in r['variables'] if v['name'].startswith('Vapor') and v['name']!='VaporFlow'})
    else:su={};pu={}
    for s,f in zip(r['stocks'],r['flows']):
        if s['name'] in su:s['units']=su[s['name']];f['units']='('+su[s['name']]+')/'+r['time_settings']['units']
    for v in r['variables']:
        if v['name'] in pu:v['units']=pu[v['name']]
    p.write_text(json.dumps(r,indent=2)+'\n');e['candidate_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
(D/'MANIFEST.json').write_text(json.dumps(dict(candidates=E),indent=2)+'\n')
