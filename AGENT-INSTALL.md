# Agent Install Instructions

Read this file completely before taking any action. Each step includes an explicit check — do not skip checks or assume state.

---

## Step 1 — Verify Python

```bash
python3 --version
```

Required: 3.9 or higher. If `python3` is not found, stop and tell the user Python 3.9+ is required.

---

## Step 2 — Install the skill

Check whether `~/.hermes/skills/prolog-reasoning` already exists:

```bash
ls ~/.hermes/skills/prolog-reasoning 2>/dev/null && echo EXISTS || echo MISSING
```

**If MISSING:** clone directly into the skills directory:

```bash
mkdir -p ~/.hermes/skills
git clone https://github.com/dr3d/prolog-reasoning.git ~/.hermes/skills/prolog-reasoning
```

**If EXISTS:** the skill is already installed. Continue to Step 3.

---

## Step 3 — Set up a knowledge base for the current project

The knowledge base and executor live in the project directory, not in the skill directory. Use the current working directory as the project root.

Check whether `prolog-executor.py` already exists here:

```bash
ls prolog-executor.py 2>/dev/null && echo EXISTS || echo MISSING
```

**If MISSING:** initialize a blank knowledge base:

```bash
python3 ~/.hermes/skills/prolog-reasoning/prolog-executor.py --init blank
```

If you want a domain-specific starter instead of blank, replace `blank` with one of: `personal`, `project`, `game`, `access-control`.

**If EXISTS:** skip — do not overwrite a knowledge base that may already contain facts.

---

## Step 4 — Generate the manifest

Run from the project directory (where `knowledge-base.pl` lives):

```bash
python3 ~/.hermes/skills/prolog-reasoning/prolog-executor.py --manifest -kb knowledge-base.pl
```

This writes `~/.hermes/kb-manifest.json` and prints the manifest. The `-kb knowledge-base.pl` tells the manifest to include the project KB. If `~/.hermes/knowledge-base.pl` also exists, it will appear as a second block automatically.

Verify the output contains a `## Knowledge Base` block for the project:

```
## Knowledge Base
Facts: N  Rules: N
Predicates: ...
Known entities: ...
Skill: prolog-reasoning
Query: python3 ~/.hermes/skills/prolog-reasoning/prolog-executor.py "<prolog_query>" -kb knowledge-base.pl
```

If the command fails with "file not found", confirm `knowledge-base.pl` exists in the current directory (Step 3 should have created it).

---

## Step 5 — Wire the manifest into Hermes prefill

**CRITICAL:** The `prefill_messages_file` key MUST be nested under `agent:` in config.yaml. 
The CLI reads it from `CLI_CONFIG["agent"]["prefill_messages_file"]`. Top-level placement only works for gateway/cron, NOT interactive CLI sessions.

Check whether `~/.hermes/config.yaml` exists:

```bash
ls ~/.hermes/config.yaml 2>/dev/null && echo EXISTS || echo MISSING
```

**If MISSING:** create it with proper nesting:

```bash
cat > ~/.hermes/config.yaml << 'EOF'
agent:
  prefill_messages_file: ~/.hermes/kb-manifest.json
EOF
```

**If EXISTS:** check whether `prefill_messages_file` is already set under `agent:`:

```bash
grep -A1 "^agent:" ~/.hermes/config.yaml | grep prefill_messages_file && echo CORRECTLY_SET || echo NEEDS_FIXING
```

- If CORRECTLY_SET: leave it alone and tell the user the existing value.
- If NEEDS_FIXING or if `prefill_messages_file` exists at top level (WRONG): you must edit config.yaml to move/add it under `agent:`. Use a YAML editor or patch tool to ensure proper nesting.

**Common pitfall:** Don't just append `agent:\n  prefill_messages_file: ...` to the end of an existing config that already has an `agent:` section — this creates duplicate keys and breaks YAML parsing. Instead, insert it into the existing `agent:` block.

---

## Step 6 — Smoke test

```bash
python3 ~/.hermes/skills/prolog-reasoning/prolog-executor.py "1 is 1." -kb knowledge-base.pl
```

Expected output:

```json
{"success": true, "bindings": [{}]}
```

Empty bindings `[{}]` means the ground query succeeded. If `success` is `false`, confirm `knowledge-base.pl` exists in the current directory.

---

## Done

Tell the user:
- Where the skill was installed (`~/.hermes/skills/prolog-reasoning/`)
- Where the KB lives (current project directory)
- That the manifest is wired into `~/.hermes/config.yaml`
- That they should regenerate the manifest after any KB write: `python3 ~/.hermes/skills/prolog-reasoning/prolog-executor.py --manifest`
