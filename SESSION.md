# Session Notes — 2026-04-02 (session 5)

## Session 5 — Gemini integration, --validate, test expansion

### Gemini collaboration
Antigravity loaded the project with Gemini 2.5, which implemented `retractall/1` and `assertz_unique/1` — both were already in FUTURE.md. Changes reviewed, tests passed, accepted and pushed. Gemini also produced a DEEP_DIVE_PLAN.md and GEMINI-NOTES.md; both absorbed (one pitfall extracted into SKILL.md: relationship-first storage) and deleted. Nothing else was net-new.

### retractall/1 and assertz_unique/1
Both shipped in one commit. `retractall` mirrors existing `retract/1` — same `_clause_to_term` path, removes all matches, always succeeds. `assertz_unique` uses structural `==` equality to prevent KB bloat. 2 tests added. Both removed from FUTURE.md.

### --validate flag
New CLI mode catches the primary silent failure: unquoted dates and hyphenated names parsed as arithmetic by the Prolog parser. Walks clause heads after load (bodies excluded — arithmetic there is intentional), flags compounds with arithmetic functors in data positions.

Date pattern `-(-(year, month), day)` detected specifically and shows the exact fix: `'2026-03-31'`. Hyphen between names shows both options: `mary_ann` or `'mary-ann'`. Arithmetic expressions (`10+5`, `3*4`) show quoted form. Every warning is self-contained — LLM can apply the fix without guessing.

Added to compaction workflow in SKILL.md (step 5 after writing facts). Added to pitfalls cross-reference. Added to README quick-start. FUTURE.md §5 updated — `--validate` now exists for syntax; cycle detection is the remaining open item there.

### Test expansion
26 `TestValidate` tests added (132 total): all four arithmetic operators, arg position reporting, functor/arity in warnings, pre-1900 years, zero-arity heads, nested bad terms, quoted vs unquoted variants, mixed KBs, rule bodies excluded, and CLI exit codes + output strings end-to-end via `run_validate` with temp files.

### Daily KB backup
`--manifest` now snapshots `~/.hermes/knowledge-base.pl` to `~/.hermes/backups/knowledge-base-YYYY-MM-DD.pl` on first call of the day. Keeps last 7 days. Silent, no agent steps, no new flag. Recovery from calamitous LLM writes.

### README updated
`retractall/1` and `assertz_unique/1` added to capabilities list. `--validate` description expanded (exit codes, what it catches). Daily backup behaviour documented near manifest section.

---

# Session Notes — 2026-04-02 (continued)

## Session 4 continued — demos, critique reviews, README polish

### Polypharmacy demo

New demo added: `demos/polypharmacy/`. Patient on 7 drugs for 5 conditions. Engine derives `at_risk(margaret, bleeding)` from warfarin + thrombocytopenia (never stored, always inferred), uses that derived state to block ibuprofen — three-hop inference. Active regimen audit surfaces amiodarone interacting with warfarin, digoxin, and atorvastatin simultaneously via CYP2C9, P-gp, and CYP3A4 enzyme inhibition. Strongest demo in the set.

Found and fixed another engine bug while building it: `query()` was using `_deref` instead of `_apply_bindings` to serialize result variables — compound terms showed internal `_Gn` variable names instead of resolved values (e.g. `direct_interaction(_G25, _G26)` instead of `direct_interaction(warfarin, bleeding_risk)`). Fixed, test added. 104 tests total.

### Demos folder

`scenarios/` renamed to `demos/`. All three original READMEs reworked — wrong expected outputs corrected, copy-paste script errors removed, stub rules documented. `demos/README.md` index added. Top-level README updated with demos table (four entries) and count.

### Symlink removal

`ln -s` step removed from README and AGENT-INSTALL.md — full path invocation is simpler and correct.

### Manifest mtime caching

`run_manifest()` now skips regeneration if `kb-manifest.json` is already newer than all KB source files. One `stat()` per KB file, otherwise no work done.

### CHATGPT-IDEAS.md / CRITIQUE.md — absorbed and deleted

Both external review files consumed, useful ideas extracted into FUTURE.md, files deleted.

**FUTURE.md additions from reviews:**
- `retractall/1` — trivial missing built-in, needed for clean entity updates
- Deduplication on assert — prevent silent KB bloat
- Entity aliases as Prolog facts (not Python-side lookup table)
- Query timeout / search budget — needed before public release
- Domain suitability documentation — prevent tool misuse

**Deliberate non-goals:** probabilistic reasoning (philosophical mismatch with ground-truth KB), Python-side normalization layer (agent's job), IR layer (SKILL.md handles it).

### README: Honest Scope section

New section added explaining what the tool is and isn't — closed-world domains, no fuzzy knowledge, not a general reasoning upgrade, not production-hardened. The translation problem called out explicitly. Right mental model: "typed queryable fact store with inference." Preempts misuse and sets expectations for an exploratory project.

### Acknowledgements updated

Nemotron-3-nano-4B added — contributed manifest injection diagnosis and caught the date/hyphen gotcha. Qwen3.5-27B continued collaboration. Claude Sonnet 4.6 listed for engine/test/demo work.

---

# Session Notes — 2026-04-02

## Session 4 (2026-04-02) — test suite, engine fixes, demos, manifest caching

### Test suite (103 tests)

Zero tests existed. Writing the suite immediately exposed 5 real engine bugs:

1. **`\+` prefix hijacked by infix `+`** — `\+(fail)` was parsed as `\` applied to `+(fail)` because the infix loop ran before the prefix check. Fixed by moving the `\+` check above the infix loop.

2. **List detection over-eager** — `[] = []` was being swallowed as list syntax because the guard was `s.startswith('[') and s.endswith(']')`. Fixed with `_bracket_end()` — only treat as a list if the `[` at position 0 closes at the very last character.

3. **Outer parens not stripped** — `\+(true)` parsed the inner `(true)` as an atom, not the built-in `true`. Fixed by adding a paren-stripping pass in `_parse_term`.

4. **Anonymous variables aliased** — `[_, _] = [1, 2]` failed because both `_` shared the same binding slot. Fixed by calling `_rename_anon()` on the query goal before solving.

5. **`mod` missing from infix operator list** — `X is 10 mod 3` returned no solutions. Fixed by adding `mod` to the operator loop.

5 expected failures document confirmed open issues: cut escaping `findall/3`, `(A,B)` conjunction as subgoal, `assert((head :- body))` syntax, raw query conjunction, occurs check.

### Engine fix: compound term deref in results

`query()` was using `_deref` to serialize result variables. `_deref` stops at a Compound without resolving its args through the bindings — so compound reason terms like `direct_interaction(warfarin, bleeding_risk)` came out as `direct_interaction(_G25, _G26)`. Fixed by switching to `_apply_bindings` which recursively resolves the full term. Test added.

### Manifest mtime caching

`run_manifest()` now skips regeneration if `kb-manifest.json` is already newer than all KB source files. Comparison via `os.path.getmtime`. Returns existing manifest content in that case. Safe to call repeatedly — cost is one `stat()` per KB file.

### Symlink removed

README and AGENT-INSTALL.md both had a `ln -s` step in project setup instructions. Removed — full path to the executor is simpler and correct.

### Demos folder

`scenarios/` renamed to `demos/`. Four self-contained worked examples added, each with a KB, runnable queries with verified expected outputs, and a README explaining the reasoning:

- **abyss-alpha** — robotic outpost safety. Recursive fault detection through part hierarchy (`gimbal_lock` → `thruster_main` → `rov_01`). Numeric clearance comparison. Original READMEs had wrong expected outputs (drone_alpha listed as mission-ready — no battery fact exists for it).

- **neocircuit-global** — supply chain compliance. Recursive vendor chain traversal. `Volt-Tech Inc` is certified but its upstream supplier `Primary-Ores LLC` is sanctioned — `has_risk` still fires. Original `audit-chain.sh` was a verbatim copy of abyss-alpha's script with wrong queries throughout. Fully replaced.

- **world-builder** — narrative continuity. Epistemic facts, faction relationships, `world_is_consistent` integrity check. Several rules reference undefined predicates (`connected/2`, `originally_from/2`, etc.) — documented honestly as stubs with instructions on what facts to add to make them fire.

- **polypharmacy** — drug interaction safety. Patient on 7 drugs for 5 conditions. Engine derives `at_risk(margaret, bleeding)` from two independent facts (warfarin + thrombocytopenia) — never stored, always inferred. Uses that derived state to block ibuprofen via a third rule (`elevated_risk(bleeding)` → NSAID contraindicated). Three-hop inference. Active regimen audit surfaces amiodarone interacting with warfarin, digoxin, and atorvastatin simultaneously via enzyme pathway inhibition (CYP2C9, P-gp, CYP3A4). The amiodarone finding is the clearest demonstration of what Prolog sees that an LLM would miss.

### Known limitations documented

- Conjunction in raw query strings (`"A, B"`) not supported — parser doesn't handle top-level comma. Workaround: wrap in a rule body.
- `(A, B)` parenthesized conjunction as `findall` subgoal doesn't work for same reason.
- `assert((head :- body))` — `:-` not in the infix operator list.
- Occurs check omitted (standard Prolog behaviour, but `X = f(X)` will infinite-loop in `_term_to_str` if the binding is ever serialized).

---

# Session Notes — 2026-04-01

## Session 3 (2026-04-01) — trigger problem solved

**Problem:** Qwen wasn't using the prolog-reasoning skill for factual questions — it answered from injected memory instead of querying the KB.

**Root cause:** The skill description was a multi-paragraph blob, and SKILL.md opened with schema conventions rather than a hard behavioral rule. Qwen would see the skill in the index but not choose it over the default memory path.

**Fix 1 — SKILL.md rewrite (Qwen + Claude):**
- New frontmatter description: tight one-liner, explicit "use instead of prose memory for anything definitively true"
- Opens with decision tree (query first or not) and Wrong/Right examples showing the exact failure mode
- Restored missing "When to Write / Do Not Extract" section — critical guard against extracting hedged statements
- Fixed broken query on line 155 (`findall(R, call(_, X), Facts)` → removed, patterns replaced with working examples)

**Fix 2 — `run_manifest` bug (`prolog-executor.py`):**
- `kb_path` argument was received but silently ignored — always read `~/.hermes/knowledge-base.pl`
- Now uses the specified KB, falls back to global, and includes global KB as a second block when a project KB is given

**Fix 3 — Assistant prefill (behavioral commitment):**
- Was: `"Understood. I have the knowledge base manifest in context."` — passive, no commitment
- Now: `"Understood. Known entities: alice, ann... I will run prolog-executor.py before answering any factual question about entities in the knowledge base — not from memory."`
- The model's own prior turn is the closest thing to enforcement available without Hermes-level hooks

**Fix 4 — Manifest query hint includes `-kb` path:**
- Was: `Query: python3 prolog-executor.py "<prolog_query>"`
- Now: `Query: python3 prolog-executor.py "<prolog_query>" -kb ~/.hermes/knowledge-base.pl`
- Eliminates the "exit 2 fumbling phase" where Qwen ran queries without `-kb` before loading skill view

**Validated:** "who is lemuel" — Qwen ran 15+ queries against the KB before answering, got birth year, death year, relation to Medley, all from KB results. No memory fallback.

**Still true:** `Skill: prolog-reasoning` sentinel in the manifest is not auto-processed by Hermes. Skills still fire via description matching and explicit invocation. Behavioral prefill is the effective substitute and is working.

---

## Session 3 continued — doc/engine polish (2026-04-01)

**Date/hyphen gotcha (caught by Nemotron-nano-4B):**
- 4B model reviewed SKILL.md correctly but then wrote `milestone(beta_deadline, 2026-05-12).` in its own example KB — exactly the bug it had just read about
- `2026-05-12` parses as arithmetic: 2026 − 5 − 12 = 2009. Silent wrong value, no error
- Fixed: Pitfall entry now says "hyphens are subtraction" and names dates explicitly alongside names; Events schema block now shows a WRONG example with the evaluated result

**Project KB placement bug:**
- `DATABASE` constant was `os.path.dirname(__file__) + "knowledge-base.pl"` — resolved to the skill dir (`~/.hermes/skills/prolog-reasoning/`), not cwd. Unqualified queries read the wrong KB
- Changed to bare `"knowledge-base.pl"` (cwd-relative). This is what caused project KBs to land next to the global one in `~/.hermes/`
- AGENT-INSTALL.md Step 4 updated: `--manifest` now uses `-kb knowledge-base.pl` so project KB goes into manifest

**No-args default:**
- `python3 prolog-executor.py` with no arguments returned a JSON error ("no query provided")
- Now defaults to `--manifest -kb knowledge-base.pl` — shows local KB manifest, like `git status`

**EXAMPLE-GAME-DEV.md:**
- Added explicit keycard KB update in Session 5 (was implicit — query result didn't make sense without it)
- `-kb` flags added then removed as executor defaults evolved — file is now clean, no explicit `-kb` needed for local KB queries

**Collaboration note:**
- Qwen3.5-27B rewrote SKILL.md structure (decision tree, wrong/right examples, behavioral opening)
- Claude fixed remaining issues (broken query, missing When-to-Write section, rules in schema)
- Nemotron-nano-4B did a useful review pass and caught the date gotcha by reproducing it
- All three models contributed to the final state

---

## Session 2 update (2026-04-01)

Re-confirmed the two root causes below. Found one straggler: `scripts/generate-manifest.sh`
still defaulted to `kb-manifest.md` and commented `prefill_messages_file` without the
`agent:` nesting. Fixed — script now defaults to `~/.hermes/kb-manifest.json` and documents
the required `agent:` nesting.

**Next step:** retest prefill injection on Mac mini with corrected config.yaml and `.json` manifest.

---

## Status: prefill injection fixed

The prefill bug is resolved. Two root causes found and fixed:

1. **Wrong config nesting** — CLI reads `prefill_messages_file` from `CLI_CONFIG["agent"]`
   (`cli.py:1180`), so it must be nested under `agent:` in `config.yaml`. Top-level
   placement is only read by gateway and cron, not the interactive CLI.

2. **Wrong file format** — `_load_prefill_messages` does `json.load()`. A `.md` file
   throws silently (caught, `logger.warning`, returns `[]`). File must be a JSON array
   of `{role, content}` dicts.

### Fix applied (committed, pushed)

`run_manifest` in `prolog-executor.py` now writes `~/.hermes/kb-manifest.json` as a
two-message prefill array:

```json
[
  {"role": "user", "content": "<manifest text>"},
  {"role": "assistant", "content": "Understood. Known entities: ... I will run prolog-executor.py before answering any factual question about entities in the knowledge base — not from memory."}
]
```

README updated to match.

## Still needed on Mac mini

1. Run `python3 prolog-executor.py --manifest` to regenerate `~/.hermes/kb-manifest.json`
2. Update `~/.hermes/config.yaml`:

```yaml
agent:
  prefill_messages_file: ~/.hermes/kb-manifest.json
```

3. Start a new Hermes session and verify the manifest terms appear in context at turn 1.

## Two-tier KB design intent

- Global manifest always in context via prefill → triggers skill load → skill detects local KB → injects local manifest
- Global tier is now working (once config.yaml is updated on Mac)
- Local KB tier not yet implemented

## Skill auto-load from manifest — still not implemented

`Skill: prolog-reasoning` sentinel is in the manifest content but Hermes ignores it.
Skill only fires via the three conditions in the description. This is a separate problem
from prefill — don't conflate them.

## Hermes source location

`/d/_PROJECTS/_TOOLS/hermes-agent`
