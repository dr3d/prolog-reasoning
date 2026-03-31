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

**When this matters:**
- Corrections: user says "actually I moved to Portland" — engine should retract the Austin fact, not append alongside it
- Compaction: when sweeping a conversation, new facts might update old ones — automated conflict resolution prevents "truth pollution"

**Implementation sketch:** Before `assert(F)`, query for all clauses matching `functor/arity`, compare, retract conflicts. Could be a wrapper script or a built-in. Low complexity. Now even more tractable — `functor/3` and `clause/2` are implemented, so the detection logic can be written in pure Prolog rather than Python.

---

## 4. Rule Safety / Loop Detection

**The risk:** An LLM writing rules into the KB might accidentally create a mutually recursive cycle that only terminates because of the depth limit (500). The error is cryptic ("Depth limit exceeded") and doesn't tell you which rule caused it.

**What would help:**
- Static analysis on load: detect obvious cycles (A derives B, B derives A with no base case)
- Better error reporting: when depth limit is hit, report the call stack so the problematic rule is identifiable
- A `--validate` flag that loads the KB, runs a static cycle check, and reports suspicious rules without executing queries

**Complexity:** Cycle detection is a graph problem (DFS on the predicate dependency graph). Static analysis only — no runtime changes needed. Moderate complexity.

---

## Priority / Sequencing

If these were to be implemented in order of value vs. effort:

1. **Conflict detection** — low effort, high day-to-day value, prevents a real failure mode
2. **Forward chaining** — moderate effort, makes the KB more legible and the manifest more useful
3. **Rule safety / loop detection** — moderate effort, defensive value, nice for a public-facing tool
4. **CLP(FD) constraints** — high effort, qualitatively expands what the skill can reason about, but only needed for scheduling/resource/puzzle use cases
