# Prolog Reasoning — Lossless Memory for LLM Agents

A [Hermes](https://github.com/badayvedat/hermes) skill that gives an LLM agent a persistent, lossless fact store backed by a pure-Python Prolog interpreter. No external dependencies. No database. No embeddings. Just facts that stay true.

---

## The Problem with LLM Memory

Every standard approach to LLM memory is lossy in a way that compounds over time:

**Prose summaries** degrade precision. "Scott's mom is Ann, who lives in Ohio" becomes "Scott has family in the Midwest" after two compaction cycles. The fact is still *there*, vaguely, but you can't query it.

**Vector/embedding stores** answer "what's similar to this?" — a retrieval problem. They don't answer "is this true?" — a truth problem. You can't ask an embedding store whether Alice has write permission.

**The model's own weights** are the worst option. The model confabulates under recall pressure. It doesn't know what it knows. It fills gaps with plausible-sounding guesses.

The root issue: **hard facts need a different storage medium than context**. Prose is for narrative. Weights are for language. Neither is for truth.

---

## The Insight

Prolog ground facts are lossless by construction:

```prolog
parent(ann, scott).
role(alice, admin).
event(deploy_completed, '2026-03-31').
```

`parent(ann, scott)` is exactly as true on day 1000 as on day 1. It doesn't summarize. It doesn't drift. It doesn't hallucinate.

And because it's Prolog, facts you never explicitly stored become queryable through inference:

```prolog
grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
ancestor(X, Y)    :- parent(X, Y).
ancestor(X, Y)    :- parent(X, Z), ancestor(Z, Y).
allowed(User, Action) :- role(User, Role), permission(Role, Action).
```

```bash
python3 prolog-executor.py "ancestor(ann, X)."
# {"success": true, "bindings": [{"X": "scott"}, {"X": "blake"}, ...]}

python3 prolog-executor.py "allowed(alice, X)."
# {"success": true, "bindings": [{"X": "read"}, {"X": "write"}, {"X": "delete"}]}
```

You asserted a handful of `parent` and `permission` facts. The engine does the rest. No re-summarization, no retrieval, no guessing.

---

## How It Works in Practice

### Fact extraction (during or after conversation)

When a conversation establishes a hard fact, the agent writes it immediately:

```
user: "my sister dana just got promoted to VP"
agent: → appends  person(dana).  female(dana).  sibling(scott, dana).  role(dana, vp).
```

The agent doesn't wait for end-of-session. Facts are captured while context is still sharp.

### Querying before answering

Before answering any factual question about a known entity, the agent queries first:

```bash
# "is dana related to scott?"
python3 prolog-executor.py "sibling(scott, dana)."
# {"success": true, "bindings": [{}]}   ← ground query confirmed

# "what do we know about dana?"
python3 prolog-executor.py "findall(P-V, property(dana, P, V), Facts)."
```

The model doesn't rely on its own recall. The KB is the source of truth.

### Ambient awareness

A manifest is injected into every session so the agent always knows what's tracked:

```bash
python3 prolog-executor.py --manifest
# ## Knowledge Base
# Facts: 47  Rules: 8
# Predicates: born/2  event/2  lives_in/2  occupation/2  parent/2  role/2  sibling/2
# Known entities: alice, ann, blake, dana, scott
```

No per-turn KB lookups needed. The agent wakes up knowing what it knows.

---

## Two-Tier Architecture

Personal facts and project facts are kept separate to prevent context bleed:

**Global KB** (`~/.hermes/knowledge-base.pl`) — persistent across all sessions:
- Family, relationships, biographical data
- Career history, preferences
- Never reset

**Project KB** (`~/project-name/knowledge-base.pl`) — scoped to a project:
- Task progress, decisions, domain-specific entities
- Can be promoted to global when facts become permanent

```bash
python3 prolog-executor.py -kb ~/.hermes/knowledge-base.pl "lives_in(scott, X)."
python3 prolog-executor.py -kb ~/myst/knowledge-base.pl   "scene_needed(X)."
```

---

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions — when to extract, when to query, schema conventions |
| `prolog-executor.py` | Pure-Python Prolog interpreter, zero dependencies |
| `knowledge-base.pl` | The fact store — edit directly or via agent |
| `scripts/generate-manifest.sh` | Regenerate KB manifest after writes |
| `templates/` | Starter copies for new projects |
| `FUTURE.md` | Design notes: forward chaining, CLP constraints, conflict detection |
| `AGENT-INSTALL.md` | Agent-executable install instructions with explicit conditionals |

---

## Requirements

- Python 3.9+
- [Hermes](https://github.com/badayvedat/hermes)
- No other external packages

## Installation

> **Installing from inside an AI agent?** Use [`AGENT-INSTALL.md`](AGENT-INSTALL.md) — explicit step-by-step instructions written for autonomous execution, with conditional logic and no placeholders.

**1. Clone the skill into your Hermes skills directory:**

```bash
git clone https://github.com/dr3d/hermes-skills.git ~/.hermes/skills
```

Or if you already have a skills directory, just copy the folder:

```bash
cp -r prolog-reasoning ~/.hermes/skills/
```

**2. Set up a knowledge base for your project:**

```bash
cd ~/your-project
cp ~/.hermes/skills/prolog-reasoning/templates/prolog-executor.py .
cp ~/.hermes/skills/prolog-reasoning/templates/knowledge-base.pl.example knowledge-base.pl
```

**3. Generate a manifest and wire it into Hermes prefill:**

```bash
python3 prolog-executor.py --manifest > ~/.hermes/kb-manifest.md
```

```yaml
# ~/.hermes/config.yaml
prefill_messages_file: ~/.hermes/kb-manifest.md
```

Regenerate the manifest after any KB write to keep it current:

```bash
~/.hermes/skills/prolog-reasoning/scripts/generate-manifest.sh
```

**4. Verify it works:**

```bash
python3 prolog-executor.py "ancestor(tom, X)."
# {"success": true, "bindings": [{"X": "bob"}, {"X": "liz"}, {"X": "ann"}, {"X": "pat"}]}
```

---

## Interpreter Capabilities

- Facts, rules, unification, backtracking
- `is/2` and arithmetic: `+  -  *  //  /  mod`
- Comparisons: `>  <  >=  =<  =:=  =\=`
- `findall/3`, negation as failure (`\+`), cut (`!`)
- `assert/1`, `assertz/1`, `asserta/1`, `retract/1` (non-deterministic)
- `functor/3`, `clause/2`
- Lists, quoted atoms, anonymous variables
- Depth limit: 500 (prevents runaway recursion)

Not supported: tabling, constraint solving (CLP), DCGs, operator definitions, modules. See `FUTURE.md` for what's planned.

---

## Schema Quick Reference

```prolog
% Identity
person(scott).  male(scott).  female(dana).
born(scott, 1981).
lives_in(scott, austin).
occupation(scott, developer).

% Relationships
parent(ann, scott).         % parent(Parent, Child)
spouse(scott, susan).
sibling(scott, blake).
partner(scott, hope).

% General properties (catch-all for one-offs)
property(scott, prefers, dark_mode).
property(scott, eye_color, brown).

% Events
event(deploy_completed, '2026-03-31').
event(started_job,       '2024-01-15').

% Roles / memberships
role(alice, admin).
member(scott, team_platform).

% GOTCHA: hyphens are subtraction in Prolog
parent(mary-ann, scott).    % WRONG — parses as subtraction
parent('mary-ann', scott).  % RIGHT — quoted atom
parent(mary_ann, scott).    % RIGHT — underscore
```

---

## Why Not Just Use a SQL Database?

SQL requires a schema, a running server, and queries that enumerate everything explicitly. Prolog gives you schema-free storage and inference — `grandparent`, `ancestor`, `allowed` are never stored, they're derived. For a personal knowledge base where the shape of the data isn't known in advance, that flexibility matters.

For a zero-dependency, no-server tool that travels with a Python script and reasons about relationships the way an agent naturally thinks about them, Prolog is the right fit.

---

## License

MIT
