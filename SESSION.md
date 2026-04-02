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
