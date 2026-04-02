# Prolog Reasoning — Lossless Memory for LLM Agents

A [Hermes](https://github.com/NousResearch/hermes-agent) skill and standalone engine for storing hard facts that LLM agents can query and reason from. No server. No schema. No embeddings. No dependencies beyond Python.

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

You asserted a handful of `parent` and `permission` facts. The engine does the rest. No re-summarization, no retrieval, no guessing.

---

## Try It

The executor is a standalone Python script. Clone the repo and query the sample KB immediately — no agent setup, no config:

```bash
git clone https://github.com/dr3d/prolog-reasoning.git
cd prolog-reasoning
```

```bash
# Inference: ancestors derived from parent facts
python3 prolog-executor.py "ancestor(tom, X)."
# {"success": true, "bindings": [{"X": "bob"}, {"X": "liz"}, {"X": "ann"}, {"X": "pat"}]}

# Access control: what can alice do?
python3 prolog-executor.py "allowed(alice, X)."
# {"success": true, "bindings": [{"X": "read"}, {"X": "write"}, {"X": "delete"}]}

# Classification: what can fly?
python3 prolog-executor.py "can_fly(X)."
# {"success": true, "bindings": [{"X": "eagle"}, {"X": "bat"}]}

# Arithmetic
python3 prolog-executor.py "factorial(6, F)."
# {"success": true, "bindings": [{"F": "720"}]}
```

```bash
# See what's in the KB
python3 prolog-executor.py --manifest
```

None of `ancestor`, `allowed`, or `can_fly` are stored as facts — they're derived by rules from a handful of `parent`, `role`, and `bird` assertions. That's the point.

To start a KB for your own project: `python3 prolog-executor.py --init blank` (or `personal`, `project`, `game`, `access-control`). Edit `knowledge-base.pl` directly or let the agent write it. The Hermes integration is the layer on top — the engine underneath is just Python and logic.

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
# Skill: prolog-reasoning
# Query: python3 prolog-executor.py "<prolog_query>" -kb ~/.hermes/knowledge-base.pl
```

No per-turn KB lookups needed. The agent wakes up knowing which entities and predicates exist. Combined with the behavioral commitment in the assistant prefill turn, this is what drives the agent to query before answering — not from memory.

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
python3 prolog-executor.py "lives_in(scott, X)." -kb ~/.hermes/knowledge-base.pl
python3 prolog-executor.py "scene_needed(X)."    -kb ~/myst/knowledge-base.pl
```

---

## Demos

The `demos/` folder contains four self-contained worked examples — each with its own KB, runnable queries, and a README explaining what the engine is doing and why it matters:

| Demo | Domain | Key reasoning |
|------|--------|---------------|
| [`demos/abyss-alpha/`](demos/abyss-alpha/) | Robotic outpost safety | Recursive fault detection through part hierarchies, negation-as-failure, transitive access control |
| [`demos/neocircuit-global/`](demos/neocircuit-global/) | Supply chain compliance | Recursive vendor chain traversal, transitive sanctions risk — one bad actor poisons the whole product |
| [`demos/world-builder/`](demos/world-builder/) | Narrative continuity | Epistemic facts, faction relationships, world consistency checking for long-form fiction |
| [`demos/polypharmacy/`](demos/polypharmacy/) | Drug interaction safety | Three-hop derived risk inference — engine derives bleeding risk from two independent facts, uses it to block a third drug |

Each demo is runnable immediately from the repo root. See the individual READMEs for queries and expected outputs.

---

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions — when to extract, when to query, schema conventions |
| `prolog-executor.py` | Pure-Python Prolog interpreter, zero dependencies |
| `knowledge-base.pl` | The fact store — created per project via `--init`, edit directly or via agent |
| `scripts/generate-manifest.sh` | Regenerate KB manifest after writes |
| `templates/` | Domain starter KBs (`blank`, `personal`, `project`, `game`, `access-control`) — used by `--init` |
| `demos/` | Worked examples: four self-contained KBs with runnable queries and explanations |
| `EXAMPLE-GAME-DEV.md` | Realistic multi-session example: game dev using the skill across weeks |
| `FUTURE.md` | Design notes: forward chaining, CLP constraints, conflict detection |
| `AGENT-INSTALL.md` | Agent-executable install instructions with explicit conditionals |

---

## Requirements

- Python 3.9+
- [Hermes](https://github.com/NousResearch/hermes-agent)
- No other external packages

## Installation

> **Installing from inside an AI agent?** Use [`AGENT-INSTALL.md`](AGENT-INSTALL.md) — explicit step-by-step instructions written for autonomous execution, with conditional logic and no placeholders.

**1. Clone into your Hermes skills directory:**

```bash
mkdir -p ~/.hermes/skills
git clone https://github.com/dr3d/prolog-reasoning.git ~/.hermes/skills/prolog-reasoning
```

**2. Set up a knowledge base for your project:**

```bash
cd ~/your-project
python3 ~/.hermes/skills/prolog-reasoning/prolog-executor.py --init blank
```

Or start from a domain-specific template:

```bash
python3 ~/.hermes/skills/prolog-reasoning/prolog-executor.py --init personal      # biography, family, preferences
python3 ~/.hermes/skills/prolog-reasoning/prolog-executor.py --init project       # tasks, owners, dependencies
python3 ~/.hermes/skills/prolog-reasoning/prolog-executor.py --init game          # locations, inventory, quests, flags
python3 ~/.hermes/skills/prolog-reasoning/prolog-executor.py --init access-control  # users, roles, permissions
```

**3. Generate a manifest and wire it into Hermes prefill:**

```bash
python3 prolog-executor.py --manifest
```

This writes `~/.hermes/kb-manifest.json` as a prefill messages array.

```yaml
# ~/.hermes/config.yaml
agent:
  prefill_messages_file: ~/.hermes/kb-manifest.json
```

The manifest regenerates automatically when the KB has changed — `--manifest` compares file modification times and skips the write if the manifest is already newer. You can call it as often as you like without redundant disk writes.

To force a regeneration after KB writes:

```bash
~/.hermes/skills/prolog-reasoning/scripts/generate-manifest.sh
```

**4. Verify it works:**

```bash
python3 prolog-executor.py "1 is 1."
# {"success": true, "bindings": [{}]}
```

Empty bindings `[{}]` means the ground query succeeded — the engine is running.

---

## How the Skill Activates

**KB already exists (returning session):** The manifest in prefill gives the agent ambient awareness of what entities and predicates exist. The assistant prefill turn commits the model behaviorally:

> *"Understood. Known entities: alice, ann, blake... I will run prolog-executor.py before answering any factual question about entities in the knowledge base — not from memory."*

This is what drives query-before-answer behavior. The manifest also contains `Skill: prolog-reasoning` and the ready-to-run query command, so the agent has everything it needs from turn 1.

**No KB yet (first time):** The skill appears in the Hermes skill index with a one-line description. The agent discovers it when a conversation involves facts worth keeping, or you can invoke `/prolog-reasoning` directly to kick off setup. Either way, the agent runs `--init` to create the KB, then the manifest path takes over from there.

Once the manifest is wired into `config.yaml` it stays wired. The only ongoing maintenance is regenerating the manifest after KB writes — which `scripts/generate-manifest.sh` handles.

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

## Honest Scope

This is an exploratory project. It works, it's useful, and it's being actively developed — but it has real limits worth understanding before you build on it.

**What it's good at:**
- Closed-world domains where facts are definite and stable: family trees, roles and permissions, game state, medical facts, legal rules, supply chain relationships
- Answering questions that require traversing relationships the agent never explicitly stored
- Catching contradictions and enforcing consistency that an LLM would miss across a long session
- Giving the agent a source of truth that doesn't decay under context compression

**What it's not:**
- A general reasoning upgrade for LLMs. It doesn't make the model smarter — it gives it a deterministic sandbox for a specific class of logic problems.
- Suitable for fuzzy, uncertain, or probabilistic knowledge. "Probably", "might", and "I think" don't belong in a Prolog KB. If you need uncertainty quantification, this is the wrong tool.
- A replacement for the LLM's semantic layer. Natural language understanding, ambiguity resolution, and fact extraction are still the model's job. The KB stores what the model has already decided is true.
- Production-hardened. The interpreter is a clean pure-Python implementation, not a battle-tested Prolog runtime. It covers the common subset well but has known gaps (see `FUTURE.md`).

**The translation problem is real.** Everything depends on the LLM correctly converting natural language to valid Prolog facts. Small syntax errors cause silent failures. Schema drift — `parent_of` vs `parent` vs `is_parent` — breaks queries. SKILL.md addresses this with conventions and examples, but it's an ongoing challenge, not a solved one.

**The right mental model:** This is a typed, queryable fact store with inference — not a knowledge graph, not a database, not a reasoning engine in the AI sense. Prolog does search, not thinking. What it gives you is determinism, losslessness, and the ability to derive conclusions from combinations of facts that an LLM would lose track of. That's the valuable part.

---

## Where This Is Going

> **Experimental.** Prolog as LLM memory is a new idea and we're actively exploring it. The engine works, the patterns are emerging, and the schema conventions are best guesses that will evolve. If you build on this, expect to iterate — and contributions are welcome.

This project is exploring a hypothesis: that hard facts and soft context belong in different storage media, and that agents which treat them the same will always drift. Prolog is one answer to the hard-facts side of that — compact, lossless, inferable.

Open questions we're working through: the right schema conventions for common domains, how compaction interacts with KB growth over long sessions, whether forward-chaining rules belong in the KB or stay implicit in SKILL.md, and how the two-tier (global/project) model holds up at scale. `FUTURE.md` tracks the design threads. If you're using this and hitting edges, that's useful signal.

---

## Acknowledgements

This project has been developed in collaboration with several local models running on a **PowerSpec G483**. Local inference matters.

**Qwen3.5-27B** — early configuration and skill integration work, SKILL.md structural rewrite (decision tree, wrong/right examples, behavioral opening), and ongoing reasoning assistance across sessions.

**Nemotron-3-nano-4B** — review pass that caught the date/hyphen arithmetic gotcha by reproducing it in its own example KB, and contributed to diagnosing manifest injection issues with the prefill pipeline. Remarkable work for a 4B model.

**Claude Sonnet 4.6** — engine development, test suite, bug fixes, demos.

---

## License

MIT
