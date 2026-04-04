---
name: prolog-reasoning
description: "lossless symbolic memory — store hard facts as Prolog ground terms, query with inference; use instead of prose memory for anything definitively true"
tags: []
related_skills: []
---

# CRITICAL: QUERY BEFORE ANSWERING

**If the user asks a factual question about ANY entity in the KB manifest → Query Prolog FIRST.**

```
WRONG: "Your mom is Ann and dad is Ian."  ← answered from injected context
RIGHT: query parent(X, scott) → answer from results
```

**Do NOT answer from injected memory if the entity appears in the KB manifest.** The manifest at the top of this conversation tells you what's in the KB. If it mentions the person/entity → query it. Period. The injection can be stale; the KB is always current.

---

## Quick Decision Tree (Follow Every Time)

1. **User asks a factual question?**
   - YES → Go to step 2
   - NO → Skip to **When to Write Facts** below

2. **Is the entity in the KB manifest?** (check the "Known entities:" line)
   - YES → **MUST QUERY PROLOG** before answering
   - NO → Can answer from memory/context

3. **Run the query:**
   ```bash
   python3 prolog-executor.py "<query>" -kb ~/.hermes/knowledge-base.pl
   ```

4. **Answer ONLY from query results** (or say "not in KB" if no match)

---

## Examples: Wrong vs Right

### WRONG - Using Memory
```
User: "who is my mum and dad?"
Agent: "Your mom is Ann and dad is Ian."  # From injected memory!
```

### RIGHT - Querying First
```
User: "who is my mum and dad?"
Agent: [queries parent(X, scott)]
Result: {"success": true, "bindings": [{"X": "ann"}, {"X": "ian"}]}
Agent: "Based on the knowledge base: your parents are Ann and Ian."
```

### WRONG - Partial Query
```
User: "what do we know about arthur?"
Agent: [queries boxer(arthur)]  # Only checks one predicate!
Agent: "Arthur was a boxer."    # Missed that he moved to Australia!
```

### RIGHT - Comprehensive Query
```
User: "what do we know about arthur?"
Agent: [queries findall(P-V, property(arthur, P, V), Facts), then boxer(arthur)]
Result: Arthur is a boxer who moved to australia
Agent: "Arthur was a boxer who moved to Australia."
```

---

## Core Principle

**LLM memory is lossy. Prolog facts are ground truth.**

When the user states something definitively true, it goes into `knowledge-base.pl`. When you need to answer about those facts, query the KB — don't rely on injected context. Use this skill instead of prose memory tools for anything that is factually precise and should be queryable.

---

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

**Trigger points** — always consider extracting when:
1. The user states a biographical or relational fact about themselves or known people
2. A conversation is being summarized or compacted — extract facts first, then prose
3. The user corrects a prior belief ("actually, ann is my aunt not my cousin")
4. A task completes and its outcome is a fact ("the migration ran successfully on 2026-03-31")

**Preferred pattern — extract in real time, don't wait.** Compaction mode is a catch-all sweep, not the primary intake path.

---

## Invocation Modes

### Query Mode (User asks a factual question)
```bash
# Find Scott's parents
python3 prolog-executor.py "parent(P, scott)." -kb ~/.hermes/knowledge-base.pl

# What do we know about Arthur? (comprehensive)
python3 prolog-executor.py "findall(P-V, property(arthur, P, V), Facts)." -kb ~/.hermes/knowledge-base.pl

# Is X related to Y?
python3 prolog-executor.py "ancestor(tom, scott)." -kb ~/.hermes/knowledge-base.pl

# What can alice do?
python3 prolog-executor.py "allowed(alice, X)." -kb ~/.hermes/knowledge-base.pl
```

### Compaction Mode (Extract facts from conversation)
When the user states hard facts or a session is ending:
1. Sweep for definite statements (no hedging like "I think" or "maybe")
2. Assert each fact with `--assert` — validates before writing, skips duplicates silently:
   ```bash
   python3 prolog-executor.py --assert "parent(ann, scott)." -kb ~/.hermes/knowledge-base.pl
   ```
3. If `--assert` returns an error, fix the fact and retry before moving on
4. Add a date comment directly in the KB after asserting: `% added 2026-04-02`
5. Only after all facts are asserted clean — hand off to normal prose compaction

**Do not use `echo >> knowledge-base.pl`** — use `--assert` instead. It validates, deduplicates, and avoids shell security warnings.

> **Executor path**: examples above assume `prolog-executor.py` is symlinked into your project dir. If not, use the full path: `~/.hermes/skills/prolog-reasoning/prolog-executor.py`

---

## Query Patterns

```bash
# Find all parents of scott
python3 prolog-executor.py "parent(P, scott)." -kb ~/.hermes/knowledge-base.pl

# Find all children of ann
python3 prolog-executor.py "parent(ann, C)." -kb ~/.hermes/knowledge-base.pl

# All properties of scott
python3 prolog-executor.py "findall(P-V, property(scott, P, V), Facts)." -kb ~/.hermes/knowledge-base.pl

# Is medley a grandparent of scott?
python3 prolog-executor.py "grandparent(medley, scott)." -kb ~/.hermes/knowledge-base.pl

# Find all ancestors of scott
python3 prolog-executor.py "ancestor(A, scott)." -kb ~/.hermes/knowledge-base.pl
```

---

## Natural Language → Prolog

Common statement types and how to encode them. The predicate choice matters — a wrong predicate name means queries never find the fact.

| User says | Write | Notes |
|-----------|-------|-------|
| "X is Y's parent / mum / dad" | `parent(X, Y).` | `parent(Parent, Child)` — parent first |
| "X and Y are siblings" | `sibling(X, Y). sibling(Y, X).` | Assert both directions |
| "X married Y" | `married(X, Y). married(Y, X).` | Assert both directions |
| "X lives in / moved to Y" | `lives_in(X, y).` | Retract old first if correcting |
| "X's job / role is Y" | `occupation(X, y).` or `role(X, y).` | Use `occupation` for job titles, `role` for system roles (admin, etc.) |
| "X was born in year Y" | `born(X, 1975).` | Year as number, no quotes needed |
| "X was born in city Y" | `born_in(X, city).` | Separate predicate from year |
| "X died in year Y" | `died(X, 1998).` | |
| "X died in place Y" | `died_in(X, place).` | Distinct from `died/2` |
| "X happened on date Y" | `event(x_name, '2026-03-31').` | Date MUST be quoted atom |
| "X owns / has Y" | `owns(X, y).` | |
| "X is a [category]" | `person(X). male(X). female(X).` | Use typed predicates, not `is_a/2` |
| "something about X" (misc) | `property(X, key, value).` | Catch-all for one-offs |
| "X remembers / once did Y" | `memory(X, event_id). detail(event_id, 'prose').` | Anecdotes: queryable hook + prose blob |

**Argument order gotchas:**
- `parent(Parent, Child)` — not `parent(Child, Parent)`
- `permission(Role, Action)` — not `permission(Action, Role)`
- When unsure, check what rules in the KB expect, or check AGENT-TEST.md examples

---

## Schema Conventions

**Use lowercase atoms with underscores:**
```prolog
% RIGHT
lives_in(scott, austin).
parent(ann, scott).
occupation(scott, 'software-engineer').

% WRONG — hyphens parse as minus in Prolog
parent(mary-ann, scott).   % This is subtraction!
parent('mary-ann', scott). % RIGHT — quoted atom
parent(mary_ann, scott).   % RIGHT — underscore
```

**Relationships:**
```prolog
parent(ann, scott).         % parent(Parent, Child)
spouse(scott, susan).
sibling(scott, blake).
male(scott).  female(dana).
born(scott, 1975).
lives_in(scott, austin).
```

**General properties (use property/3 for one-offs):**
```prolog
property(scott, eye_color, brown).
property(arthur, moved_to, australia).
```

**Events — dates MUST be quoted atoms:**
```prolog
event(deploy_completed, '2026-03-31').  % RIGHT — quoted atom
event(started_job,      '2024-01-15').  % RIGHT

event(deploy_completed, 2026-03-31).    % WRONG — parses as 2026 minus 3 minus 31 = 1992
```

**Rules — derive, don't store redundantly:**
```prolog
grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
ancestor(X, Y)    :- parent(X, Y).
ancestor(X, Y)    :- parent(X, Z), ancestor(Z, Y).
allowed(User, Action) :- role(User, Role), permission(Role, Action).
```

**Rules are as important as facts.** A KB with only facts is a flat lookup table — it can't derive cousins, ancestors, or permissions. When seeding a new domain from a fact dump, always write the inference rules too, or start from a template that includes them:

```bash
python3 prolog-executor.py --init personal   # includes sibling/2, ancestor/2, grandparent/2, mother/2, father/2
python3 prolog-executor.py --init game       # includes can_enter/2, has_item/2, quest_complete/1
```

For a family KB, the minimum useful rule set:
```prolog
sibling(X, Y)     :- parent(P, X), parent(P, Y), X \= Y.
grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
ancestor(X, Y)    :- parent(X, Y).
ancestor(X, Y)    :- parent(X, Z), ancestor(Z, Y).
cousin(X, Y)      :- parent(PX, X), parent(PY, Y), sibling(PX, PY).
mother(X, Y)      :- parent(X, Y), female(X).
father(X, Y)      :- parent(X, Y), male(X).
```

Without these, queries like `cousin(X, oliver)` or `ancestor(reginald, X)` return nothing even if all the `parent/2` facts are present.

---

## Output Format

```json
{ "success": true,  "bindings": [{"X": "bob"}, {"X": "liz"}] }
{ "success": false, "error": "No solutions found" }
```

Empty bindings `[{}]` means the query succeeded with no variables — ground query confirmed true.

---

## Correcting Facts

**Never append a contradicting fact.** Two conflicting ground clauses both succeed in Prolog, giving wrong duplicate results.

The two-step pattern — retract old, assert new:
```bash
# User says "I moved to Portland"
python3 prolog-executor.py "retractall(lives_in(scott, _))." -kb ~/.hermes/knowledge-base.pl
python3 prolog-executor.py --assert "lives_in(scott, portland)." -kb ~/.hermes/knowledge-base.pl

# User says "Dana is now CTO, not VP"
python3 prolog-executor.py "retractall(role(dana, _))." -kb ~/.hermes/knowledge-base.pl
python3 prolog-executor.py --assert "role(dana, cto)." -kb ~/.hermes/knowledge-base.pl
```

`retractall/1` accepts patterns — `retractall(lives_in(scott, _))` removes ALL `lives_in` facts for scott regardless of the location value. Always retract before asserting when a fact can only have one true value at a time.

---

## Pitfalls

- **Hyphens are subtraction**: anything with a `-` that isn't quoted is arithmetic. This catches names (`mary-ann`) AND dates (`2026-05-12` = 2009). Always quote: `'mary-ann'`, `'2026-05-12'`. Run `--validate` after writing to catch these silently.
- **No standalone atoms**: `rtx_5090.` by itself is unqueryable noise. Always wrap in a predicate: `hardware(rtx_5090).` — then `hardware(X)` lists everything in that category.
- **Variable names**: must start uppercase (`X`, `Parent`, `Role`)
- **No built-in list predicates**: the executor has no `member/2`, `append/3` — define them in the KB if needed
- **Depth limit is 500**: deep recursive rules error; prefer iterative facts over deep recursion
- **Don't assert both a fact and a rule that derives the same predicate** — causes duplicate results

---

## Two-Tier KB Architecture

**Global KB** (`~/.hermes/knowledge-base.pl`) — persistent across all sessions:
- Family, relationships, biographical data
- Career history, preferences

**Project KB** (`~/project-name/knowledge-base.pl`) — scoped to a project:
- Task progress, decisions, domain-specific entities
- Can be promoted to global when facts become permanent

```bash
python3 prolog-executor.py "lives_in(scott, X)." -kb ~/.hermes/knowledge-base.pl
python3 prolog-executor.py "scene_needed(X)."    -kb ~/myst/knowledge-base.pl
```

---

## Ambient Awareness — Manifest in Prefill

The KB manifest is injected into every session via `prefill_messages_file`. The agent wakes up already knowing what entities and predicates exist — no per-turn decision needed.

Generate and wire it up:
```bash
python3 prolog-executor.py --manifest -kb ~/.hermes/knowledge-base.pl
# writes ~/.hermes/kb-manifest.json
```

```yaml
# ~/.hermes/config.yaml  (note: under agent:, not at root level)
agent:
  prefill_messages_file: /home/scott/.hermes/kb-manifest.json
```

Regenerate after every KB write:
```bash
~/.hermes/skills/prolog-reasoning/scripts/generate-manifest.sh
```

---

## Final Reminder

**The KB is the source of truth for immutable facts.** Injected memory can be stale or incomplete. When in doubt → query Prolog.
