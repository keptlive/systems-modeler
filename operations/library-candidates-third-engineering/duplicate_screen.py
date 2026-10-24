"""Bounded static expansion of scalar RHS DAGs; no authored expression evaluation."""
import ast,json,math,operator
from app.core.equations import preprocess_equation,canonical_name,decode_identifier
OPS={ast.Add:('add',operator.add),ast.Sub:('sub',operator.sub),ast.Mult:('mul',operator.mul),ast.Div:('div',operator.truediv),ast.Pow:('pow',operator.pow)}
def fingerprint(raw,abstract=False):
    stocks=raw.get('stocks',[]);stocknames={canonical_name(s['name']):i for i,s in enumerate(stocks)}
    if len(stocknames)!=len(stocks):raise ValueError('ambiguous stocks')
    variables={canonical_name(x['name']):x.get('equation','') for x in [*raw.get('variables',[]),*raw.get('flows',[])]}
    cache={};count=0
    def read(n,trail=()):
        nonlocal count
        count+=1
        if count>100000 or len(trail)>80:raise ValueError('bounded expansion')
        if isinstance(n,ast.Expression):return read(n.body,trail)
        if isinstance(n,ast.Constant) and type(n.value) in (int,float):return ('num',float(n.value))
        if isinstance(n,ast.Name):
            key=canonical_name(decode_identifier(n.id))
            if key in stocknames:return ('stock',stocknames[key])
            if key in variables:
                if key in trail:raise ValueError('cycle')
                if key not in cache:cache[key]=read(ast.parse(preprocess_equation(variables[key]),mode='eval'),trail+(key,))
                return cache[key]
            return ('external',key)
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.USub,ast.UAdd)):
            val=read(n.operand,trail)
            return ('num',-val[1]) if isinstance(n.op,ast.USub) and val[0]=='num' else val if isinstance(n.op,ast.UAdd) else ('neg',val)
        if isinstance(n,ast.BinOp) and type(n.op) in OPS:
            name,op=OPS[type(n.op)];left=read(n.left,trail);right=read(n.right,trail)
            if left[0]==right[0]=='num':
                try:
                    if name=='pow' and abs(right[1])>32:raise ValueError('large power')
                    value=op(left[1],right[1])
                    if isinstance(value,(int,float)) and math.isfinite(value) and abs(value)<1e100:return ('num',float(value))
                except (ValueError,OverflowError,ZeroDivisionError):pass
            if name in ('add','mul'):
                terms=[]
                for item in (left,right):terms.extend(item[1:]) if item[0]==name else terms.append(item)
                return (name,*sorted(terms,key=repr))
            return (name,left,right)
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name):return ('call',n.func.id.lower(),*(read(a,trail) for a in n.args))
        if isinstance(n,ast.Compare):return ('compare',tuple(type(op).__name__ for op in n.ops),read(n.left,trail),*(read(c,trail) for c in n.comparators))
        if isinstance(n,ast.BoolOp):return ('boolean',type(n.op).__name__,*(read(v,trail) for v in n.values))
        if isinstance(n,ast.IfExp):return ('conditional',read(n.test,trail),read(n.body,trail),read(n.orelse,trail))
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.Not):return ('not',read(n.operand,trail))
        raise ValueError(type(n).__name__)
    aliases={}
    for stock in stocks:
        for alias in {stock['id'],stock['name']}:
            if alias in aliases and aliases[alias]!=stock['id']:raise ValueError('ambiguous stock endpoint aliases')
            aliases[alias]=stock['id']
    rates=[]
    for stock in stocks:
        terms=[]
        for flow in raw.get('flows',[]):
            value=None
            if aliases.get(flow.get('to_stock'))==stock['id']:value=read(ast.parse(preprocess_equation(flow.get('equation','')),mode='eval'))
            if aliases.get(flow.get('from_stock'))==stock['id']:
                negative=read(ast.parse(preprocess_equation(flow.get('equation','')),mode='eval'));terms.append(('neg',negative))
            if value is not None:terms.extend(value[1:]) if value[0]=='add' else terms.append(value)
        rates.append(('add',*sorted(terms,key=repr)))
    if abstract:
        def mask(x):return ('num','constant') if isinstance(x,tuple) and x[0]=='num' else tuple(mask(v) for v in x) if isinstance(x,tuple) else x
        rates=mask(tuple(rates))
    return repr((len(stocks),rates))

def screen(root,directory):
    from tests.library_admission import baseline_models
    candidates=json.loads((directory/'MANIFEST.json').read_text())['candidates'];others={}
    # Exclude only individually reviewed, byte-exact admissions of this batch.
    # Preserve this screen as a regression after parent admits approved files.
    for index,raw in enumerate(baseline_models(root,{e['id'] for e in candidates})):
        others['active/'+raw.get('id',str(index))]=raw
    paths=[p for p in (root/'operations').glob('library-candidates*/*.json') if p.parent!=directory]
    for p in paths:
        value=json.loads(p.read_text())
        if isinstance(value,dict) and value.get('stocks') and value.get('flows'):others[str(p.relative_to(root))]=value
    known={};shapes={};skipped=[]
    for path,raw in others.items():
        try:
            known.setdefault(fingerprint(raw),[]).append(path);shapes.setdefault(fingerprint(raw,True),[]).append(path)
        except (ValueError,SyntaxError,RecursionError,TypeError):skipped.append(path)
    rows=[]
    for e in candidates:
        raw=json.loads((directory/e['file']).read_text());rows.append(dict(file=e['file'],exact_expanded_matches=known.get(fingerprint(raw),[]),constant_abstracted_shape_matches=shapes.get(fingerprint(raw,True),[])))
    return dict(compared=len(others),expanded=len(others)-len(skipped),unexpanded=skipped,candidates=rows,limits='Stock order preserved; no state permutation/isomorphism, transcendental identity or initial-condition equivalence proof. Non-scalar/cyclic/unsupported expressions listed rather than silently claimed screened.')
