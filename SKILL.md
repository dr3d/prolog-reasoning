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
2. Check if already in KB: `python3 prolog-executor.py "parent(ann, scott)." -kb ~/.hermes/knowledge-base.pl`
3. Append new facts to `knowledge-base.pl` under appropriate section
4. Add date comment: `% added 2026-04-01`
5. Run `python3 prolog-executor.py --validate -kb ~/.hermes/knowledge-base.pl` — fix any warnings before proceeding
6. Only after KB is validated — hand off to normal prose compaction

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

---

## Output Format

```json
{ "success": true,  "bindings": [{"X": "bob"}, {"X": "liz"}] }
{ "success": false, "error": "No solutions found" }
```

Empty bindings `[{}]` means the query succeeded with no variables — ground query confirmed true.

---

## Correcting Facts

If the user corrects a fact, find and update `knowledge-base.pl` directly — do not append a contradicting fact. Two conflicting ground clauses both succeed in Prolog, giving wrong duplicate results.

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
