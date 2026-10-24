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

m=model('holt-shared-predator-fifth-systems','Shared-predator apparent competition between independent prey','Original illustrative normalized-density implementation of Holt1977 equations8-9 page204. Two prey have separate logistic resource bases and share a food-limited predator; no direct interspecific competition. Densities are divided by fixed reference densities, so capacities and conversion/nutritional coefficients use the same normalized convention. Nonnegative parameters and initial densities, positive capacities, time in days. Original defaults, no empirical fit. No adaptive diet, handling-time saturation, spatial structure, stochastic extinction or positivity clamp. Solver/step changes can break numerical positivity.','ecology','https://people.clas.ufl.edu/rdholt/files/001.pdf','Holt,R.D.(1977). Predation, apparent competition, and the structure of prey communities. Theoretical Population Biology12:197-229. doi:10.1016/0040-5809(77)90042-9. Original authored equations/JSON; no paper text/figures/code copied.',80,.025,'day')
for i,(n,v) in enumerate([('Prey_1',.9),('Prey_2',.6),('Predator',.2)]):stock(m,n,v,'1',200+350*i,410)
for n,v,u in [('Growth_1',1,'1/day'),('Growth_2',.8,'1/day'),('Capacity_1',1.5,'1'),('Capacity_2',1.2,'1'),('Capture_1',.8,'1/day'),('Capture_2',.6,'1/day'),('Food_Value_1',1,'1'),('Food_Value_2',.8,'1'),('Conversion',.5,'1'),('Maintenance',.5,'1/day')]:variable(m,n,v,u)
for i in (1,2):
 flow(m,f'Prey_{i}_Births',f'Growth_{i} * Prey_{i}','1/day',to=f'Prey_{i}')
 flow(m,f'Prey_{i}_Crowding',f'Growth_{i} * Prey_{i}^2 / Capacity_{i}','1/day',fr=f'Prey_{i}')
 flow(m,f'Prey_{i}_Predation',f'Capture_{i} * Prey_{i} * Predator','1/day',fr=f'Prey_{i}')
flow(m,'Predator_Recruitment','Conversion * (Capture_1 * Food_Value_1 * Prey_1 + Capture_2 * Food_Value_2 * Prey_2) * Predator','1/day',to='Predator')
flow(m,'Predator_Mortality','Conversion * Maintenance * Predator','1/day',fr='Predator')
finish(m)

m=model('three-stage-adsorption-breakthrough-fifth-systems','Three-stage adsorption breakthrough with finite-rate sorbent equilibration','Original three well-mixed equal-volume cells in series with one dissolved species and finite-rate Langmuir q*-based LDF uptake/desorption. CADET v5.1.1 CSTR and binding equations are mathematical references, not copied implementation or fixtures. Coarse network, not a plug-flow/PDE solver or calibrated industrial column. Solute stocks in milligrams, liquid volumes liters, sorbent masses grams, time seconds. Positive volume; nonnegative flow, capacity, affinity, solid mass, kinetic coefficient and liquid masses; sorbed masses initially within finite capacity. Defaults initially zero. Reversible uptake and internal advection transfer equal mass between stocks; effluent accumulation closes the feed budget. No explicit axial dispersion term, thermal feedback, pore diffusion, multicomponent competition, depletion clamp or parameter estimation.','engineering','https://cadet.github.io/v5.1.1/modelling/binding/multi_component_langmuir_ldf.html','CADET v5.1.1 official documentation: Binding models, Linear Driving Force; Multi Component Langmuir LDF; Continuous stirred tank reactor model. q*-based LDF, not native kinetic Langmuir or liquid-phase LDF. Original network/defaults, not a bundled example.',30,.02,'second')
for j in (1,2,3):
 stock(m,f'Aqueous_Mass_{j}',0,'milligram',170+(j-1)*300,390)
 stock(m,f'Sorbed_Mass_{j}',0,'milligram',170+(j-1)*300,570)
stock(m,'Effluent_Mass',0,'milligram',1100,390)
for n,v,u in [('Liquid_Volume',1,'liter'),('Flow_Rate',.5,'liter/second'),('Feed_Concentration',1,'milligram/liter'),('Solid_Mass',1,'gram'),('Capacity',2,'milligram/gram'),('Affinity',1,'liter/milligram'),('Kinetic_Rate',.5,'1/second')]:variable(m,n,v,u)
for j in (1,2,3):
 variable(m,f'Concentration_{j}',f'Aqueous_Mass_{j} / Liquid_Volume','milligram/liter')
 variable(m,f'Equilibrium_Loading_{j}',f'Capacity * Affinity * Concentration_{j} / (1 + Affinity * Concentration_{j})','milligram/gram')
flow(m,'Feed_Mass_Rate','Flow_Rate * Feed_Concentration','milligram/second',to='Aqueous_Mass_1')
for j in (1,2,3):
 flow(m,f'Advected_Mass_{j}',f'Flow_Rate * Concentration_{j}','milligram/second',fr=f'Aqueous_Mass_{j}',to=f'Aqueous_Mass_{j+1}' if j<3 else 'Effluent_Mass')
 flow(m,f'Reversible_Uptake_{j}',f'Kinetic_Rate * (Solid_Mass * Equilibrium_Loading_{j} - Sorbed_Mass_{j})','milligram/second',fr=f'Aqueous_Mass_{j}',to=f'Sorbed_Mass_{j}')
variable(m,'Tracked_Mass',' + '.join(s['name'] for s in m['stocks']),'milligram')
finish(m)
