# Future Extensions

Design notes and open questions for extending the prolog-reasoning skill. Captured here so the thinking isn't lost when the context window closes.

---

## 1. Forward Chaining / State Materialization

**What the engine does now:** SLD resolution — backward chaining. Facts are derived on demand when a query is issued. If you `assert(parent(tom, sue))` mid-session, the engine does *not* automatically propagate derived facts (`grandparent`, `ancestor`, etc.) until something queries for them.

**What forward chaining would add:** A `materialize` or `close` operation that saturates the DB to a fixed point — iterating rules until no new facts can be derived, then asserting them all as ground facts. The result is a fully materialized KB where every derivable fact is explicit.

**When this matters:**
- Ambient awareness: the `--manifest` output would show derived facts, not just asserted ones
- Compaction: after a conversation sweep, running `close` would make implicit knowledge explicit before summarizing
- Debugging: easier to inspect "what does the KB actually know" without running individual queries

**Implementation sketch:** A `--materialize` flag or `close/0` built-in. Iterate over all rules, run each against current facts, assert new conclusions, repeat until fixed point. Maybe 50–80 lines. Main risk: rules with variables that generate infinite solutions (e.g., arithmetic rules) — would need a guard to skip non-ground conclusions.

**Complexity:** Low-to-moderate. Self-contained addition to the existing engine.

---

## 2. Constraint Propagation / CLP(FD)

**What the engine does now:** Variables are either bound (to a ground term) or unbound. There is no concept of a variable being "partially known" — e.g., known to be an integer between 3 and 7, with further constraints narrowing the domain.

**What CLP(FD) would add:** Constrained logic variables with attached domains. Constraints like `X in 1..10, X #> 5` would propagate immediately to `X in 6..10` without enumerating. Only when the problem is fully constrained (or when `label/1` is called) does the engine commit to specific values.

**The two key concepts the user named:**
- *Propagation of known states*: when a new constraint is posted, immediately reduce all affected domains (arc consistency / AC-3)
- *Propagation of freedom*: track what values remain *possible* for each variable — the complement of what's been ruled out

**When this matters:**
- Scheduling: "scott's meeting is Tuesday between 2–5pm, alice is unavailable 3–4pm" → propagates to a narrowed window without enumeration
- Resource allocation: assign tasks to people given capacity constraints
- Logic puzzles: Sudoku, N-queens, Einstein's riddle — the classic CLP(FD) use cases
- Partially-determined facts: storing "X is probably in range Y" as a first-class KB entry rather than a prose note

**Implementation sketch:**
1. New term type `CVar` with a domain (set of integers, or interval)
2. Constraint store as a separate dict in the engine (variable → active constraints)
3. Built-in predicates: `#=/2`, `#>/2`, `#</2`, `#>=/2`, `#=</2`, `in/2`, `ins/2`
4. Propagation: on each constraint post, run arc consistency over affected variables
5. `label/1`: enumerate remaining domain values when propagation alone doesn't fully determine

**Complexity:** Significant — roughly 300–400 lines of pure Python. No external deps required. This is essentially a CLP(FD) subset. The hard parts are arc consistency (AC-3 or similar) and the interaction between the constraint store and standard unification.

**Prior art to study:** SWI-Prolog's `library(clpfd)` is the reference implementation. ECLiPSe Prolog has good documentation of the underlying propagation algorithms.

---

## 3. Conflict Detection / Retraction

**What the engine does now:** The SKILL.md instructs the agent to manually edit `knowledge-base.pl` when correcting a fact. Two conflicting ground clauses (`lives_in(scott, austin)` and `lives_in(scott, portland)`) both succeed — Prolog doesn't flag contradictions, it just backtracks between them.

**What conflict detection would add:** A `--retract-matching` flag or `resolve/1` built-in that, given a new fact, finds and removes any existing clauses with the same functor/arity that contradict it before asserting the new one.

**Preferred interface — `assertz_replace/2`:** Takes a pattern and a replacement in one call:
```prolog
assertz_replace(lives_in(scott, _), lives_in(scott, portland)).
```
Retracts all clauses unifying with the pattern, then asserts the new fact. More ergonomic than a separate `retractall` + `assert` sequence for agents. Currently the two-step `retractall` + `--assert` workaround works, but a single built-in would be cleaner.

**When this matters:**
- Corrections: user says "actually I moved to Portland" — engine should retract the Austin fact, not append alongside it
- Compaction: when sweeping a conversation, new facts might update old ones — automated conflict resolution prevents "truth pollution"

**Implementation sketch:** Before `assert(F)`, query for all clauses matching `functor/arity`, compare, retract conflicts. Could be a wrapper script or a built-in. Low complexity. Now even more tractable — `functor/3` and `clause/2` are implemented, so the detection logic can be written in pure Prolog rather than Python.

---

## 4. KB Integrity Rules / `--check` Pass

**The idea:** User-defined integrity constraints written in Prolog itself, run as a validation pass before or after writes.

```prolog
% Add to knowledge-base.pl:
integrity_violation(self_parent) :- parent(X, X).
integrity_violation(conflicting_location) :- lives_in(X, A), lives_in(X, B), A \= B.
```

```bash
python3 prolog-executor.py --check
# {"violations": [{"rule": "conflicting_location", "details": "..."}]}
```

**Why this is Prolog-native:** Constraints are just rules. No new engine features needed — `--check` just queries all `integrity_violation/1` clauses and reports matches. The KB self-documents its own invariants.

**When this matters:**
- Catch contradictions the agent introduced across sessions
- Enforce domain rules (a person can't have two birth years, an asset can't be both complete and missing)
- Run as a post-write sanity check in the manifest generation script

**Complexity:** Very low. ~10 lines in the executor. The hard part is writing good constraint rules, which is the user/agent's job.

---

## 5. Rule Safety / Loop Detection

**The risk:** An LLM writing rules into the KB might accidentally create a mutually recursive cycle that only terminates because of the depth limit (500). The error is cryptic ("Depth limit exceeded") and doesn't tell you which rule caused it.

**What would help:**
- Static analysis on load: detect obvious cycles (A derives B, B derives A with no base case)
- Better error reporting: when depth limit is hit, report the call stack so the problematic rule is identifiable
- Extend `--validate` (already ships syntax checks) with a static cycle check — DFS on the predicate dependency graph, report suspicious rules without executing queries

**Complexity:** Cycle detection is a graph problem (DFS on the predicate dependency graph). Static analysis only — no runtime changes needed. Moderate complexity.

---

## 6. Proof Traces / Explainability

**What the engine does now:** Returns `{"success": true, "bindings": [...]}` and discards the proof. The agent knows *what* is true but not *why*.

**What explainability would add:** A `--explain` flag that returns the first proof as a flat list of steps alongside the normal result:

```json
{
  "success": true,
  "bindings": [{}],
  "proof": [
    "can_enter(vault) ← rule: gate(_, vault, Item), has(player, Item)",
    "  gate(library, vault, lantern) — fact",
    "  has(player, lantern) — fact"
  ]
}
```

No nested tree, no all-branches enumeration — just the derivation chain for the first solution. The agent can then relay this as reasoning, not just recall.

**When this matters:**
- Answering "why?" questions: "why can the player enter the vault?" → the proof shows the exact gate item and inventory fact that satisfied it
- Debugging rules that succeed unexpectedly — the trace shows which clause fired
- Trust: the agent isn't guessing, it's reporting a verifiable derivation

**Implementation sketch:** Thread a proof accumulator (list of strings) through `_solve` and `_solve_goals`. On each clause match, append a line for the rule/fact. On each built-in, append the operation. Return the accumulated proof for the first solution when `--explain` is passed. The hard part is keeping the accumulator clean on backtrack — need to snapshot and restore rather than mutate.

**Complexity:** Moderate. Touches the core recursion but is self-contained. Doesn't change normal query behavior.

---

## 7. Entity Aliases

**What the engine does now:** `john` and `john_smith` and `John` are three distinct atoms. If the agent writes facts under two spellings, queries for one won't find the other.

**The right approach:** Express aliases as Prolog facts, not a Python-side lookup table. A Python alias table is a second source of truth that can diverge from the KB. Keeping aliases in the KB makes them queryable, inspectable, and agent-writable:

```prolog
alias(john, john_smith).
alias('John Smith', john_smith).
canonical(X, C) :- alias(X, C).
canonical(X, X) :- \+ alias(X, _).
```

Then any rule that looks up an entity can call `canonical/2` first. The agent writes `alias/2` facts exactly like any other KB fact — no special tooling needed.

**Complexity:** Zero engine changes. Pure KB convention. Worth documenting in SKILL.md schema section.

---

## 8. Query Timeout / Search Budget

**The problem:** Beyond `MAX_DEPTH = 500`, there is no per-query cost control. A query that generates an enormous number of intermediate solutions (e.g. a badly written `findall` over a large KB) blocks indefinitely. In an agent loop this means a hung subprocess with no signal to the caller.

**What would help:**
- A `--timeout N` CLI flag that kills the query after N milliseconds and returns `{"success": false, "error": "timeout"}`
- Optionally a `--max-solutions N` flag to cap how many solutions are collected before returning

**Implementation sketch:** Wrap `_solve` in a thread with a deadline, or use `signal.alarm` on Unix. On Windows, thread-based timeout is the only portable option. The CLI already catches exceptions and returns JSON errors — the caller interface doesn't change.

**Complexity:** Low-to-moderate (portability). Worth doing before any public release.

---

## 9. Domain Suitability Documentation

**The issue:** The tool gets misapplied when users try to use it for inherently fuzzy knowledge — opinions, uncertain statements, probabilistic beliefs, open-ended concepts. It fails silently in those cases: facts get stored, queries return wrong answers or no answers, and the user doesn't understand why.

**What would help:** A clear "this tool is for X, not Y" section in SKILL.md and README, with concrete examples:

| Domain | Suitable? | Reason |
|--------|-----------|--------|
| Family trees, roles, permissions | ✅ | Closed, stable, deterministic |
| Game state, inventory, quests | ✅ | Closed world, explicit rules |
| Legal / policy rules (structured) | ✅ | Rule-based, verifiable |
| Medical facts, drug interactions | ✅ | Closed schema, ground truth |
| Opinions, preferences | ⚠️ | Store as facts only if treated as ground truth (`prefers(scott, dark_mode)`) |
| Uncertain / hedged statements | ❌ | "probably", "might", "I think" — do not extract |
| General conversation, creative ideation | ❌ | Wrong tool entirely |

The "When to Write / Do Not Extract" section in SKILL.md already touches this — it just needs to be sharper.

**Complexity:** Zero engine work. Documentation only.

---

## 10. `setof/3` and `bagof/3`

**What the engine does now:** Only `findall/3` is implemented. `findall` collects all solutions including duplicates — `findall(X, role(X, admin), L)` on a KB with two identical `role(alice, admin)` facts returns `[alice, alice]`.

**What `setof/3` and `bagof/3` would add:**
- `setof/3` — like `findall` but sorts and deduplicates results. Fails (rather than returning `[]`) if no solutions. Standard Prolog.
- `bagof/3` — like `setof` but preserves duplicates, groups by unbound variables. Useful for collecting facts grouped by a shared argument.

**When this matters:**
- Any query where duplicates would mislead: `findall(X, parent(_, X), Kids)` on a KB where a child appears under two parents returns duplicates
- Sorted output for display: `setof(X, lives_in(X, london), People)` returns alphabetical list
- `bagof` is rarely needed but `setof` comes up often in clean fact retrieval

**Implementation sketch:** `setof` is ~20 lines — run `findall` internally, then apply Python `sorted(set(...))` on the serialized results before building the list term. The tricky part is `bagof`'s grouping semantics (`^` operator for existential quantification) — can defer that.

**Complexity:** Low for `setof`. Medium for full `bagof` with `^` operator.

---

## 11. Conjunction in `findall` Subgoal

**What the engine does now:** `findall(X, parent(scott, X), Kids)` works. But `findall(X, (parent(scott, X), female(X)), Daughters)` fails — the parser doesn't handle top-level comma inside the subgoal argument.

**Root cause:** The `_split_top` parser splits on commas to separate clause body goals. Inside a `findall` the second argument is itself a conjunction, but the parser treats it as two separate `findall` arguments rather than one conjunctive goal.

**Workaround:** Wrap the conjunction in a helper rule:
```prolog
daughter(P, X) :- parent(P, X), female(X).
% then: findall(X, daughter(scott, X), Daughters)
```

**Fix:** In `_parse_term`, detect `findall(`, extract its three arguments respecting nested brackets, then parse the subgoal argument through `_split_top` as a conjunction. SESSION.md Session 4 documents this as a known expected failure.

**Complexity:** Low-to-moderate. Targeted parser change, shouldn't affect other parsing paths.

---

## 12. Two-Tier KB Namespace Isolation

**What the engine does now:** When a project KB is given with `-kb`, both the project KB and the global KB are loaded into the same engine. All predicates share one flat namespace — `parent/2` in the global KB and `parent/2` in a project KB unify freely.

**The risk:** A project KB that redefines a predicate (`lives_in/2` for fictional characters in a game) will mix with real-world facts from the global KB. Queries can return results from the wrong KB without any indication.

**What isolation would add:** A way to keep project facts separate from global facts when loading both, preventing cross-contamination while still allowing the agent to query either tier explicitly.

**Approaches (in ascending complexity):**
1. **Load order as override** — load global first, project second. Project clauses shadow global ones for the same predicate. Simple, already partially true.
2. **Namespace prefixing convention** — document in SKILL.md that project KBs should use a prefix (`game_lives_in` vs `lives_in`). Zero engine changes, relies on agent discipline.
3. **Separate engines with explicit merge** — run two `PrologEngine` instances and combine clause lists with project-first ordering. Cleanest isolation. Requires refactoring `run_query` to accept two KB paths explicitly.

**When this matters:** Mostly when the project domain overlaps with global personal facts — a fiction-writing KB using `person/1`, `lives_in/2`, `parent/2` for characters will pollute queries against the real KB.

**Complexity:** Low (convention) to moderate (separate engines).

---

## Priority / Sequencing

If these were to be implemented in order of value vs. effort:

1. **Conflict detection / `assertz_replace`** — low effort, high day-to-day value, prevents a real failure mode
2. **`findall` conjunction fix** — low effort, removes a known papercut that forces helper rules
3. **`setof/3`** — low effort, fixes duplicate results from findall
4. **KB integrity rules / --check** — very low effort, pure Prolog, catches contradictions across sessions
5. **Entity aliases** — zero engine work, pure KB convention, document in SKILL.md
6. **Proof traces** — moderate effort, turns the engine from a lookup tool into an explainable reasoner
7. **Query timeout / search budget** — low-moderate effort, needed before any public release
8. **Forward chaining** — moderate effort, makes the KB more legible and the manifest more useful
9. **Rule safety / loop detection** — moderate effort, defensive value
10. **Two-tier KB namespace isolation** — low (convention) to moderate (separate engines), worth addressing before the project KB sees heavy use
11. **CLP(FD) constraints** — high effort, qualitatively expands what the skill can reason about, but only needed for scheduling/resource/puzzle use cases
