# Session Notes — 2026-04-01

## What we were doing

Testing manifest injection with Qwen3.5-27B. Moved from G483 back to M1 Mini mid-session.

## Open bug: prefill_messages_file not injecting

`prefill_messages_file: ~/.hermes/kb-manifest.md` in `~/.hermes/config.yaml` is NOT working.
Qwen confirmed: manifest was not in context at session start. It had to manually read config.yaml,
find the path, then open the file itself.

**Next step on G483: trace why prefill_messages_file isn't firing in Hermes source.**

## Skill auto-load from manifest — not implemented

The manifest has a `Skill: prolog-reasoning` sentinel line (commit e00078e). Intent was for Hermes
to auto-inject the skill when it sees this. It doesn't — Hermes ignores the line entirely.
Skill only fires via the three conditions in the description (fact stated, factual question, compaction).

## SKILL.md changes made today

- Removed condition 4 from skill description trigger — "manifest appears in context" was too vague,
  caused false triggers during KB conversations, and was redundant since auto-load doesn't work
- Global manifest regenerated from correct KB:
  `bash scripts/generate-manifest.sh ~/.hermes/knowledge-base.pl ~/.hermes/kb-manifest.md`
- Result: 59 facts, 10 rules, personal entities

## Two-tier KB design intent (not yet working)

- Global manifest always in context via prefill → triggers skill load → skill detects local KB → injects local manifest
- Whole cascade depends on prefill working — it doesn't, so nothing fires automatically
