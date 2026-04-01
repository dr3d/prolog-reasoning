"""
prolog-executor.py — Pure-Python Prolog inference engine (no external dependencies).

Usage:
    python3 prolog-executor.py "<prolog_query>"

Output is always JSON on stdout.
"""

import json
import os
import sys
import re
from typing import List, Dict, Optional

DATABASE = os.path.join(os.path.dirname(__file__), "knowledge-base.pl")
MAX_DEPTH = 500


# ============================================================================
# TERM TYPES
# ============================================================================

class Term:
    pass


class Atom(Term):
    def __init__(self, name: str):
        self.name = name
    def __eq__(self, other):
        return isinstance(other, Atom) and self.name == other.name
    def __hash__(self):
        return hash(('atom', self.name))
    def __repr__(self):
        return f"Atom({self.name!r})"


class Variable(Term):
    def __init__(self, name: str):
        self.name = name
    def __eq__(self, other):
        return isinstance(other, Variable) and self.name == other.name
    def __hash__(self):
        return hash(('var', self.name))
    def __repr__(self):
        return f"Var({self.name})"


class Number(Term):
    def __init__(self, value):
        self.value = value
    def __eq__(self, other):
        return isinstance(other, Number) and self.value == other.value
    def __hash__(self):
        return hash(('num', self.value))
    def __repr__(self):
        return f"Num({self.value})"


class Compound(Term):
    def __init__(self, functor: str, args: List[Term]):
        self.functor = functor
        self.args = args
    def __eq__(self, other):
        return (isinstance(other, Compound) and self.functor == other.functor
                and self.args == other.args)
    def __hash__(self):
        return hash(('compound', self.functor, tuple(self.args)))
    def __repr__(self):
        return f"{self.functor}({', '.join(map(repr, self.args))})"


class Clause:
    def __init__(self, head: Term, body: Optional[List[Term]] = None):
        self.head = head
        self.body = body or []


class CutException(Exception):
    pass


# ============================================================================
# LIST HELPERS
# ============================================================================

def make_list(items: list) -> Term:
    """Build a Prolog list term from a Python list of Terms."""
    result: Term = Atom('[]')
    for item in reversed(items):
        result = Compound('.', [item, result])
    return result


def term_to_list(term: Term) -> Optional[list]:
    """If term is a proper Prolog list, return Python list of Terms. Else None."""
    result = []
    while isinstance(term, Compound) and term.functor == '.' and len(term.args) == 2:
        result.append(term.args[0])
        term = term.args[1]
    if isinstance(term, Atom) and term.name == '[]':
        return result
    return None


# ============================================================================
# ENGINE
# ============================================================================

class PrologEngine:
    def __init__(self):
        self.clauses: List[Clause] = []
        self.var_counter = 0

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_file(self, filename: str):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Knowledge base not found: {filename}")
        with open(filename, 'r') as f:
            content = f.read()
        self._parse_and_add_clauses(content)

    def _parse_and_add_clauses(self, text: str):
        # Strip comments
        text = re.sub(r'%.*?$', '', text, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        # Split on '.' at end of clause (followed by whitespace or EOF)
        for clause_text in re.split(r'\.\s', text + ' '):
            clause_text = clause_text.strip()
            if not clause_text:
                continue
            if ':-' in clause_text:
                head_str, body_str = clause_text.split(':-', 1)
                head = self._parse_term(head_str.strip())
                body_terms = [self._parse_term(t.strip())
                              for t in _split_top(body_str, ',')]
                body_terms = [t for t in body_terms if t is not None]
                if head is not None:
                    self.clauses.append(Clause(head, body_terms))
            else:
                head = self._parse_term(clause_text.strip())
                if head is not None:
                    self.clauses.append(Clause(head))

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    def _parse_term(self, s: str) -> Optional[Term]:
        s = s.strip()
        if not s:
            return None

        # Quoted atom: 'foo-bar'
        if s.startswith("'") and s.endswith("'") and len(s) >= 2:
            return Atom(s[1:-1])

        # Special atoms
        if s == '!':
            return Atom('!')
        if s == '[]':
            return Atom('[]')

        # List: [...]
        if s.startswith('[') and s.endswith(']'):
            inner = s[1:-1].strip()
            if not inner:
                return Atom('[]')
            parts = _split_top(inner, '|')
            if len(parts) == 2:
                heads = [self._parse_term(t.strip())
                         for t in _split_top(parts[0], ',')]
                tail = self._parse_term(parts[1].strip())
                result: Term = tail if tail is not None else Atom('[]')
                for h in reversed(heads):
                    if h is not None:
                        result = Compound('.', [h, result])
                return result
            items = [self._parse_term(t.strip()) for t in _split_top(inner, ',')]
            return make_list([i for i in items if i is not None])

        # Number
        if re.match(r'^-?\d+(\.\d+)?$', s):
            return Number(float(s) if '.' in s else int(s))

        # Infix operators — MUST come before Variable check so "X \= Y" isn't
        # swallowed whole as a variable name. Check longest operators first.
        # Low-precedence operators first so they become the outermost split.
        for op in ('=:=', '=\\=', '\\=', '>=', '=<', 'is', '=', '>', '<',
                   '+', '-', '*', '//', '/'):
            idx = _find_infix(s, op)
            if idx >= 0:
                left = self._parse_term(s[:idx].strip())
                right = self._parse_term(s[idx + len(op):].strip())
                if left is not None and right is not None:
                    return Compound(op, [left, right])

        # Prefix \+
        if s.startswith('\\+'):
            inner = self._parse_term(s[2:].strip())
            if inner is not None:
                return Compound('\\+', [inner])

        # Variable (uppercase or _) — after infix so "X \= Y" is caught above
        if s[0].isupper() or s[0] == '_':
            return Variable(s)

        # Compound functor(args)
        m = re.match(r'^([a-z_][a-zA-Z0-9_]*)\((.*)\)$', s, re.DOTALL)
        if m:
            functor = m.group(1)
            args = [self._parse_term(a.strip())
                    for a in _split_top(m.group(2), ',')]
            args = [a for a in args if a is not None]
            return Compound(functor, args)

        # Atom (including hyphenated atoms like mary-ann — stored as-is)
        return Atom(s)

    # ------------------------------------------------------------------
    # Query entrypoint
    # ------------------------------------------------------------------

    def query(self, query_str: str) -> List[Dict[str, str]]:
        query_str = query_str.strip().rstrip('.')
        goal = self._parse_term(query_str)
        if goal is None:
            return []

        # Collect user-visible variables from the query
        query_vars = _collect_vars(goal)

        solutions = []
        try:
            for bindings in self._solve(goal, {}, 0):
                if query_vars:
                    row = {}
                    for v in query_vars:
                        val = self._deref(Variable(v), bindings)
                        row[v] = self._term_to_str(val)
                    if row not in solutions:
                        solutions.append(row)
                else:
                    # Ground query — just record success once
                    if {} not in solutions:
                        solutions.append({})
        except CutException:
            pass
        except RecursionError:
            raise RuntimeError("Recursion depth exceeded")

        return solutions

    # ------------------------------------------------------------------
    # Solver
    # ------------------------------------------------------------------

    def _solve(self, goal: Term, bindings: Dict, depth: int):
        if depth > MAX_DEPTH:
            raise RuntimeError("Depth limit exceeded")

        goal = self._deref(goal, bindings)

        # --- Atom goals ---
        if isinstance(goal, Atom):
            name = goal.name
            if name == '!':
                yield bindings
                raise CutException()
            elif name in ('true',):
                yield bindings
            elif name in ('fail', 'false'):
                return
            elif name == 'nl':
                print()
                yield bindings
            else:
                for clause in self.clauses:
                    rc = self._rename_variables(clause)
                    if not (isinstance(rc.head, Atom) and rc.head.name == name):
                        continue
                    u = self._unify(goal, rc.head, bindings)
                    if u is None:
                        continue
                    if not rc.body:
                        yield u
                    else:
                        try:
                            yield from self._solve_goals(rc.body, u, depth + 1)
                        except CutException:
                            return
            return

        # --- Compound goals ---
        if isinstance(goal, Compound):
            f, args, n = goal.functor, goal.args, len(goal.args)

            # --- Built-ins ---

            if f == '=' and n == 2:
                u = self._unify(args[0], args[1], bindings)
                if u is not None:
                    yield u
                return

            if f == '\\=' and n == 2:
                u = self._unify(self._deref(args[0], bindings),
                                self._deref(args[1], bindings), bindings)
                if u is None:
                    yield bindings
                return

            if f == '\\+' and n == 1:
                succeeded = any(True for _ in self._solve(args[0], bindings, depth + 1))
                if not succeeded:
                    yield bindings
                return

            if f == 'not' and n == 1:
                succeeded = any(True for _ in self._solve(args[0], bindings, depth + 1))
                if not succeeded:
                    yield bindings
                return

            if f == 'is' and n == 2:
                try:
                    val = self._eval_arith(args[1], bindings)
                    u = self._unify(args[0], Number(val), bindings)
                    if u is not None:
                        yield u
                except Exception:
                    pass
                return

            if f in ('>', '<', '>=', '=<', '=:=', '=\\=') and n == 2:
                try:
                    lv = self._eval_arith(args[0], bindings)
                    rv = self._eval_arith(args[1], bindings)
                    ok = ((f == '>'   and lv > rv)  or
                          (f == '<'   and lv < rv)  or
                          (f == '>='  and lv >= rv) or
                          (f == '=<'  and lv <= rv) or
                          (f == '=:=' and lv == rv) or
                          (f == '=\\=' and lv != rv))
                    if ok:
                        yield bindings
                except Exception:
                    pass
                return

            if f == 'findall' and n == 3:
                template, subgoal, result_var = args
                collected = [self._apply_bindings(template, b)
                             for b in self._solve(subgoal, bindings, depth + 1)]
                u = self._unify(result_var, make_list(collected), bindings)
                if u is not None:
                    yield u
                return

            if f == 'write' and n == 1:
                print(self._term_to_str(self._deref(args[0], bindings)), end='')
                yield bindings
                return

            if f == 'nl' and n == 0:
                print()
                yield bindings
                return

            if f == 'assert' and n == 1:
                clause_term = self._deref(args[0], bindings)
                clause = self._term_to_clause(clause_term)
                if clause is not None:
                    self.clauses.append(clause)
                    yield bindings
                return

            if f == 'retract' and n == 1:
                pattern = self._deref(args[0], bindings)
                i = 0
                while i < len(self.clauses):
                    clause_term = self._clause_to_term(self.clauses[i])
                    u = self._unify(pattern, clause_term, bindings)
                    if u is not None:
                        self.clauses.pop(i)
                        yield u
                        # i is NOT incremented here: after the pop, what was at i+1
                        # has shifted into position i, so the next iteration naturally
                        # checks the right clause on backtrack.
                    else:
                        i += 1
                return

            if f == 'functor' and n == 3:
                term_arg = self._deref(args[0], bindings)
                if isinstance(term_arg, Variable):
                    # Construct mode: functor(Term, Name, Arity)
                    name_d = self._deref(args[1], bindings)
                    arity_d = self._deref(args[2], bindings)
                    if isinstance(name_d, Atom) and isinstance(arity_d, Number):
                        a = int(arity_d.value)
                        if a == 0:
                            constructed = name_d
                        else:
                            fresh = []
                            for _ in range(a):
                                self.var_counter += 1
                                fresh.append(Variable(f'_G{self.var_counter}'))
                            constructed = Compound(name_d.name, fresh)
                        u = self._unify(term_arg, constructed, bindings)
                        if u is not None:
                            yield u
                elif isinstance(term_arg, Atom):
                    u = self._unify(args[1], Atom(term_arg.name), bindings)
                    if u is not None:
                        u = self._unify(args[2], Number(0), u)
                        if u is not None:
                            yield u
                elif isinstance(term_arg, Number):
                    u = self._unify(args[1], term_arg, bindings)
                    if u is not None:
                        u = self._unify(args[2], Number(0), u)
                        if u is not None:
                            yield u
                elif isinstance(term_arg, Compound):
                    u = self._unify(args[1], Atom(term_arg.functor), bindings)
                    if u is not None:
                        u = self._unify(args[2], Number(len(term_arg.args)), u)
                        if u is not None:
                            yield u
                return

            if f == 'clause' and n == 2:
                head_pat = self._deref(args[0], bindings)
                for clause in self.clauses:
                    rc = self._rename_variables(clause)
                    u = self._unify(head_pat, rc.head, bindings)
                    if u is None:
                        continue
                    if not rc.body:
                        body_term = Atom('true')
                    elif len(rc.body) == 1:
                        body_term = rc.body[0]
                    else:
                        body_term = rc.body[-1]
                        for bt in reversed(rc.body[:-1]):
                            body_term = Compound(',', [bt, body_term])
                    u2 = self._unify(args[1], body_term, u)
                    if u2 is not None:
                        yield u2
                return

            if f == 'assertz' and n == 1:
                clause_term = self._deref(args[0], bindings)
                clause = self._term_to_clause(clause_term)
                if clause is not None:
                    self.clauses.append(clause)
                    yield bindings
                return

            if f == 'asserta' and n == 1:
                clause_term = self._deref(args[0], bindings)
                clause = self._term_to_clause(clause_term)
                if clause is not None:
                    self.clauses.insert(0, clause)
                    yield bindings
                return

            # --- User-defined clauses ---
            for clause in self.clauses:
                rc = self._rename_variables(clause)
                if not (isinstance(rc.head, Compound) and
                        rc.head.functor == f and
                        len(rc.head.args) == n):
                    continue
                u = self._unify(goal, rc.head, bindings)
                if u is None:
                    continue
                if not rc.body:
                    yield u
                else:
                    try:
                        yield from self._solve_goals(rc.body, u, depth + 1)
                    except CutException:
                        return

    def _solve_goals(self, goals: List[Term], bindings: Dict, depth: int):
        if not goals:
            yield bindings
            return
        first, rest = goals[0], goals[1:]
        first_d = self._deref(first, bindings)
        # Handle cut inline so it propagates correctly
        if isinstance(first_d, Atom) and first_d.name == '!':
            yield from self._solve_goals(rest, bindings, depth)
            raise CutException()
        for sol in self._solve(first, bindings, depth):
            yield from self._solve_goals(rest, sol, depth)

    # ------------------------------------------------------------------
    # Unification — non-mutating, returns new dict or None
    # ------------------------------------------------------------------

    def _unify(self, t1: Term, t2: Term, bindings: Dict) -> Optional[Dict]:
        t1 = self._deref(t1, bindings)
        t2 = self._deref(t2, bindings)

        if isinstance(t1, Variable):
            if isinstance(t2, Variable) and t1.name == t2.name:
                return bindings
            new = dict(bindings)
            new[t1.name] = t2
            return new

        if isinstance(t2, Variable):
            new = dict(bindings)
            new[t2.name] = t1
            return new

        if isinstance(t1, Atom) and isinstance(t2, Atom):
            return bindings if t1.name == t2.name else None

        if isinstance(t1, Number) and isinstance(t2, Number):
            return bindings if t1.value == t2.value else None

        if isinstance(t1, Compound) and isinstance(t2, Compound):
            if t1.functor != t2.functor or len(t1.args) != len(t2.args):
                return None
            cur = bindings
            for a1, a2 in zip(t1.args, t2.args):
                cur = self._unify(a1, a2, cur)
                if cur is None:
                    return None
            return cur

        return None

    def _deref(self, term: Term, bindings: Dict) -> Term:
        while isinstance(term, Variable) and term.name in bindings:
            term = bindings[term.name]
        return term

    # ------------------------------------------------------------------
    # Arithmetic evaluator
    # ------------------------------------------------------------------

    def _eval_arith(self, term: Term, bindings: Dict):
        term = self._deref(term, bindings)
        if isinstance(term, Number):
            return term.value
        if isinstance(term, Variable):
            raise ValueError(f"Unbound variable in arithmetic: {term.name}")
        if isinstance(term, Compound):
            f = term.functor
            if f == '+' and len(term.args) == 2:
                return self._eval_arith(term.args[0], bindings) + self._eval_arith(term.args[1], bindings)
            if f == '-' and len(term.args) == 2:
                return self._eval_arith(term.args[0], bindings) - self._eval_arith(term.args[1], bindings)
            if f == '-' and len(term.args) == 1:
                return -self._eval_arith(term.args[0], bindings)
            if f == '*' and len(term.args) == 2:
                return self._eval_arith(term.args[0], bindings) * self._eval_arith(term.args[1], bindings)
            if f == '//' and len(term.args) == 2:
                return int(self._eval_arith(term.args[0], bindings) // self._eval_arith(term.args[1], bindings))
            if f == '/' and len(term.args) == 2:
                return self._eval_arith(term.args[0], bindings) / self._eval_arith(term.args[1], bindings)
            if f == 'mod' and len(term.args) == 2:
                return self._eval_arith(term.args[0], bindings) % self._eval_arith(term.args[1], bindings)
        raise ValueError(f"Cannot evaluate: {term!r}")

    # ------------------------------------------------------------------
    # Variable renaming (fresh copy per clause invocation)
    # ------------------------------------------------------------------

    def _rename_variables(self, clause: Clause) -> Clause:
        mapping: Dict[str, str] = {}
        head = self._rename_term(clause.head, mapping)
        body = [self._rename_term(t, mapping) for t in clause.body]
        return Clause(head, body)

    def _rename_term(self, term: Term, mapping: Dict) -> Term:
        if isinstance(term, Variable):
            if term.name == '_':
                self.var_counter += 1
                return Variable(f"_G{self.var_counter}")
            if term.name not in mapping:
                self.var_counter += 1
                mapping[term.name] = f"_G{self.var_counter}"
            return Variable(mapping[term.name])
        if isinstance(term, Compound):
            return Compound(term.functor, [self._rename_term(a, mapping) for a in term.args])
        return term

    # ------------------------------------------------------------------
    # Apply bindings (instantiate a template)
    # ------------------------------------------------------------------

    def _apply_bindings(self, term: Term, bindings: Dict) -> Term:
        term = self._deref(term, bindings)
        if isinstance(term, Compound):
            return Compound(term.functor,
                            [self._apply_bindings(a, bindings) for a in term.args])
        return term

    # ------------------------------------------------------------------
    # assert/retract helpers
    # ------------------------------------------------------------------

    def _term_to_clause(self, term: Term) -> Optional[Clause]:
        if isinstance(term, Compound) and term.functor == ':-' and len(term.args) == 2:
            body = term_to_list(term.args[1])
            if body is None:
                body = [term.args[1]]
            return Clause(term.args[0], body)
        if isinstance(term, (Atom, Compound)):
            return Clause(term)
        return None

    def _clause_to_term(self, clause: Clause) -> Term:
        if not clause.body:
            return clause.head
        return Compound(':-', [clause.head, make_list(clause.body)])

    # ------------------------------------------------------------------
    # Term → string
    # ------------------------------------------------------------------

    def _term_to_str(self, term: Term) -> str:
        if isinstance(term, Atom):
            # Quote atoms that need it
            if re.match(r'^[a-z][a-zA-Z0-9_]*$', term.name) or term.name in ('[]', '!'):
                return term.name
            return f"'{term.name}'"
        if isinstance(term, Variable):
            return term.name
        if isinstance(term, Number):
            v = term.value
            if isinstance(v, float) and v == int(v):
                return str(int(v))
            return str(v)
        if isinstance(term, Compound):
            # Pretty-print lists
            lst = term_to_list(term)
            if lst is not None:
                return '[' + ', '.join(self._term_to_str(i) for i in lst) + ']'
            # Infix operators
            if term.functor in ('=', '\\=', 'is', '>', '<', '>=', '=<',
                                '=:=', '=\\=', '+', '-', '*', '//', '/') and len(term.args) == 2:
                l = self._term_to_str(term.args[0])
                r = self._term_to_str(term.args[1])
                return f"({l} {term.functor} {r})"
            args_str = ', '.join(self._term_to_str(a) for a in term.args)
            return f"{term.functor}({args_str})"
        return str(term)


# ============================================================================
# UTILITIES
# ============================================================================

def _split_top(s: str, sep: str) -> List[str]:
    """Split s by sep only at depth 0 (not inside parens/brackets/quotes)."""
    depth = 0
    in_quote = False
    current: List[str] = []
    result: List[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "'" and not in_quote:
            in_quote = True
            current.append(c)
        elif c == "'" and in_quote:
            in_quote = False
            current.append(c)
        elif in_quote:
            current.append(c)
        elif c in '([':
            depth += 1
            current.append(c)
        elif c in ')]':
            depth -= 1
            current.append(c)
        elif depth == 0 and s[i:i+len(sep)] == sep:
            result.append(''.join(current))
            current = []
            i += len(sep)
            continue
        else:
            current.append(c)
        i += 1
    if current:
        result.append(''.join(current))
    return result


def _find_infix(s: str, op: str) -> int:
    """Return index of op at top level (depth 0), or -1.
    Scans left-to-right but records the *rightmost* match, which yields
    left-associativity: splitting 'a+b+c' at the rightmost '+' gives
    left='a+b', right='c' → +(+(a,b), c).
    """
    depth = 0
    in_quote = False
    last = -1
    i = 0
    while i < len(s):
        c = s[i]
        if c == "'" and not in_quote:
            in_quote = True
        elif c == "'" and in_quote:
            in_quote = False
        elif in_quote:
            pass
        elif c in '([':
            depth += 1
        elif c in ')]':
            depth -= 1
        elif depth == 0 and not in_quote:
            if s[i:i+len(op)] == op:
                before = s[i-1] if i > 0 else ' '
                after = s[i+len(op)] if i+len(op) < len(s) else ' '
                # Word operators (is, mod) must have word boundaries
                if op.isalpha():
                    if (before.isalnum() or before == '_' or
                            after.isalnum() or after == '_'):
                        i += 1
                        continue
                else:
                    # Symbolic: skip '=' when it's part of a longer operator
                    if op == '=' and before in (':', '\\', '<', '>'):
                        i += 1
                        continue
                    if op == '=' and after in (':', '\\', '<', '>'):
                        i += 1
                        continue
                    if op == '>' and after == '=':
                        i += 1
                        continue
                    if op == '<' and after == '=':
                        i += 1
                        continue
                # Must have something on both sides
                if i > 0 and i + len(op) < len(s):
                    last = i
        i += 1
    return last


def _collect_vars(term: Term) -> List[str]:
    """Collect all user-visible variable names from a term (no _G prefix)."""
    seen: List[str] = []
    seen_set: set = set()
    def walk(t):
        if isinstance(t, Variable):
            if not t.name.startswith('_G') and t.name != '_' and t.name not in seen_set:
                seen.append(t.name)
                seen_set.add(t.name)
        elif isinstance(t, Compound):
            for a in t.args:
                walk(a)
    walk(term)
    return seen


# ============================================================================
# ENTRYPOINT
# ============================================================================

def run_query(query: str, kb_path: str = None) -> dict:
    try:
        engine = PrologEngine()
        engine.load_file(kb_path or DATABASE)
        bindings = engine.query(query)
        if bindings:
            return {"success": True, "bindings": bindings}
        return {"success": False, "error": "No solutions found"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def run_manifest(kb_path: str = None) -> str:
    """Introspect the KB and return a compact human-readable manifest."""
    path = kb_path or DATABASE
    engine = PrologEngine()
    try:
        engine.load_file(path)
    except FileNotFoundError:
        return "Knowledge base: empty (no file found)"

    facts = [c for c in engine.clauses if not c.body]
    rules = [c for c in engine.clauses if c.body]

    # Predicate inventory
    pred_counts: Dict[str, int] = {}
    for c in engine.clauses:
        if isinstance(c.head, Compound):
            key = f"{c.head.functor}/{len(c.head.args)}"
        elif isinstance(c.head, Atom):
            key = f"{c.head.name}/0"
        else:
            continue
        pred_counts[key] = pred_counts.get(key, 0) + 1

    # Known entities — atoms that appear as arguments in facts
    entities: set = set()
    def collect_atoms(term: Term):
        if isinstance(term, Atom) and term.name not in ('[]', '!', 'true', 'fail'):
            entities.add(term.name)
        elif isinstance(term, Compound):
            for a in term.args:
                collect_atoms(a)
    for c in facts:
        collect_atoms(c.head)

    lines = [
        "## Knowledge Base",
        f"Facts: {len(facts)}  Rules: {len(rules)}",
    ]

    if pred_counts:
        pred_list = "  ".join(sorted(pred_counts.keys()))
        lines.append(f"Predicates: {pred_list}")

    if entities:
        entity_list = ", ".join(sorted(entities))
        lines.append(f"Known entities: {entity_list}")

    lines.append("Query: python3 prolog-executor.py \"<prolog_query>\"")
    return "\n".join(lines)


def main() -> None:
    args = sys.argv[1:]

    # Extract -kb <path> from anywhere in args
    kb_path = None
    if '-kb' in args:
        idx = args.index('-kb')
        if idx + 1 < len(args):
            kb_path = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
        else:
            print(json.dumps({"success": False, "error": "-kb requires a path argument"}))
            sys.exit(1)

    if not args:
        print(json.dumps({"success": False, "error": "no query provided"}))
        sys.exit(1)

    if args[0] == "--manifest":
        print(run_manifest(kb_path))
        sys.exit(0)

    if args[0] == "--init":
        domain = args[1] if len(args) > 1 else "blank"
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        src = os.path.join(templates_dir, f"knowledge-base.{domain}.pl")
        dest = kb_path or "knowledge-base.pl"
        if not os.path.exists(src):
            available = [f[len("knowledge-base."):-len(".pl")]
                         for f in os.listdir(templates_dir)
                         if f.startswith("knowledge-base.") and f.endswith(".pl")]
            print(f"Unknown domain '{domain}'. Available: {', '.join(sorted(available))}")
            sys.exit(1)
        if os.path.exists(dest):
            print(f"{dest} already exists — remove it first if you want to reinitialize.")
            sys.exit(1)
        import shutil
        shutil.copy(src, dest)
        print(f"Created {dest} from {domain} template.")
        sys.exit(0)

    query = " ".join(args)
    result = run_query(query, kb_path)
    print(json.dumps(result, default=str))
    sys.exit(0 if result.get("success") else 2)


if __name__ == "__main__":
    main()
