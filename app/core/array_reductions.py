"""Bounded typed reduction pass; scopes are supplied by structured validation."""
from dataclasses import dataclass
import json


class ReductionError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


@dataclass
class Budget:
    remaining: int = 2_000_000

    def charge(self, amount):
        if amount > self.remaining:
            raise ReductionError("resource_limit", "Shared reduction work budget exhausted")
        self.remaining -= amount


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Reference:
    name: str
    selectors: tuple | None = None


@dataclass(frozen=True)
class Selection:
    names: tuple
    reduced_axes: tuple


@dataclass(frozen=True)
class Reduction:
    op: str
    reference: Reference
    selection: Selection
    start: int
    end: int


@dataclass(frozen=True)
class Lowered:
    source: str
    equation: str
    reductions: tuple
    replacements: tuple


def ident(text):
    return isinstance(text, str) and bool(text) and len(text) <= 128 and (text[0].isascii() and (text[0].isalpha() or text[0] == "_")) and all(c.isascii() and (c.isalnum() or c == "_") for c in text)


def lex(source, budget):
    if not isinstance(source, str) or len(source) > 100_000:
        raise ReductionError("resource_limit", "Expression must be a string of at most 100000 characters")
    budget.charge(len(source))
    tokens, pos = [], 0
    while pos < len(source):
        start, c = pos, source[pos]
        if c.isspace():
            pos += 1
            continue
        if c == "{":
            depth = 1
            pos += 1
            while pos < len(source) and depth:
                if source[pos] == "{":
                    depth += 1
                    if depth > 64:
                        raise ReductionError("resource_limit", "Comment nesting limit")
                elif source[pos] == "}":
                    depth -= 1
                pos += 1
            if depth:
                raise ReductionError("syntax", "Unclosed comment")
            continue
        if c == "}":
            raise ReductionError("syntax", "Unexpected comment terminator")
        if c == '"':
            pos += 1
            while pos < len(source):
                if source[pos] == "\\":
                    if pos + 1 >= len(source) or source[pos + 1] not in ('"', "\\", "n"):
                        raise ReductionError("syntax", "Unsupported quoted identifier escape")
                    pos += 2
                elif source[pos] == '"':
                    pos += 1
                    break
                else:
                    pos += 1
            else:
                raise ReductionError("syntax", "Unclosed quoted identifier")
            text = source[start:pos]
            try:
                json.loads(text)
            except ValueError as exc:
                raise ReductionError("syntax", "Invalid quoted identifier") from exc
            tokens.append(Token("quoted", text, start, pos))
            continue
        if c.isascii() and (c.isalpha() or c == "_"):
            pos += 1
            while pos < len(source) and source[pos].isascii() and (source[pos].isalnum() or source[pos] == "_"):
                pos += 1
            tokens.append(Token("ident", source[start:pos], start, pos))
            continue
        pos += 1
        tokens.append(Token("punct", c, start, pos))
    return tokens


def reference(tokens, budget):
    """Parse only a reference, never evaluate arithmetic or source strings."""
    if len(tokens) == 1 and tokens[0].kind == "quoted":
        # Whole-reference quoting is supported as an additive spelling. A quoted
        # function-like name remains an identifier and is never scanned as code.
        decoded = json.loads(tokens[0].text)
        if any(c in decoded for c in ('{', '}', '"', '\\')):
            return None
        inner = lex(decoded, budget)
        if any(t.kind == "quoted" for t in inner):
            return None
        return reference(inner, budget)
    if not tokens or tokens[0].kind != "ident" or not ident(tokens[0].text):
        return None
    parts, pos = [tokens[0].text], 1
    while pos + 1 < len(tokens) and tokens[pos].text == "." and tokens[pos + 1].kind == "ident":
        if not ident(tokens[pos + 1].text):
            return None
        parts.append(tokens[pos + 1].text)
        pos += 2
    if pos == len(tokens):
        return Reference(".".join(parts))
    if tokens[pos].text != "[" or tokens[-1].text != "]":
        return None
    tail = tokens[pos + 1:-1]
    if not tail or len(tail) % 2 == 0:
        return None
    if any(t.kind != "ident" or not ident(t.text) for t in tail[::2]) or any(t.text != "," for t in tail[1::2]):
        return None
    return Reference(".".join(parts), tuple(t.text for t in tail[::2]))


def lower_expression(source, scope, budget=None):
    """Return retained source + scalar text + typed reduction/source spans.

    Caller must share Budget across the entire expanded model. This pass neither
    resolves ordinary scalar references nor validates scalar syntax/functions.
    """
    budget = budget if budget is not None else Budget()
    tokens = lex(source, budget)
    stack, calls = [], []
    # Balanced iterative traversal; no input-dependent Python recursion.
    for index, token in enumerate(tokens):
        if token.text in ("(", "["):
            if len(stack) >= 64:
                raise ReductionError("resource_limit", "Delimiter nesting limit")
            stack.append((index, token.text, []))
        elif token.text == "," and stack and stack[-1][1] == "(":
            stack[-1][2].append(index)
        elif token.text in (")", "]"):
            if not stack or stack[-1][1] != (")" == token.text and "(" or "["):
                raise ReductionError("syntax", "Mismatched delimiter")
            opening, kind, commas = stack.pop()
            if kind == "(" and opening and tokens[opening - 1].kind == "ident" and (opening < 2 or tokens[opening - 2].text != "."):
                calls.append((opening - 1, opening, index, commas))
    if stack:
        raise ReductionError("syntax", "Unclosed delimiter")
    replacements, nodes = [], []
    for fn, opening, closing, commas in calls:
        budget.charge(1)
        op = tokens[fn].text.upper()
        if op not in ("SUM", "MEAN", "MIN", "MAX"):
            continue
        starts, ends = [opening + 1] + [c + 1 for c in commas], commas + [closing]
        budget.charge(closing - opening)
        args = [tokens[a:b] for a, b in zip(starts, ends)]
        refs = [reference(arg, budget) for arg in args]
        if len(args) != 1 or refs[0] is None:
            if op in ("SUM", "MEAN"):
                raise ReductionError("unsupported_semantics", "Reduction requires exactly one declared reference")
            continue  # Existing scalar MIN/MAX syntax is the scalar parser's job.
        ref = refs[0]
        try:
            selection = scope.select(ref, budget)
        except ReductionError as exc:
            if op in ("MIN", "MAX") and ref.selectors is None and exc.code == "unknown_reference":
                continue  # Preserve scalar unknown-reference/function error behavior.
            raise
        if op in ("MIN", "MAX") and not selection.reduced_axes:
            continue  # A literal cell/scalar does not become a one-element array.
        names = [json.dumps(n) for n in selection.names]
        if not names:
            raise ReductionError("empty_reduction", "Empty reductions have no implicit identity")
        if op in ("SUM", "MEAN"):
            text = "(" + " + ".join(names) + ")"
            if op == "MEAN":
                text = "(" + text + " / " + str(len(names)) + ")"
        else:
            # Singleton MIN/MAX is identity; Python min(number) is not.
            text = names[0] if len(names) == 1 else op + "(" + ", ".join(names) + ")"
        start, end = tokens[fn].start, tokens[closing].end
        budget.charge(len(replacements))
        if any(start < b and a < end for a, b, _ in replacements):
            raise ReductionError("unsupported_semantics", "Nested reduction expressions are unsupported")
        budget.charge(len(text.encode("utf-8")))
        replacements.append((start, end, text))
        nodes.append(Reduction(op, ref, selection, start, end))
    pieces, pos = [], 0
    for start, end, text in sorted(replacements):
        pieces.extend((source[pos:start], text))
        pos = end
    pieces.append(source[pos:])
    equation = "".join(pieces)
    if len(equation) > 100_000:
        raise ReductionError("resource_limit", "Expanded expression length limit")
    return Lowered(source, equation, tuple(sorted(nodes, key=lambda n: n.start)), tuple(sorted(replacements)))
