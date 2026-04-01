---
name: prolog-reasoning
description: Structured fact journal and inference engine — stores hard facts as Prolog, queries them before reasoning
---

# prolog-reasoning

A persistent, queryable fact store for Hermes. When conversations contain definite facts about the world, they go here — not into prose summaries. Ground Prolog facts are lossless, deduplicatable, and inferable. This is the structured memory layer.

## Invocation Modes

This skill has two modes depending on how it is called:

**Compaction mode** — invoked with no query, or with the word `compact`:
> "prolog-reasoning" / "prolog-reasoning compact"

The agent's job is to sweep the current conversation, extract hard facts, and write them to `knowledge-base.pl`. Do this before any prose summarization — facts must be extracted while the full context is still available. This is the primary way the KB gets populated.

**Query mode** — invoked with a Prolog query:
> "prolog-reasoning: ancestor(tom, X)."

Run the query against the KB and return results. Use this before answering any factual question about a known entity.

When in doubt about which mode: if the conversation is long or being wound down, default to compaction mode first, then answer any pending question.

**Preferred pattern — extract in real time, don't wait:** When the user states a hard fact mid-conversation, write it to the KB immediately. Don't accumulate and batch at compaction time — that risks losing precision. Compaction mode is a catch-all sweep, not the primary intake path.

---

## Core Idea

LLM memory compaction is lossy. This skill is the lossless alternative for hard facts. When a conversation establishes that X is true — not hypothetically, not tentatively — that fact belongs in `knowledge-base.pl` as a Prolog term. The engine is deliberately simple: store ground facts, query with shallow inference. No WAM required.

## When to Write Facts

**Do extract** when the user or conversation definitively asserts:
- Relationships between people: family, friendships, professional connections
- Attributes of people or things: location, occupation, age, preferences
- Events that occurred: meetings, decisions, completions
- Memberships and classifications: roles, categories, ownership
- Policies or rules the user has stated as fixed

**Do not extract**:
- Questions ("does scott have a sister?")
- Hypotheticals ("what if I moved to Austin")
- Hedged statements ("I think bob might be retired")
- Opinions that may change ("I prefer tabs over spaces right now")
- Things already in the KB (check before asserting)

**Trigger points** — always check whether to extract when:
1. The user states a biographical or relational fact about themselves or known people
2. A conversation is being summarized or compacted
3. The user corrects a prior belief ("actually, ann is my aunt not my cousin")
4. A task completes and its outcome is a fact ("the migration ran successfully on 2026-03-31")

## When to Query

Before answering any factual question about a person, place, relationship, or policy that might be in the KB — query first. Do not rely on LLM recall for things that should be in the KB. Examples:

```bash
# Is X related to Y?
python3 prolog-executor.py "ancestor(tom, X)."

# What role does a user have?
python3 prolog-executor.py "role(alice, R)."

# What do we know about scott?
python3 prolog-executor.py "findall(P-V, property(scott, P, V), Facts)."
```

## Schema Conventions

Use lowercase atoms for all values. Use underscores for multi-word atoms, or quoted atoms for proper nouns with punctuation.

```prolog
% RIGHT
lives_in(scott, austin).
parent(ann, scott).
occupation(scott, 'software-engineer').

% WRONG — hyphens parse as minus in Prolog
parent(mary-ann, scott).   % mary-ann is subtraction, not an atom
```

### Predicate naming by domain

**People / identity**
```prolog
person(scott).
male(scott).  female(dana).
born(scott, 1975).          % year or date atom
lives_in(scott, austin).
occupation(scott, developer).
```

**Relationships**
```prolog
parent(ann, scott).         % parent(Parent, Child)
spouse(scott, susan).
ex_spouse(scott, susan).
sibling(scott, blake).
partner(scott, hope).
```

**General properties** — use `property/3` for one-offs rather than inventing a new predicate:
```prolog
property(scott, eye_color, brown).
property(scott, prefers, dark_mode).
```

**Events**
```prolog
event(migration_completed, '2026-03-31').
event(started_job, '2024-01-15').
```

**Memberships / roles**
```prolog
role(alice, admin).
member(scott, team_platform).
```

**Rules** — derive from facts, don't assert redundantly:
```prolog
grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
sibling(X, Y) :- parent(P, X), parent(P, Y), X \= Y.
```

## Memory Compaction Protocol

**Order matters: extract facts before prose summarization.** Once the conversation is summarized, precision is gone.

When invoked in compaction mode:

1. Sweep the full conversation for hard facts (see criteria above)
2. For each candidate, verify it is not already in the KB: `python3 prolog-executor.py "parent(ann, scott)."`
3. Append new facts to `knowledge-base.pl` under the appropriate section
4. Add a date comment for recently established facts: `% added 2026-03-31`
5. Only after KB is updated — hand off to normal prose compaction for the rest

## Correcting Facts

If the user corrects a fact, find and update `knowledge-base.pl` directly — do not append a contradicting fact. Two conflicting ground clauses both succeed in Prolog.

## Ambient Awareness — Manifest in Prefill

The agent should not have to decide "should I check the KB?" — it should always know what the KB contains. Achieve this by injecting a manifest into every session via Hermes `prefill_messages_file`.

Generate the manifest:
```bash
python3 prolog-executor.py --manifest
# ## Knowledge Base
# Facts: 47  Rules: 8
# Predicates: parent/2  role/2  lives_in/2  ...
# Known entities: scott, ann, blake, alice, ...
```

To keep it current, regenerate after every KB write:
```bash
~/.hermes/skills/prolog-reasoning/scripts/generate-manifest.sh [kb_path] [output_path]
# default output: ~/.hermes/kb-manifest.md
```

Then in `~/.hermes/config.yaml`:
```yaml
prefill_messages_file: /Users/you/.hermes/kb-manifest.md
```

With this in place the agent wakes up every session already knowing what entities and predicates exist in the KB. Fact recall becomes ambient — no decision required.

## Two-Tier KB Architecture

For projects with both personal and project-specific facts, maintain separate KBs:

**Global KB** (`~/.hermes/knowledge-base.pl`):
- Persistent personal facts across all sessions
- Family tree, career history, preferences
- Never deleted or reset between sessions

**Session/Project KB** (`~/project-name/knowledge-base.pl`):
- Project-specific facts (assets, scenes, progress)
- Can be promoted to global later if relevant
- Isolated per project to avoid context bleed

Query either with `-kb <path>`:
```bash
python3 prolog-executor.py "lives_in(scott, X)." -kb ~/.hermes/knowledge-base.pl
python3 prolog-executor.py "scene_needed(X)." -kb ~/myst/knowledge-base.pl
```

## Output Format

```json
{ "success": true,  "bindings": [{"X": "bob"}, {"X": "liz"}] }
{ "success": false, "error": "No solutions found" }
```

Empty bindings `[{}]` means the query succeeded with no variables (ground query confirmed true).

## Pitfalls

- Hyphenated atoms (`mary-ann`) parse as subtraction — use `'mary-ann'` or `mary_ann`
- Variable names must start with uppercase (`X`, `Parent`, `Role`)
- Anonymous variable `_` matches anything, binds nothing
- Don't assert both a fact and a rule that derives the same predicate — the fact is redundant and causes duplicate results
- Depth limit is 500 — deep recursive rules will error; prefer iterative facts over deep recursion

### Executor Implementation Pitfalls

**Ground query bug**: When unification succeeds with no variables left to bind, it returns `{}` (empty dict), which is falsy in Python. Always check `if s is not None:` not `if s:`:

```python
# WRONG - ground queries fail!
s = unify(query_args, fact_args)
if s: results.append(s)           # {} evaluates to False!

# CORRECT
if s is not None: results.append(s)  # {} means success with no bindings
```

**Body predicate merging**: When combining substitution dicts from resolved body predicates, don't call `unify()` on them — just merge and check for conflicts:

```python
# WRONG - unify() doesn't handle dict-to-dict unification
u = unify(sr, r)
if u is not None: new_body.append(u)

# CORRECT - merge dicts directly
merged = {**r, **sr}
conflict = any(k in r and r[k] != v for k,v in sr.items())
if not conflict: new_body.append(merged)
```

These bugs cause rules to fail even when facts exist (e.g., `grandparent(medley, scott)` returns no results).

**No built-in list predicates**: The executor does NOT have `member/2`, `append/3`, or other common list operations. You must define them yourself in the KB:

```prolog
% Define member/2 if you need it
member(X, [X|_]).
member(X, [_|T]) :- member(X, T).
```

Without this, rules using `member/2` will fail with "No solutions found" even when the logic is correct.

**Depth limit handles cycles**: The executor has a built-in depth limit of 500 recursive calls. For transitive closure on graphs with cycles (bidirectional navigation, family trees), you can rely on this instead of implementing visited-list tracking:

```prolog
% Simple version - relies on depth=500 limit to prevent infinite loops
can_reach(A, B) :- connects(A, B).
can_reach(A, B) :- connects(A, Mid), can_reach(Mid, B).
```

This works for most practical cases and is simpler than visited-list approaches (which require `member/2`).

### Advanced Patterns

**Transitive closure with cycles**: For graph traversal where cycles exist (bidirectional navigation, family trees), rely on the executor's depth limit rather than implementing visited-list tracking. The executor has a built-in depth limit of 500 recursive calls:

```prolog
% Simple version - relies on depth=500 limit to prevent infinite loops
can_reach(A, B) :- connects(A, B).
can_reach(A, B) :- connects(A, Mid), can_reach(Mid, B).
```

This works for most practical cases and is simpler than visited-list approaches (which require `member/2` that must be defined manually).

**Mixed-arity predicates**: When you need optional arguments, handle both forms explicitly:

```prolog
% Accepts scene/2 or scene/3
main_island_scene(Scene) :- 
    (scene(Scene, _) ; scene(Scene, _, _)), 
    \+ is_age(Scene),
    !.  % cut prevents duplicates if scene appears in both forms
```

Note: Mixed arity can be a code smell — consider using separate `property/3` predicates instead of optional arguments.

**KB as living documentation**: Use meta-predicates to track project state, not just facts:

```prolog
% Track what's left to build
todo(calibrate_hotspots, 'adjust x,y,w,h coordinates').
todo(implement_puzzle, 'tower rotation mechanic').

% Test checklist
test(start_button_works).
test(all_scenes_load).

% Query todos: findall(T, todo(T, _), Tasks)
```

This turns the KB into an active project management tool that survives session loss.
