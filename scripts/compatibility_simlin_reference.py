"""Optional observed semantics probe. Run with an isolated pysimlin environment.
The installed wheel is not asserted to have been built from the inspected source pin.
"""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, math, subprocess, tempfile
from pathlib import Path
from xml.sax.saxutils import escape

PIN = "3f87e9024a580b86b65e3d0c5c3353660fc5426e"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def number(x):
    x=float(x)
    return x if math.isfinite(x) else {"nonfinite": "nan" if math.isnan(x) else "positive_infinity" if x>0 else "negative_infinity"}

def cases():
    for expr in ["STARTTIME", "STOPTIME", "STARTTIME()", "STOPTIME()", "initial_time", "final_time", "ARCSIN(-1)", "ARCCOS(1)", "ARCTAN(-1)", "ASIN(0.5)", "ACOS(0.5)", "ATAN(1)", "ARCSIN(2)", "INT(-3.2)", "TRUNC(-3.2)", "INTEGER(-3.2)", "ROUND(2.5)", "ROUND(-2.5)", "QUANTUM(-9.9,3)", "QUANTUM(9.9,0)", "QUANTUM(-9.9,-3)", "REM(-10,3)", "MODULO(-10,3)", "LOG(100)", "LOG(8,2)", "SAFEDIV(1,0)", "SAFEDIV(1,0,9)", "SAFEDIV(1,1e-9,9)", "SAFEDIV(1,2,1/0)", "SAFEDIV(SQRT(-1),0,9)"]:
        yield "xmile",expr
    for expr in ["INTEGER(-3.2)", "INTEGER(3.2)", "QUANTUM(-9.9,3)", "QUANTUM(9.9,0)", "QUANTUM(-9.9,-3)", "MODULO(-10,3)", "LOG(100)", "LOG(8,2)", "ARCSIN(-1)", "IF THEN ELSE(1,7,1/0)", "XIDZ(1,2,1/0)"]:
        yield "mdl",expr
    for dialect in ("xmile","mdl"):
        for denominator in ("0", "-0.0", "1e-9", "-1e-9", "0.000000999999", "0.000001", "-0.000001", "0.000001000001"):
            for name in ("ZIDZ", "XIDZ"):
                yield dialect,f"{name}(1,{denominator}"+(",9)" if name=="XIDZ" else ")")

def source(dialect,expr):
    if dialect=="mdl":
        return "{UTF-8}\nOutput = "+expr+" ~ dimensionless ~ |\nINITIAL TIME = 5 ~ second ~ |\nFINAL TIME = 6 ~ second ~ |\nTIME STEP = 0.25 ~ second ~ |\nSAVEPER = TIME STEP ~ second ~ |\n"
    return '<xmile xmlns="http://docs.oasis-open.org/xmile/ns/XMILE/v1.0" version="1.0"><sim_specs method="Euler"><start>5</start><stop>6</stop><dt>0.25</dt></sim_specs><model name="main"><variables><aux name="Output"><eqn>'+escape(expr)+'</eqn></aux></variables></model></xmile>'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    import simlin
    head=subprocess.check_output(["git","-C",str(args.source),"rev-parse","HEAD"],text=True).strip()
    if head!=PIN:
        raise SystemExit("Inspected source pin differs")
    files=["src/simlin-engine/src/builtins.rs","src/simlin-engine/src/vm.rs","src/simlin-engine/src/mdl/xmile_compat.rs"]
    result={"distribution":"pysimlin","installed_version":importlib.metadata.version("pysimlin"),"inspected_source_commit":head,"wheel_source_equivalence_asserted":False,"source_sha256":{f:sha((args.source/f).read_bytes()) for f in files},"native_sha256":{p.name:sha(p.read_bytes()) for p in Path(simlin.__file__).parent.rglob("*.so")},"scope":"Original one-output scalar probes, Euler start=5 stop=6 dt=0.25. Observations, not a universal compatibility claim. Nonfinite output does not prove lazy or eager evaluation. No performance measurement.","cases":[]}
    with tempfile.TemporaryDirectory(prefix="simlin-functions-") as folder:
        for i,(dialect,expr) in enumerate(cases()):
            raw=source(dialect,expr)
            path=Path(folder)/f"probe-{i}.{dialect}"
            path.write_text(raw)
            row={"dialect":dialect,"expression":expr,"input_sha256":sha(raw.encode())}
            try:
                frame=simlin.load(path).run(analyze_loops=False).results
                row.update(time=[number(v) for v in frame.index],output=[number(v) for v in frame["output"]])
            except Exception as error:
                row["error"]={"type":type(error).__name__,"message":str(error)[:2000]}
            result["cases"].append(row)
    # Identical graphical-function geometry; ordinary name is a syntax control.
    with tempfile.TemporaryDirectory(prefix="simlin-table-") as folder:
        for name,args_text,lookup in (("Curve","0.5",False),("TRUNC","0.5",False),("SAFEDIV","0.5",False),("SAFEDIV","4,2",False),("Curve","0.5",True),("TRUNC","0.5",True),("SAFEDIV","0.5",True)):
            expression=("LOOKUP("+name+","+args_text+")") if lookup else name+"("+args_text+")"
            raw=source("xmile",expression)
            table='<aux name="'+name+'"><eqn>0</eqn><gf type="continuous"><xscale min="0" max="1"/><yscale min="10" max="20"/><ypts>10,20</ypts></gf></aux>'
            raw=raw.replace('<variables>','<variables>'+table)
            path=Path(folder)/"table.xmile"
            path.write_text(raw)
            row={"dialect":"xmile","expression":expression,"graphical_function":{"name":name,"xscale":[0,1],"ypts":[10,20]},"input_sha256":sha(raw.encode())}
            try:
                frame=simlin.load(path).run(analyze_loops=False).results
                row.update(time=[number(v) for v in frame.index],output=[number(v) for v in frame["output"]])
            except Exception as error:
                row["error"]={"type":type(error).__name__,"message":str(error)[:2000]}
            result["cases"].append(row)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(f"Recorded {len(result['cases'])} observations; {sum('error' in c for c in result['cases'])} rejected probes")

if __name__=="__main__":
    main()
