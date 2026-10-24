"""Strict bounded scalar Vensim MDL importer with source and loss reporting."""
import json
import math
import re
from app.core.equations import canonical_name, symbol_identity, resolve_name, validate_equation

MAX_SOURCE_BYTES = 2_000_000
MAX_RECORDS = 500
MAX_EXPRESSION = 100_000
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"

class MDLImportError(ValueError):
    def __init__(self, message, original_source, code="unsupported_mdl", record=None):
        self.original_source = original_source
        self.diagnostics = [{"severity":"error","code":code,"message":message,"record":record}]
        super().__init__(message)

def parse_mdl(text):
    """Return model, diagnostics, original_source and source_format; never guess topology."""
    def fail(message, code="unsupported_mdl", record=None):
        raise MDLImportError(message, text, code, record)
    if not isinstance(text, str):
        fail("MDL source must be text", "invalid_source")
    try:
        source_bytes = len(text.encode("utf-8"))
    except UnicodeEncodeError:
        fail("MDL source must contain valid Unicode scalar values", "invalid_source")
    if source_bytes > MAX_SOURCE_BYTES:
        fail("MDL source exceeds two megabytes", "resource_limit")
    diagnostics = []
    def warn(code, message, record=None):
        diagnostics.append({"severity":"warning","code":code,"message":message,"record":record})
    # A sketch marker is recognized only at the beginning of a physical line.
    marker = re.search(r"(?m)^\\\\\\---///", text)
    source = text[:marker.start()] if marker else text
    if marker:
        warn("display_metadata_omitted", "Sketch and trailing Vensim display/settings metadata retained in original_source, not imported into the editor")
    source = re.sub(r"^\s*\{UTF-8\}", "", source, count=1, flags=re.I)
    # Split delimiters outside quoted names and brace comments. Comments cannot
    # create equations or hide a delimiter inside a quoted identifier.
    records, fields, chars = [], [], []
    quoted, comment, escaped = False, 0, False
    for character in source:
        if comment:
            if character == "{": comment += 1
            elif character == "}": comment -= 1
            continue
        if character == '"' and not escaped:
            quoted = not quoted
        if not quoted and character == "{":
            comment = 1
            chars.append(" ")
            continue
        if not quoted and character in "~|":
            fields.append("".join(chars).strip()); chars=[]
            if character == "|":
                records.append(fields); fields=[]
                if len(records) > MAX_RECORDS:
                    fail("Too many MDL records", "resource_limit")
        else:
            chars.append(character)
        escaped = character == "\\" and not escaped if quoted else False
    if quoted or comment:
        fail("Unterminated quoted name or brace comment", "invalid_syntax")
    if "".join(chars).strip() or fields:
        fail("MDL equation records must end with a pipe", "invalid_syntax")
    entries, controls = [], {}
    names = {}
    for number, fields in enumerate(records, 1):
        head = re.sub(r"\\\s*\n", " ", fields[0]).strip()
        if not head:
            continue
        if re.fullmatch(r"\*+\s*\.[\s\S]*?\*+", head):
            warn("group_metadata_omitted", "Display group retained only in original source", number)
            continue
        if len(fields) > 3:
            fail("Unsupported extra record fields", record=number)
        if ":MACRO:" in head.upper() or ":END OF MACRO:" in head.upper():
            fail("MDL macros are not supported", record=number)
        # Find assignment outside names; lookup declarations have no equals sign.
        quote = False
        quote_escape = False
        assignment = None
        for i,c in enumerate(head):
            if c == '"' and not quote_escape: quote = not quote
            quote_escape = c == "\\" and not quote_escape if quote else False
            if c == "=" and not quote:
                assignment=i; break
        if assignment is None:
            fail("Only scalar assignment records are supported; standalone lookup/dimension declarations are unsupported", record=number)
        lhs, rhs = head[:assignment].strip(), head[assignment+1:].strip()
        if lhs.startswith('"') and lhs.endswith('"'):
            try: name=json.loads(lhs)
            except ValueError: fail("Invalid quoted identifier", "invalid_syntax", number)
        else:
            name=re.sub(r"\s+", " ", lhs).strip()
        if not name or any(c in name for c in "[]:~|=()\\") or name.startswith("*"):
            fail("Arrays, macros and non-scalar declarations are unsupported", record=number)
        key=symbol_identity(name)
        if key in {"time", "dt"}:
            fail("Variable name conflicts with reserved scalar execution symbol", "duplicate_name", number)
        if key in names:
            fail("Duplicate or ambiguous variable names", "duplicate_name", number)
        names[key]=name
        units=fields[1].strip() if len(fields)>1 else ""
        bounds=re.search(r"\s*\[[^\]]*\]\s*$",units)
        if bounds:
            units=units[:bounds.start()].strip()
            warn("unit_range_metadata", "Unit range annotation retained in original source; not enforced as an execution constraint", number)
        if not rhs:
            fail("Empty equations are unsupported", "invalid_syntax", number)
        if len(rhs) > MAX_EXPRESSION:
            fail("Equation exceeds expression budget", "resource_limit", number)
        if key in {"initial_time","final_time","time_step","saveper"}:
            controls[key]=(rhs,units,number)
        else:
            entries.append({"name":name,"rhs":rhs,"units":units or None,"record":number})
    if not entries:
        fail("MDL contains no scalar model equations", "invalid_syntax")
    if len(entries)*2 > MAX_RECORDS:
        fail("Conservative expanded element limit exceeded", "resource_limit")
    def numeric_control(key, default):
        if key not in controls:
            warn("default_control", f"Missing {key}; explicit default {default} applied")
            return default
        rhs,_,n=controls[key]
        if not re.fullmatch(NUMBER,rhs) or not math.isfinite(float(rhs)):
            fail("Simulation controls require finite numeric literals", record=n)
        return float(rhs)
    start=numeric_control("initial_time",0)
    end=numeric_control("final_time",100)
    dt=numeric_control("time_step",0.25)
    if dt <= 0 or end <= start or dt > end-start:
        fail("Invalid simulation time grid", "invalid_control")
    if "saveper" in controls:
        save=controls["saveper"][0].strip()
        if canonical_name(save) != "time_step" and (not re.fullmatch(NUMBER,save) or float(save)!=dt):
            fail("SAVEPER must equal TIME STEP; output resampling is unsupported", record=controls["saveper"][2])
    time_units = next((controls[k][1] for k in ("time_step","initial_time","final_time") if k in controls and controls[k][1]),None)
    if time_units and any(unit and canonical_name(unit)!=canonical_name(time_units) for _,unit,_ in controls.values()):
        fail("Conflicting simulation time units", "invalid_control")
    model={"name":"Imported MDL model","stocks":[],"flows":[],"variables":[],"tables":[],"connectors":[],
        "time_settings":{"start":start,"end":end,"dt":dt,"units":time_units,"integration_method":"euler"}}
    # Declared names are matched longest first, case-insensitively; spaces and
    # underscores share the engine's documented identifier alias convention.
    model_names={symbol_identity(e["name"]):e["name"] for e in entries}
    candidates=dict(model_names)
    # Retain only unambiguous legacy spellings; literal declarations win.
    legacy = {}
    for name in model_names.values():
        legacy.setdefault(canonical_name(name), []).append(name)
    candidates.update({key: names[0] for key,names in legacy.items()
                       if len(names) == 1 and key not in candidates})
    candidates.update({"time":"TIME","time_step":"DT","initial_time":"STARTTIME","final_time":"STOPTIME"})
    patterns=[]
    for key,name in candidates.items():
        pattern=r"[ _\n\u00a0]+".join(re.escape(part) for part in key.split("_"))
        patterns.append((re.compile(pattern,re.I),key,name))
    patterns.sort(key=lambda x:len(x[1]),reverse=True)
    funcs={"IF THEN ELSE":"IF_THEN_ELSE",
        "SIN":"sin","COS":"cos","TAN":"tan","ARCSIN":"asin","ARCCOS":"acos","ARCTAN":"atan",
        "EXP":"exp","LN":"ln","SQRT":"sqrt","ABS":"abs","MIN":"min","MAX":"max","STEP":"STEP",
        "LOG":"log","POWER":"pow","INTEGER":"TRUNC","MODULO":"MODULO","ZIDZ":"ZIDZ","XIDZ":"XIDZ","SMOOTH":"SMOOTH","SMOOTHI":"SMOOTH",
        "SMOOTH3":"SMOOTH3","SMOOTH3I":"SMOOTH3"}
    # Vensim function contracts, not spelling-based aliases. LOG has an explicit
    # base; information smooths share the engine's continuous hidden-stock law.
    # https://vensim.com/documentation/fn_log.html (x, base)
    # https://vensim.com/documentation/fn_power.html (base, exponent)
    # https://vensim.com/documentation/fn_smooth.html and fn_smooth3.html
    # https://vensim.com/documentation/fn_integer.html truncates toward zero, not floor.
    # https://vensim.com/documentation/fn_xidz.html and fn_zidz.html require
    # abs(denominator)<1e-6; never translate these into exact-zero SAFEDIV.
    # Simlin0.8.5 MDL currently translates them to SAFEDIV: that dialect mismatch
    # is intentional here in favor of the documented Vensim source semantics.
    # MODULO uses its distinct C-remainder primitive, never Python mod.
    # https://vensim.com/documentation/fn_modulo.html
    # Deliberately no PULSE (width/height), RANDOM (seed /
    # truncation), SMOOTH N (discrete/order reduction), or material DELAY aliases.
    strict_arities={"LOG":2,"POWER":2,"INTEGER":1,"MODULO":2,"ZIDZ":2,"XIDZ":3,"SMOOTH":2,"SMOOTHI":3,"SMOOTH3":2,"SMOOTH3I":3}
    function_patterns=[(re.compile(r"[ _\s]+".join(k.split()),re.I),v) for k,v in sorted(funcs.items(),key=lambda x:-len(x[0]))]
    translation_work = 0
    def charge_translation(record):
        nonlocal translation_work
        translation_work += 1
        if translation_work > 2_000_000:
            fail("MDL translation work budget exceeded", "resource_limit", record)
    def translate(expr, record):
        output=[]; pos=0
        while pos<len(expr):
            if expr[pos].isspace():
                output.append(" ");pos+=1;continue
            matched=False
            for pattern,fn in function_patterns:
                charge_translation(record)
                m=pattern.match(expr,pos)
                if m and expr[m.end():].lstrip().startswith("("):
                    spelling=re.sub(r"[ _\s]+"," ",m.group()).upper()
                    if spelling in strict_arities:
                        begin=m.end()
                        while expr[begin].isspace():begin+=1
                        depth=0;quoted=False;escaped=False;end=None
                        for index in range(begin,len(expr)):
                            charge_translation(record)
                            char=expr[index]
                            if char=='"' and not escaped:quoted=not quoted
                            if not quoted:
                                if char=='(':depth+=1
                                elif char==')':
                                    depth-=1
                                    if depth==0:end=index;break
                            escaped=char=='\\' and not escaped if quoted else False
                        if end is None:fail("Unbalanced function arguments","invalid_syntax",record)
                        arguments=split_args(expr[begin+1:end],record)
                        if len(arguments)!=strict_arities[spelling] or not all(arguments):
                            fail(spelling+" requires "+str(strict_arities[spelling])+" arguments","invalid_syntax",record)
                    output.append(fn);pos=m.end();matched=True;break
            if matched:continue
            if expr[pos]=='"':
                m=re.match(r'"(?:[^"\\]|\\.)*"',expr[pos:])
                if not m:fail("Unterminated identifier", "invalid_syntax",record)
                try:owner=resolve_name(json.loads(m.group()), model_names.values())
                except ValueError:fail("Invalid quoted identifier","invalid_syntax",record)
                if owner is None:fail("Unknown quoted reference",record=record)
                output.append(json.dumps(owner));pos+=len(m.group());continue
            number=re.match(NUMBER,expr[pos:])
            # Signs are operators; retaining a signed numeric token is equivalent.
            if number:
                if not math.isfinite(float(number.group())):
                    fail("Nonfinite numeric literal", "invalid_syntax", record)
                output.append(number.group());pos+=len(number.group());continue
            for pattern,key,name in patterns:
                charge_translation(record)
                m=pattern.match(expr,pos)
                if m and (m.end()==len(expr) or not (expr[m.end()].isalnum() or expr[m.end()]=="_")):
                    if key in ("initial_time","final_time"):
                        if resolve_name(name,model_names.values()) is not None:
                            fail("Dynamic simulation control "+key+" conflicts with declared "+name,record=record)
                    output.append(json.dumps(name) if key in model_names else name)
                    pos=m.end();matched=True;break
            if matched:continue
            for operator,replacement in ((":AND:"," and "),(":OR:"," or "),(":NOT:"," not "),("<>","!="),("<=","<="),(">=",">="),("=","=="),("^","**")):
                if expr[pos:pos+len(operator)].upper()==operator:
                    output.append(replacement);pos+=len(operator);matched=True;break
            if matched:continue
            if expr[pos] in "+-*/(),<>":
                output.append(expr[pos]);pos+=1;continue
            fail("Unsupported function, reference, subscript, or operator near "+repr(expr[pos:pos+35]),record=record)
        return "".join(output).strip()

    def split_args(body, record):
        depth=0;quote=False;quote_escape=False;parts=[];begin=0
        for i,c in enumerate(body):
            if c=='"' and not quote_escape:quote=not quote
            quote_escape = c == "\\" and not quote_escape if quote else False
            if quote:continue
            if c=="(":depth+=1
            elif c==")":
                depth-=1
                if depth<0:fail("Unbalanced parentheses","invalid_syntax",record)
            elif c=="," and depth==0:
                parts.append(body[begin:i].strip());begin=i+1
        if depth or quote:fail("Unbalanced function arguments","invalid_syntax",record)
        return parts+[body[begin:].strip()]

    for entry in entries:
        name,rhs,units,record=(entry[k] for k in ("name","rhs","units","record"))
        integ=re.match(r"(?is)^INTEG\s*\(",rhs)
        if integ:
            if not rhs.rstrip().endswith(")"):fail("Malformed INTEG","invalid_syntax",record)
            parts=split_args(rhs[integ.end():].rstrip()[:-1],record)
            if len(parts)!=2 or not all(parts):fail("INTEG requires derivative and initial value","invalid_syntax",record)
            derivative,initial=(translate(p,record) for p in parts)
            ident="mdl:"+name
            stock={"id":ident,"name":name,"units":units,"initial_value":0,"equation":initial}
            if re.fullmatch(NUMBER,parts[1]):
                value=float(parts[1])
                if not math.isfinite(value):fail("Nonfinite initial value","invalid_syntax",record)
                stock.update(initial_value=value,equation="")
            model["stocks"].append(stock)
            # An explicit signed net inflow preserves dStock/dt without claiming
            # the source syntax establishes material connections or conservation.
            model["flows"].append({"id":"mdl:net:"+name,"name":"MDL net derivative "+name,
                "equation":derivative,"to_stock":ident,"units":f"({units})/({time_units})" if units and time_units else None})
            warn("net_derivative_flow","Stock derivative represented by a signed net inflow; material-flow topology was not inferred",record)
        else:
            if re.search(r"\bINTEG\s*\(",rhs,re.I):
                fail("Nested INTEG is unsupported",record=record)
            inline = re.match(r"(?is)^WITH[ _\s]+LOOKUP\s*\(",rhs)
            if inline:
                if not rhs.rstrip().endswith(")"):fail("Malformed WITH LOOKUP","invalid_syntax",record)
                parts=split_args(rhs[inline.end():].rstrip()[:-1],record)
                if len(parts)!=2:fail("WITH LOOKUP requires input and point table","invalid_syntax",record)
                table_body=parts[1].strip()
                if not (table_body.startswith("(") and table_body.endswith(")")):
                    fail("Lookup points require a parenthesized table","invalid_syntax",record)
                table_body=table_body[1:-1].strip()
                if table_body.startswith("["):
                    range_match=re.match(r"\[\s*\(\s*"+NUMBER+r"\s*,\s*"+NUMBER+r"\s*\)\s*-\s*\(\s*"+NUMBER+r"\s*,\s*"+NUMBER+r"\s*\)\s*\]\s*,",table_body)
                    if not range_match:fail("Malformed lookup plot range","invalid_syntax",record)
                    table_body=table_body[range_match.end():].strip()
                    warn("lookup_plot_range","Lookup plot range retained in source; interpolation uses explicit points",record)
                point_parts=split_args(table_body,record)
                if not 2 <= len(point_parts) <= 1000:
                    fail("Lookup requires 2 to 1000 points","resource_limit",record)
                points=[]
                for point in point_parts:
                    match=re.fullmatch(r"\(\s*("+NUMBER+r")\s*,\s*("+NUMBER+r")\s*\)",point)
                    if not match:fail("Lookup coordinates require finite numeric literals","invalid_syntax",record)
                    pair=[float(v) for v in match.groups()]
                    if not all(math.isfinite(v) for v in pair):fail("Nonfinite lookup coordinate","invalid_syntax",record)
                    if points and pair[0] <= points[-1][0]:fail("Lookup x coordinates must increase strictly","invalid_syntax",record)
                    points.append(pair)
                table_name="MDL table "+name
                model["tables"].append({"name":table_name,"points":points,"interpolation":"continuous"})
                expression="LOOKUP("+json.dumps(table_name)+", "+translate(parts[0],record)+")"
            else:
                expression=translate(rhs,record)
            model["variables"].append({"id":"mdl:"+name,"name":name,"equation":expression,"units":units})
    all_names=[e["name"] for k in ("stocks","flows","variables") for e in model[k]]
    canonical=[symbol_identity(n) for n in all_names]
    if len(canonical)!=len(set(canonical)):
        fail("Generated net flow name conflicts with source variable","duplicate_name")
    for kind in ("stocks","flows","variables"):
        for item in model[kind]:
            if item.get("equation"):
                ok, errors=validate_equation(item["equation"],all_names,[t["name"] for t in model["tables"]])
                if not ok:fail("Invalid scalar equation: "+str(errors),"invalid_equation")
    warn("solver_semantics","Imported numeric controls use Euler; solver options in trailing Vensim metadata are not applied")
    return {"model":model,"diagnostics":diagnostics,"original_source":text,"source_format":"vensim_mdl"}

