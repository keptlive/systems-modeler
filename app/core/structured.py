"""Bounded, native structured-model lowering. No simulation or eval occurs here."""
from copy import deepcopy
from itertools import product
import json
import re
from app.core.equations import canonical_name
from app.core.array_reductions import Budget, Selection, ReductionError, lower_expression

MAX_CELLS = 4096
MAX_MODULE_DEPTH = 8
MAX_INSTANCES = 128
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*(?:\[[^\[\]]*\])?')

class StructuredModelError(ValueError):
    def __init__(self, code, message, path="$"):
        self.code, self.path = code, path
        self.diagnostics = [{"severity": "error", "code": code, "message": message, "path": path}]
        super().__init__(f"{path}: {message}")

def fail(code, message, path="$"):
    raise StructuredModelError(code, message, path)

def compile_structured_model(raw):
    """Return model/source_map/diagnostics; original input is never mutated."""
    if not isinstance(raw, dict):
        fail("invalid_schema", "Model must be an object")
    for kind in ("stocks", "flows", "variables"):
        if kind in raw and not isinstance(raw[kind], list):
            fail("invalid_schema", f"{kind} must be a list")
    for key, expected in (("dimensions", list), ("modules", list), ("module_definitions", dict)):
        if key in raw and not isinstance(raw[key], expected):
            fail("invalid_schema", f"{key} has an invalid container type")
    structured_elements = any(isinstance(e, dict) and any(e.get(k) for k in ("dimensions", "equations", "initial_values")) for kind in ("stocks", "flows", "variables") for e in raw.get(kind, []) if isinstance(raw.get(kind), list))
    if not structured_elements and not any(raw.get(k) for k in ("dimensions", "modules", "module_definitions")):
        return {"model": deepcopy(raw), "source_map": {}, "diagnostics": []}
    if not isinstance(raw.get("dimensions", []), list):
        fail("invalid_schema", "dimensions must be a list")
    if len(raw.get("dimensions", [])) > 32:
        fail("resource_limit", "Too many dimensions")
    dims = {}
    for d in raw.get("dimensions", []):
        if not isinstance(d, dict) or (not isinstance(d.get("name"), str) or len(d["name"]) > 128 or not IDENT.fullmatch(d["name"])):
            fail("invalid_dimension", "Dimensions require identifier names")
        if set(d) - {"name", "elements"}:
            fail("unsupported_semantics", "Dimension mappings and extra dimension fields are unsupported")
        name, elements = d["name"], d.get("elements")
        if name in dims or not isinstance(elements, list) or not elements or any(not isinstance(e, str) or len(e) > 128 or not IDENT.fullmatch(e) for e in elements) or len(set(elements)) != len(elements):
            fail("invalid_dimension", "Dimension names and nonempty members must be unique identifiers")
        if len(elements) > MAX_CELLS:
            fail("resource_limit", "Dimension exceeds cell limit")
        dims[name] = elements
    definitions = raw.get("module_definitions", {})
    if not isinstance(definitions, dict):
        fail("invalid_schema", "module_definitions must be an object")
    result = deepcopy(raw)
    for key in ("dimensions", "modules", "module_definitions"):
        result.pop(key, None)
    result.update(stocks=[], flows=[], variables=[], connectors=[])
    source_map, scopes, cells = {}, {}, []
    instance_count = 0
    identifier_bytes = 0
    expanded_aliases = set()

    def add_scope(body, prefix, parent=None, bindings=None, chain=()):
        nonlocal instance_count, identifier_bytes
        if not isinstance(body, dict):
            fail("invalid_schema", "Module definition must be an object", prefix)
        if len(chain) > MAX_MODULE_DEPTH:
            fail("resource_limit", "Module nesting exceeds limit", prefix)
        if parent is not None and set(body) - {"inputs", "outputs", "stocks", "flows", "variables", "modules", "description", "name", "connectors"}:
            fail("unsupported_semantics", "Unsupported module definition fields", prefix)
        if parent is not None and any(body.get(k) for k in ("dimensions", "tables", "time_settings", "module_definitions")):
            fail("unsupported_semantics", "Module-local dimensions, tables, settings and definitions are unsupported", prefix)
        if body.get("connectors"):
            fail("unsupported_semantics", "Structured connectors require explicit regeneration; nonempty connectors are unsupported", prefix)
        if not isinstance(body.get("outputs", {}), dict):
            fail("invalid_schema", "Module outputs must be an object", prefix)
        scope = {"symbols": {}, "children": {}, "parent": parent, "bindings": {} if bindings is None else bindings, "outputs": body.get("outputs", {}), "prefix": prefix}
        scopes[prefix] = scope
        declared_inputs = body.get("inputs", []) if parent is not None else []
        if not isinstance(declared_inputs, list) or any(not isinstance(x, str) or len(x) > 128 or not IDENT.fullmatch(x) for x in declared_inputs) or len(set(declared_inputs)) != len(declared_inputs):
            fail("invalid_schema", "Module inputs must be unique identifier names", prefix)
        if not isinstance(scope["bindings"], dict):
            fail("module_binding", "Input bindings must be an object", prefix)
        if set(declared_inputs) != set(scope["bindings"]):
            fail("module_binding", "Every module input requires exactly one explicit binding", prefix)
        if any(not isinstance(v, str) for v in scope["bindings"].values()):
            fail("module_binding", "Input bindings must be reference strings", prefix)
        for kind in ("stocks", "flows", "variables"):
            entries = body.get(kind, [])
            if not isinstance(entries, list):
                fail("invalid_schema", f"{kind} must be a list", prefix)
            if len(entries) > MAX_CELLS:
                fail("resource_limit", "Too many source elements", prefix)
            for n, elem in enumerate(entries):
                path = f"{prefix or '$'}.{kind}[{n}]"
                if not isinstance(elem, dict):
                    fail("invalid_schema", "Element must be an object", path)
                allowed = {"id", "name", "units", "initial_value", "equation", "position", "role", "dimensions", "initial_values", "equations", "from_stock", "to_stock"}
                if set(elem) - allowed:
                    fail("unsupported_semantics", "Unsupported structured element fields", path)
                name = elem.get("name", "")
                if not isinstance(name, str) or len(name) > 128 or not IDENT.fullmatch(name) or name in scope["symbols"] or name in declared_inputs:
                    fail("invalid_name", "Structured element names must be unique identifiers", path)
                shape = elem.get("dimensions", [])
                if not isinstance(shape, list) or any(not isinstance(d, str) or d not in dims for d in shape) or len(set(shape)) != len(shape):
                    fail("invalid_shape", "Shape requires distinct declared dimensions", path)
                count = 1
                for d in shape:
                    count *= len(dims[d])
                if count + len(cells) > MAX_CELLS:
                    fail("resource_limit", "Expanded model exceeds cell limit", path)
                if elem.get("id") is not None and not isinstance(elem["id"], str):
                    fail("invalid_schema", "Source IDs must be strings", path)
                symbol = {"kind": kind, "shape": shape, "cells": {}, "path": path, "original_id": elem.get("id")}
                if symbol["original_id"] is not None and any(s["original_id"] == symbol["original_id"] for s in scope["symbols"].values()):
                    fail("duplicate_id", "Source element IDs must be unique within a scope", path)
                scope["symbols"][name] = symbol
                if kind != "stocks" and elem.get("initial_values"):
                    fail("invalid_override", "initial_values applies only to stocks", path)
                for field in ("initial_values", "equations"):
                    if not isinstance(elem.get(field, {}), dict):
                        fail("invalid_override", f"{field} must be an object", path)
                valid_keys = set()
                for indices in product(*(dims[d] for d in shape)):
                    key = ",".join(indices)
                    valid_keys.add(key)
                    full = (prefix + "." if prefix else "") + name + ("[" + key + "]" if shape else "")
                    alias = canonical_name(full)
                    if alias in expanded_aliases:
                        fail("ambiguous_name", "Expanded names collide under scalar identifier matching", path)
                    expanded_aliases.add(alias)
                    identifier_bytes += len(full.encode("utf-8")) * 4
                    if identifier_bytes > 2_000_000:
                        fail("resource_limit", "Expanded identifier metadata budget exceeded", path)
                    out = deepcopy({k: v for k, v in elem.items() if k not in {"dimensions", "initial_values", "equations"}})
                    out.update(name=full, id="structured:" + full)
                    if key in elem.get("initial_values", {}):
                        out["initial_value"] = elem["initial_values"][key]
                    if key in elem.get("equations", {}):
                        out["equation"] = elem["equations"][key]
                    symbol["cells"][indices] = out
                    cells.append((scope, symbol, elem, out, dict(zip(shape, indices))))
                    source_map[out["id"]] = {"path": path, "indices": dict(zip(shape, indices)), "name": full, "kind": kind[:-1], "id": out["id"]}
                for field in ("initial_values", "equations"):
                    overrides = elem.get(field, {})
                    if not isinstance(overrides, dict) or set(overrides) - valid_keys:
                        fail("invalid_override", f"{field} contains invalid cell keys", path)
        instances = body.get("modules", [])
        if not isinstance(instances, list):
            fail("invalid_schema", "modules must be a list", prefix)
        for inst in instances:
            if not isinstance(inst, dict):
                fail("invalid_schema", "Module instance must be an object", prefix)
            if set(inst) - {"name", "definition", "inputs"}:
                fail("unsupported_semantics", "Module arrays and extra instance fields are unsupported", prefix)
            name, definition = inst.get("name", ""), inst.get("definition")
            if not isinstance(name, str) or len(name) > 128 or not IDENT.fullmatch(name) or name in scope["children"] or name in scope["symbols"] or name in declared_inputs:
                fail("invalid_name", "Module instance names must be unique identifiers", prefix)
            if not isinstance(definition, str) or definition not in definitions:
                fail("unknown_module", "Unknown module definition", prefix)
            if definition in chain:
                fail("recursive_module", "Recursive module definitions are unsupported", prefix)
            instance_count += 1
            if instance_count > MAX_INSTANCES:
                fail("resource_limit", "Module instance limit exceeded", prefix)
            child_prefix = (prefix + "." if prefix else "") + name
            scope["children"][name] = add_scope(definitions[definition], child_prefix, scope, inst.get("inputs", {}), chain + (definition,))
        return scope

    root = add_scope(raw, "")

    def resolve(scope, reference, context, aggregate=False, trail=()):
        if not isinstance(reference, str):
            fail("invalid_reference", "References must be strings", scope["prefix"])
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)(?:\[([^\[\]]*)\])?", reference.strip())
        if not match:
            fail("invalid_reference", "Expected a declared element reference", scope["prefix"])
        base, sub = match.groups()
        if base in scope["bindings"]:
            marker = (scope["prefix"], base)
            if marker in trail:
                fail("module_binding", "Cyclic input binding")
            if sub is not None:
                fail("unsupported_semantics", "Module inputs are scalar references; bind an explicit cell")
            return resolve(scope["parent"], scope["bindings"][base], context, aggregate, trail + (marker,))
        if "." in base:
            child_name, output = base.split(".", 1)
            child = scope["children"].get(child_name)
            if child is None or output not in child["outputs"]:
                fail("unknown_output", "Only declared module outputs may be referenced")
            target = child["outputs"][output]
            if not isinstance(target, str) or sub is not None:
                fail("unsupported_semantics", "Module outputs must name explicit scalar references")
            return resolve(child, target, {}, aggregate, trail)
        symbol = scope["symbols"].get(base)
        if symbol is None:
            fail("unknown_reference", f"Unknown reference {base}", scope["prefix"])
        shape = symbol["shape"]
        selectors = [s.strip() for s in sub.split(",")] if sub is not None else shape
        if len(selectors) != len(shape):
            fail("invalid_shape", f"{base} requires {len(shape)} subscripts")
        choices = []
        for dimension, selector in zip(shape, selectors):
            if selector == dimension:
                if aggregate:
                    choices.append(dims[dimension])
                elif dimension in context:
                    choices.append([context[dimension]])
                else:
                    fail("unbound_dimension", f"Dimension {dimension} has no current index")
            elif selector in dims[dimension]:
                choices.append([selector])
            else:
                fail("invalid_index", f"Unknown {dimension} member {selector}")
        return [symbol["cells"][idx] for idx in product(*choices)]

    reduction_budget = Budget()
    def equation(scope, expr, context):
        if not isinstance(expr, str):
            fail("invalid_equation", "Equations must be strings")
        class ValidatedSelection:
            def select(self, ref, budget):
                # Ports have already been validated as explicit scalar references.
                # Only local declared shapes can introduce reduction axes.
                symbol = scope["symbols"].get(ref.name)
                axes = symbol["shape"] if symbol else ()
                selectors = axes if ref.selectors is None else ref.selectors
                reduced = tuple(d for d, selector in zip(axes, selectors) if d == selector)
                reference = ref.name
                if ref.selectors is not None:
                    reference += "[" + ",".join(ref.selectors) + "]"
                try:
                    values = resolve(scope, reference, context, True)
                except StructuredModelError as exc:
                    if exc.code == "unknown_reference":
                        raise ReductionError(exc.code, str(exc)) from exc
                    raise
                names = tuple(v["name"] for v in values)
                budget.charge(sum(len(n.encode("utf-8")) + 5 for n in names))
                return Selection(names, reduced)
        try:
            lowered = lower_expression(expr, ValidatedSelection(), reduction_budget)
        except ReductionError as exc:
            fail(exc.code, str(exc), scope["prefix"])
        def replace(m):
            token = m.group()
            if token.startswith('"'):
                values = resolve(scope, json.loads(token), context)
                return json.dumps(values[0]["name"])
            base = token.split("[", 1)[0]
            if base in scope["symbols"] or base in scope["bindings"] or "." in base or "[" in token:
                values = resolve(scope, token, context)
                return json.dumps(values[0]["name"])
            # Unknown function calls are left for the scalar parser; unknown bare
            # names fail here, so a module cannot capture an outer symbol.
            if expr[m.end():].lstrip().startswith("(") or token.upper() in {"TIME", "DT", "TIME_STEP", "STARTTIME", "STOPTIME", "PI", "E", "TRUE", "FALSE", "AND", "OR", "NOT", "IF", "THEN", "ELSE"}:
                return token
            if re.fullmatch(r"[eE][0-9]+", token) and m.start() and expr[m.start()-1].isdigit():
                return token
            fail("unknown_reference", f"Unknown reference {token}", scope["prefix"])
        source = expr
        pieces, pos = [], 0
        for start, end, text in lowered.replacements:
            expr = source[pos:start]
            pieces.extend((TOKEN.sub(replace, expr), text))
            pos = end
        expr = source[pos:]
        pieces.append(TOKEN.sub(replace, expr))
        equation = "".join(pieces)
        if len(equation) > 100_000:
            fail("resource_limit", "Expanded expression length limit")
        try:
            reduction_budget.charge(len(equation))
        except ReductionError as exc:
            fail(exc.code, str(exc), scope["prefix"])
        return equation

    for scope in scopes.values():
        for name, symbol in scope["symbols"].items():
            original_id = symbol["original_id"]
            if original_id is not None and original_id in scope["symbols"] and original_id != name:
                fail("ambiguous_id", "Source IDs must not collide with another element name", symbol["path"])
        for name in scope["bindings"]:
            resolve(scope, name, {})
        for name, target in scope["outputs"].items():
            if not isinstance(name, str) or len(name) > 128 or not IDENT.fullmatch(name) or not isinstance(target, str):
                fail("module_binding", "Outputs require identifier ports and reference strings")
            resolve(scope, target, {})

    for scope, symbol, original, out, context in cells:
        out["equation"] = equation(scope, out.get("equation", ""), context)
        if symbol["kind"] == "flows":
            for endpoint in ("from_stock", "to_stock"):
                ref = original.get(endpoint)
                if ref is None:
                    continue
                # IDs in scalar source are accepted as aliases for declared local stocks.
                ref = next((name for name, sym in scope["symbols"].items() if sym["original_id"] == ref), ref)
                targets = resolve(scope, ref, context)
                if targets[0]["id"] not in {c["id"] for s in scope["symbols"].values() if s["kind"] == "stocks" for c in s["cells"].values()}:
                    fail("invalid_flow_endpoint", "Flow endpoints must be declared local stocks")
                out[endpoint] = targets[0]["id"]
        result[symbol["kind"]].append(out)
    return {"model": result, "source_map": source_map, "diagnostics": []}

