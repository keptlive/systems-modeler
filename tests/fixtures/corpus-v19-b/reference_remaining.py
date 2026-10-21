import json, math, warnings, sys
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
R=Path(__file__).resolve().parents[3]

def platform(t,y):
    u,p,tr,uv,pv,c=y
    ua=(1e5-u-c)*.01*uv/(uv+10);uc=u*.05*(1-uv/50)
    pa=(1000-p)*.02*pv/(pv+5);pc=p*.03*(1-pv/25)
    switch=c*.02*uv/20
    return [ua-uc+switch,pa-pc,.1*u*p/1000,(p/10+p/100-uv)/10,(u/200+.2*u/10000-pv)/10,-switch]

def rd(t,y):
    k,n,c,p,g,r=y;create=.01*n*math.sqrt(c/1e6)*(1+.2*k/100)
    return [create-.05*k,1000-.08*n,.15*r-.1*c,.3*create-p/20,.1*p-g/7,1e5*g-.9*r]

def chips(t,y):
    f,c,i,b,a=y;ship=min(i,b/4)
    return [c/24,.1*f*b/1000/12-c/24,.9*f-ship,1040*(1+b/1000)-ship,0]

def startup(t,y):
    s,f,talent,x=y;fail=s*.2*(1-(.3+.1*math.log10(1+s)));exit=s*.05
    return [.01*talent*f/(10000+f)-fail-exit,500*(1+.5*x/10)-s*50,200*(1+x/20+s/200)-s*10+fail*10*.7,exit]

def trophic(t,y):
    a,m,h,v=y
    return [.05*a*m/1000-.02*a,.1*m*h/5000-5*a,.15*h*v/20000-2*m-3*a,.3*v*(1-v/20000)-3*h]

def online(t,y):
    e,a,c,d,q=y;enroll=500*(1+.3*c/1000);activate=e*.3*q/100;complete=.12*a;early=.4*e;late=.2*a*(1-q/100)
    return [enroll-activate-early,activate-complete-late,complete,early+late,5+.01*c]

def peer(t,y):
    w,r,v,i,h,s=y
    resistance=w*(s*2+i*v*5)*.1;willing=r*h*20*v*1.5;vax=w*.03*min(1,t/60)
    infect=(w+r)*.25*i*(1-.85*(v/.7));hospital=.05*i
    return [willing-resistance-vax,resistance-willing,vax,infect-hospital,hospital,vax*.02-s*.05]

def leverage(t,y):
    p,l,m=y;target=.4 if p<90 else .15 if p>110 else .2
    return [p*.02*(1+.05*(l-5))-p*.1*max(0,m-.2),l*.1*(p/100-1) if p>100 else 0,(target-m)/2]

cases=[('platform-network-effects-advanced-eco',platform,[1000,50,0,10,5,5000],100),('rd-investment-innovation-eco',rd,[100,10000,5e7,500,100,1e7],50),('semiconductor-chip-shortage-supply-chain-eco',chips,[1000,100,500,200,100],104),('startup-ecosystem-dynamics-eco',startup,[100,10000,5000,10],20),('trophic-cascade-ecosystem-eco',trophic,[50,500,2000,10000],100),('online-learning-platform-edu',online,[0,0,0,0,0],52),('peer-vaccination-network-nudge-epi',peer,[.5,.3,.15,.02,.003,.01],365),('leverage-cycle-dynamics-fin',leverage,[100,5,.2],100)]
rows={}
for name,rhs,y0,end in cases:
    def stop(t,y):return 1e80-max(abs(v) for v in y)
    stop.terminal=True;stop.direction=-1
    row={}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try:
            sol=solve_ivp(rhs,(0,end),y0,method='Radau',rtol=1e-9,atol=1e-10,events=stop,dense_output=True)
            row=dict(success=bool(sol.success and sol.t[-1]==end),status=sol.message,end=float(sol.t[-1]),nfev=sol.nfev,minimum=sol.y.min(axis=1).tolist(),maximum=sol.y.max(axis=1).tolist(),last=sol.y[:,-1].tolist(),threshold_event=bool(len(sol.t_events[0])))
        except Exception as e:row=dict(success=False,error=str(e))
    rows[name]=row;print(name,json.dumps(row),flush=True)

# DDE momentum reference, independent continuous method of steps with native history100.
segments=[];state=[100.,0.,0.];total_evals=0
def past(q):
    if q<0:return 100.
    return segments[min(int(q),len(segments)-1)].sol(q)[0]
def rhs(t,y):
    p,m,d=y
    return [p*(.001+.01*d),(p-past(t-5))/5-.1*m,(5*m-d)/2]
def stop(t,y):return 1e40-max(abs(v) for v in y)
stop.terminal=True;stop.direction=-1
for day in range(200):
    sol=solve_ivp(rhs,(day,day+1),state,method='Radau',rtol=1e-9,atol=1e-10,dense_output=True,events=stop)
    total_evals+=sol.nfev
    if sol.t[-1]<day+1:break
    segments.append(sol);state=sol.y[:,-1]
rows['momentum-trading-dynamics-fin']=dict(success=bool(sol.success and sol.t[-1]==200),status=sol.message,end=float(sol.t[-1]),nfev=total_evals,last=sol.y[:,-1].tolist(),threshold_event=bool(len(sol.t_events[0])))
print('momentum',rows['momentum-trading-dynamics-fin'],flush=True)
(R/'tests/fixtures/corpus-v19-b/independent-remaining.json').write_text(json.dumps(rows,indent=2)+'\n')
