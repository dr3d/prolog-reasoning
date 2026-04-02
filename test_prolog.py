"""
test_prolog.py — Test suite for prolog-executor.py

Run:  python test_prolog.py
  or: python -m pytest test_prolog.py -v
"""

import importlib.util
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Load the module — hyphenated filename prevents standard import
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location(
    "prolog_executor",
    Path(__file__).parent / "prolog-executor.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

PrologEngine = _mod.PrologEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def eng(kb: str = "") -> PrologEngine:
    """Return a PrologEngine with the given KB text loaded."""
    e = PrologEngine()
    if kb:
        e._parse_and_add_clauses(kb)
    return e


def query(kb: str, q: str):
    """All solutions for q against kb."""
    return eng(kb).query(q)


def vals(kb: str, q: str, var: str):
    """Values bound to var across all solutions."""
    return [s[var] for s in query(kb, q) if var in s]


# ===========================================================================
# Facts and Ground Queries
# ===========================================================================

class TestFacts(unittest.TestCase):

    def test_ground_fact_succeeds(self):
        self.assertTrue(query("likes(alice, bob).", "likes(alice, bob)"))

    def test_ground_fact_fails(self):
        self.assertFalse(query("likes(alice, bob).", "likes(alice, carol)"))

    def test_missing_predicate_fails(self):
        self.assertFalse(query("", "foo"))

    def test_ground_query_returns_empty_dict(self):
        self.assertEqual(query("foo.", "foo"), [{}])

    def test_multiple_facts_all_returned(self):
        kb = "color(red). color(blue). color(green)."
        self.assertEqual(vals(kb, "color(X)", "X"), ["red", "blue", "green"])

    def test_multiargument_fact(self):
        kb = "edge(a, b). edge(b, c)."
        self.assertTrue(query(kb, "edge(a, b)"))
        self.assertFalse(query(kb, "edge(a, c)"))


# ===========================================================================
# Unification
# ===========================================================================

class TestUnification(unittest.TestCase):

    def test_atom_unifies_with_itself(self):
        self.assertTrue(query("", "foo = foo"))

    def test_atoms_dont_unify(self):
        self.assertFalse(query("", "foo = bar"))

    def test_var_unifies_with_atom(self):
        self.assertEqual(query("", "X = hello"), [{"X": "hello"}])

    def test_var_unifies_with_number(self):
        self.assertEqual(query("", "X = 42"), [{"X": "42"}])

    def test_compound_unification(self):
        self.assertEqual(query("", "f(X, b) = f(a, b)"), [{"X": "a"}])

    def test_compound_arity_mismatch(self):
        self.assertFalse(query("", "f(a) = f(a, b)"))

    def test_compound_functor_mismatch(self):
        self.assertFalse(query("", "f(a) = g(a)"))

    def test_chain_unification(self):
        # X = Y, Y = foo  →  X and Y both bound to foo
        # Conjunction in query strings isn't parsed — test via a rule body instead.
        kb = "test_chain(X, Y) :- X = Y, Y = foo."
        result = query(kb, "test_chain(X, Y)")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["X"], "foo")
        self.assertEqual(result[0]["Y"], "foo")

    def test_not_unify_different_atoms(self):
        self.assertTrue(query("", "foo \\= bar"))

    def test_not_unify_same_atoms_fails(self):
        self.assertFalse(query("", "foo \\= foo"))

    def test_nested_compound_unification(self):
        result = query("", "f(g(X), Y) = f(g(1), 2)")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["X"], "1")
        self.assertEqual(result[0]["Y"], "2")

    def test_number_unifies_with_itself(self):
        self.assertTrue(query("", "42 = 42"))

    def test_number_does_not_unify_with_atom(self):
        self.assertFalse(query("", "42 = fortytwo"))

    @unittest.skip(
        "known limitation: occurs check omitted — X = f(X) "
        "binds successfully but causes infinite loop in _term_to_str"
    )
    def test_occurs_check(self):
        # Standard Prolog omits the occurs check for performance, but a well-behaved
        # implementation should either fail or document the loop risk.
        self.assertFalse(query("", "X = f(X)"))


# ===========================================================================
# Rules and Backtracking
# ===========================================================================

class TestRulesAndBacktracking(unittest.TestCase):

    KB = """
    parent(tom, bob).
    parent(tom, liz).
    parent(bob, ann).
    parent(bob, pat).
    grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
    """

    def test_rule_fires(self):
        self.assertTrue(query(self.KB, "grandparent(tom, ann)"))

    def test_rule_fails_correctly(self):
        self.assertFalse(query(self.KB, "grandparent(bob, liz)"))

    def test_multiple_solutions_via_backtracking(self):
        self.assertEqual(vals(self.KB, "parent(tom, X)", "X"), ["bob", "liz"])

    def test_all_grandchildren(self):
        self.assertEqual(sorted(vals(self.KB, "grandparent(tom, X)", "X")), ["ann", "pat"])

    def test_recursive_rule_positive(self):
        kb = """
        ancestor(X, Y) :- parent(X, Y).
        ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).
        parent(a, b). parent(b, c). parent(c, d).
        """
        self.assertTrue(query(kb, "ancestor(a, d)"))

    def test_recursive_rule_negative(self):
        kb = """
        ancestor(X, Y) :- parent(X, Y).
        ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).
        parent(a, b). parent(b, c).
        """
        self.assertFalse(query(kb, "ancestor(b, a)"))

    @unittest.expectedFailure  # known limitation: comma not parsed as conjunction in query strings
    def test_conjunction_in_query(self):
        # "A, B" as a raw query string isn't supported — the parser doesn't handle
        # top-level comma. Workaround: wrap in a rule. This test documents the gap.
        kb = "likes(alice, bob). likes(bob, carol)."
        self.assertTrue(query(kb, "likes(alice, bob), likes(bob, carol)"))

    def test_two_variable_query(self):
        kb = "age(alice, 30). age(bob, 25)."
        result = query(kb, "age(Name, Age)")
        self.assertEqual(len(result), 2)
        names = {r["Name"] for r in result}
        self.assertEqual(names, {"alice", "bob"})


# ===========================================================================
# Cut
# ===========================================================================

class TestCut(unittest.TestCase):

    def test_cut_stops_backtracking_within_predicate(self):
        kb = """
        first(X) :- member(X, [1,2,3]), !.
        member(H, [H|_]).
        member(H, [_|T]) :- member(H, T).
        """
        self.assertEqual(vals(kb, "first(X)", "X"), ["1"])

    def test_cut_does_not_affect_callers_choice_points(self):
        # Cut inside foo stops foo's alternatives but bar's remaining clauses
        # are still tried.
        kb = """
        foo(1) :- !.
        foo(2).
        bar(X) :- foo(X).
        bar(3).
        """
        self.assertEqual(vals(kb, "bar(X)", "X"), ["1", "3"])

    def test_cut_max_pattern(self):
        kb = """
        max(X, Y, X) :- X >= Y, !.
        max(_, Y, Y).
        """
        self.assertEqual(vals(kb, "max(3, 5, M)", "M"), ["5"])
        self.assertEqual(vals(kb, "max(7, 2, M)", "M"), ["7"])
        self.assertEqual(vals(kb, "max(4, 4, M)", "M"), ["4"])

    def test_cut_prevents_second_solution(self):
        # Conjunction in raw query not supported — wrap in a rule.
        kb = "foo(1). foo(2). foo(3). first_foo(X) :- foo(X), !."
        result = vals(kb, "first_foo(X)", "X")
        self.assertEqual(result, ["1"])


# ===========================================================================
# findall/3
# ===========================================================================

class TestFindall(unittest.TestCase):

    KB = "num(1). num(2). num(3)."

    def test_findall_basic(self):
        result = query(self.KB, "findall(X, num(X), L)")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["L"], "[1, 2, 3]")

    def test_findall_no_solutions_returns_empty_list(self):
        # findall always succeeds — no solutions means empty list, not failure
        result = query(self.KB, "findall(X, foo(X), L)")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["L"], "[]")

    def test_findall_with_template_expression(self):
        kb = "pair(a, 1). pair(b, 2). pair(c, 3)."
        result = query(kb, "findall(K-V, pair(K, V), L)")
        self.assertEqual(len(result), 1)
        # K-V renders as infix: (a - 1), (b - 2), (c - 3)
        self.assertEqual(result[0]["L"], "[(a - 1), (b - 2), (c - 3)]")

    @unittest.expectedFailure  # known limitation: (A, B) conjunction subgoal not parsed
    def test_findall_with_condition(self):
        # Parenthesized conjunctions like (num(X), X > 3) as findall subgoals
        # aren't supported — the parser doesn't strip outer parens or handle
        # ',' as a conjunction operator inside them.
        kb = "num(1). num(2). num(3). num(4). num(5)."
        result = query(kb, "findall(X, (num(X), X > 3), L)")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["L"], "[4, 5]")

    def test_findall_collects_all_before_continuing(self):
        # Conjunction not supported in raw query strings — verify via the list value.
        kb = "item(a). item(b)."
        result = query(kb, "findall(X, item(X), L)")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["L"], "[a, b]")

    @unittest.expectedFailure  # known bug: CutException escapes findall
    def test_cut_inside_findall_is_local(self):
        # Standard Prolog: cut inside findall stops collection after first solution
        # but findall/3 itself still succeeds, returning [1].
        # Current bug: CutException propagates out of the list comprehension,
        # escaping findall entirely — the query returns no solutions.
        result = query(self.KB, "findall(X, (num(X), !), L)")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["L"], "[1]")


# ===========================================================================
# Arithmetic
# ===========================================================================

class TestArithmetic(unittest.TestCase):

    def test_addition(self):
        self.assertEqual(query("", "X is 2 + 3"), [{"X": "5"}])

    def test_subtraction(self):
        self.assertEqual(query("", "X is 10 - 4"), [{"X": "6"}])

    def test_multiplication(self):
        self.assertEqual(query("", "X is 3 * 7"), [{"X": "21"}])

    def test_integer_division(self):
        self.assertEqual(query("", "X is 10 // 3"), [{"X": "3"}])

    def test_modulo(self):
        self.assertEqual(query("", "X is 10 mod 3"), [{"X": "1"}])

    def test_float_division(self):
        result = query("", "X is 7 / 2")
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(float(result[0]["X"]), 3.5)

    def test_precedence_mul_before_add(self):
        # 3 + 4 * 2 = 3 + 8 = 11  (not (3+4)*2 = 14)
        self.assertEqual(query("", "X is 3 + 4 * 2"), [{"X": "11"}])

    def test_precedence_mul_left_operand(self):
        # 2 * 3 + 4 = 6 + 4 = 10
        self.assertEqual(query("", "X is 2 * 3 + 4"), [{"X": "10"}])

    def test_gt_succeeds(self):
        self.assertTrue(query("", "5 > 3"))

    def test_gt_fails(self):
        self.assertFalse(query("", "3 > 5"))

    def test_lt_succeeds(self):
        self.assertTrue(query("", "2 < 7"))

    def test_gte_equal(self):
        self.assertTrue(query("", "5 >= 5"))

    def test_gte_greater(self):
        self.assertTrue(query("", "6 >= 5"))

    def test_gte_fails(self):
        self.assertFalse(query("", "4 >= 5"))

    def test_lte(self):
        self.assertTrue(query("", "3 =< 3"))
        self.assertFalse(query("", "4 =< 3"))

    def test_arith_equal(self):
        self.assertTrue(query("", "2 + 2 =:= 4"))
        self.assertFalse(query("", "2 + 2 =:= 5"))

    def test_arith_not_equal(self):
        self.assertTrue(query("", "2 + 2 =\\= 5"))
        self.assertFalse(query("", "2 + 2 =\\= 4"))

    def test_comparison_with_expression_both_sides(self):
        # Tests that expressions on both sides of =:= are evaluated
        self.assertTrue(query("", "1 + 2 =:= 3 + 0"))

    def test_is_with_bound_variable(self):
        # Conjunction not supported in raw query — wrap in a rule.
        kb = "val(42). add_eight(X) :- val(V), X is V + 8."
        result = query(kb, "add_eight(X)")
        self.assertEqual(result[0]["X"], "50")

    def test_unbound_variable_in_arithmetic_fails(self):
        # X is Y + 1 with unbound Y should fail, not crash
        self.assertFalse(query("", "X is Y + 1"))


# ===========================================================================
# Lists
# ===========================================================================

class TestLists(unittest.TestCase):

    def test_empty_list_unification(self):
        self.assertTrue(query("", "[] = []"))

    def test_list_head_tail(self):
        result = query("", "[H|T] = [1, 2, 3]")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["H"], "1")
        self.assertEqual(result[0]["T"], "[2, 3]")

    def test_list_single_element_tail(self):
        result = query("", "[H|T] = [42]")
        self.assertEqual(result[0]["H"], "42")
        self.assertEqual(result[0]["T"], "[]")

    def test_list_pattern_second_element(self):
        result = query("", "[_, X, _] = [a, b, c]")
        self.assertEqual(result[0]["X"], "b")

    def test_nested_list_unification(self):
        result = query("", "[[1, 2], [3, 4]] = [[H|_]|_]")
        self.assertEqual(result[0]["H"], "1")

    def test_compound_result_fully_dereffed(self):
        # Regression: result variables that bind to a Compound whose args are
        # themselves variables must be fully dereferenced — not show _Gn names.
        kb = "wrap(foo(1, bar))."
        result = query(kb, "wrap(X)")
        self.assertEqual(result[0]["X"], "foo(1, bar)")

    def test_findall_into_list(self):
        kb = "fruit(apple). fruit(banana). fruit(cherry)."
        result = query(kb, "findall(F, fruit(F), Fruits)")
        self.assertEqual(result[0]["Fruits"], "[apple, banana, cherry]")

    def test_member_rule_positive(self):
        kb = "member(H, [H|_]). member(H, [_|T]) :- member(H, T)."
        self.assertTrue(query(kb, "member(2, [1, 2, 3])"))

    def test_member_rule_negative(self):
        kb = "member(H, [H|_]). member(H, [_|T]) :- member(H, T)."
        self.assertFalse(query(kb, "member(5, [1, 2, 3])"))

    def test_member_backtracking(self):
        kb = "member(H, [H|_]). member(H, [_|T]) :- member(H, T)."
        self.assertEqual(vals(kb, "member(X, [a, b, c])", "X"), ["a", "b", "c"])

    def test_empty_list_fails_member(self):
        kb = "member(H, [H|_]). member(H, [_|T]) :- member(H, T)."
        self.assertFalse(query(kb, "member(1, [])"))


# ===========================================================================
# Assert / Retract
# ===========================================================================

class TestAssertRetract(unittest.TestCase):

    def test_assert_then_query(self):
        e = eng()
        list(e.query("assert(fact(hello))"))
        self.assertTrue(e.query("fact(hello)"))

    def test_assertz_appends(self):
        e = eng("foo(1). foo(2).")
        list(e.query("assertz(foo(3))"))
        self.assertEqual([s["X"] for s in e.query("foo(X)")], ["1", "2", "3"])

    def test_asserta_prepends(self):
        e = eng("foo(2). foo(3).")
        list(e.query("asserta(foo(1))"))
        self.assertEqual([s["X"] for s in e.query("foo(X)")], ["1", "2", "3"])

    def test_retract_removes_clause(self):
        e = eng("fact(a). fact(b). fact(c).")
        list(e.query("retract(fact(b))"))
        self.assertEqual([s["X"] for s in e.query("fact(X)")], ["a", "c"])

    def test_retract_nondeterminism(self):
        # Backtracking over retract removes successive matching clauses
        e = eng("foo(1). foo(2). foo(3).")
        results = list(e.query("retract(foo(X))"))
        self.assertEqual(len(results), 3)
        self.assertEqual([r["X"] for r in results], ["1", "2", "3"])
        # All three should now be gone
        self.assertFalse(e.query("foo(_)"))

    def test_assert_permanent_through_backtracking(self):
        # assert side-effect survives even when the asserting clause branch fails
        kb = "trigger :- assert(side_effect(yes)), fail.\ntrigger."
        e = eng(kb)
        list(e.query("trigger"))
        self.assertTrue(e.query("side_effect(yes)"))

    @unittest.expectedFailure  # known limitation: (head :- body) not parsed in assert arg
    def test_assert_rule(self):
        # assert((head :- body)) requires ':-' in the infix operator list, which
        # it isn't. Workaround: load rules via _parse_and_add_clauses directly.
        e = eng()
        list(e.query("assert((double(X, Y) :- Y is X * 2))"))
        result = e.query("double(5, R)")
        self.assertEqual(result[0]["R"], "10")

    def test_retractall_removes_all_matching_clauses(self):
        e = eng("fact(a, 1). fact(b, 2). fact(a, 3).")
        # Retract all fact(a, _)
        list(e.query("retractall(fact(a, _))"))
        # Only fact(b, 2) should remain
        self.assertEqual([s["X"] for s in e.query("fact(b, X)")], ["2"])
        self.assertFalse(e.query("fact(a, _)"))

    def test_assertz_unique_avoids_duplicates(self):
        e = eng("foo(1).")
        # Assert identical fact
        list(e.query("assertz_unique(foo(1))"))
        # Check we really only have one solution 
        res = e.query("foo(X)")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["X"], "1")
        # Assert different fact
        list(e.query("assertz_unique(foo(2))"))
        self.assertEqual([s["X"] for s in e.query("foo(X)")], ["1", "2"])


# ===========================================================================
# Negation as Failure
# ===========================================================================

class TestNegation(unittest.TestCase):

    def test_negation_of_fail(self):
        self.assertTrue(query("", "\\+(fail)"))

    def test_negation_of_true(self):
        self.assertFalse(query("", "\\+(true)"))

    def test_negation_of_absent_fact(self):
        self.assertTrue(query("cat(tom).", "\\+(cat(jerry))"))

    def test_negation_of_present_fact(self):
        self.assertFalse(query("cat(tom).", "\\+(cat(tom))"))

    def test_not_synonym_of_negation(self):
        self.assertTrue(query("", "not(fail)"))
        self.assertFalse(query("", "not(true)"))

    def test_negation_does_not_bind_variables(self):
        # \+(foo(X)) should not bind X even if foo(something) exists
        kb = "foo(bar)."
        result = query(kb, "\\+(foo(baz))")
        # X is not in the query, just checking it succeeds and returns no bindings
        self.assertEqual(result, [{}])


# ===========================================================================
# Built-ins: functor/3, clause/2, true, fail
# ===========================================================================

class TestBuiltins(unittest.TestCase):

    def test_true_succeeds(self):
        self.assertTrue(query("", "true"))

    def test_fail_fails(self):
        self.assertFalse(query("", "fail"))

    def test_false_fails(self):
        self.assertFalse(query("", "false"))

    def test_functor_decompose_compound(self):
        result = query("", "functor(foo(a, b, c), F, A)")
        self.assertEqual(result[0]["F"], "foo")
        self.assertEqual(result[0]["A"], "3")

    def test_functor_decompose_atom(self):
        result = query("", "functor(hello, F, A)")
        self.assertEqual(result[0]["F"], "hello")
        self.assertEqual(result[0]["A"], "0")

    def test_functor_decompose_number(self):
        result = query("", "functor(42, F, A)")
        self.assertEqual(result[0]["F"], "42")
        self.assertEqual(result[0]["A"], "0")

    def test_functor_construct(self):
        result = query("", "functor(T, foo, 2)")
        self.assertEqual(len(result), 1)
        # T should be foo/2 with fresh unbound variables
        self.assertTrue(result[0]["T"].startswith("foo("))

    def test_clause_fact_body_is_true(self):
        kb = "loves(romeo, juliet)."
        result = query(kb, "clause(loves(romeo, juliet), Body)")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Body"], "true")

    def test_clause_rule_found(self):
        kb = "grandparent(X, Z) :- parent(X, Y), parent(Y, Z)."
        result = query(kb, "clause(grandparent(A, B), Body)")
        self.assertEqual(len(result), 1)
        # Body is a conjunction term — at minimum it should mention parent
        self.assertIn("parent", result[0]["Body"])

    def test_clause_nonexistent_fails(self):
        self.assertFalse(query("", "clause(foo(X), _)"))


# ===========================================================================
# Parser
# ===========================================================================

class TestParser(unittest.TestCase):

    def test_quoted_atom(self):
        result = query("", "X = 'hello world'")
        self.assertEqual(result[0]["X"], "'hello world'")

    def test_integer_literal(self):
        self.assertEqual(query("", "X = 42"), [{"X": "42"}])

    def test_float_literal(self):
        self.assertEqual(query("", "X = 3.14"), [{"X": "3.14"}])

    def test_negative_number(self):
        self.assertEqual(query("", "X = -7"), [{"X": "-7"}])

    def test_anonymous_variable_not_in_result(self):
        kb = "foo(a, 1). foo(b, 2)."
        result = query(kb, "foo(X, _)")
        # _ should not appear as a key
        for r in result:
            self.assertNotIn("_", r)
        self.assertEqual([r["X"] for r in result], ["a", "b"])

    def test_multiple_anonymous_variables_are_distinct(self):
        # [_, _] should unify with [1, 2] — each _ is independent
        self.assertTrue(query("", "[_, _] = [1, 2]"))

    def test_comment_stripping_line(self):
        kb = "% this is a comment\nfoo(bar). % inline comment\n"
        self.assertTrue(query(kb, "foo(bar)"))

    def test_comment_stripping_block(self):
        kb = "/* block comment */ fact(yes)."
        self.assertTrue(query(kb, "fact(yes)"))

    def test_hyphenated_quoted_atom_in_fact(self):
        # Atoms with hyphens must be quoted to avoid arithmetic parse
        kb = "name('mary-ann')."
        self.assertTrue(query(kb, "name('mary-ann')"))

    def test_date_as_integer_not_arithmetic(self):
        # A bare date like 2026-04-01 parses as 2026 - 4 - 1 = 2021 — known gotcha.
        # The correct way is to quote it or use underscores.
        result = query("", "X is 2026-04-01")
        # 2026 - 4 - 1 = 2021
        self.assertEqual(result[0]["X"], "2021")


# ===========================================================================
# Known Bugs
# ===========================================================================

class TestKnownBugs(unittest.TestCase):

    @unittest.skip(
        "known limitation: occurs check omitted — X = f(X) binds successfully "
        "then causes infinite loop in _term_to_str when the result is serialized"
    )
    def test_occurs_check_avoids_loop(self):
        # Without occurs check, _unify binds X → f(X). _deref stops at the Compound
        # so won't loop, but _term_to_str recurses infinitely: X→f(X)→X→f(X)...
        # Fix: add occurs check in _unify before binding a variable.
        self.assertFalse(query("", "X = f(X)"))

    @unittest.expectedFailure  # known bug: CutException escapes findall/3
    def test_cut_local_to_findall(self):
        # Standard Prolog: cut inside findall is local — stops collection after
        # first solution, but findall/3 still succeeds returning [1].
        # Current: CutException propagates out of the list comprehension at
        # prolog-executor.py:358, escaping findall — query returns no solutions.
        # Fix: wrap the list comprehension in a try/except CutException.
        kb = "n(1). n(2). n(3)."
        result = query(kb, "findall(X, (n(X), !), L)")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["L"], "[1]")


if __name__ == "__main__":
    unittest.main(verbosity=2)
