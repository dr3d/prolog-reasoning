# Session Notes — 2026-04-01

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
  {"role": "assistant", "content": "Understood. I have the knowledge base manifest in context."}
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
