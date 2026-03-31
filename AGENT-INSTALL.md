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

**If MISSING:** symlink the executor (so it stays current with the skill) and initialize a blank knowledge base:

```bash
ln -s ~/.hermes/skills/prolog-reasoning/prolog-executor.py ./prolog-executor.py
python3 prolog-executor.py --init blank
```

If you want a domain-specific starter instead of blank, replace `blank` with one of: `personal`, `project`, `game`, `access-control`.

**If EXISTS:** skip — do not overwrite a knowledge base that may already contain facts.

---

## Step 4 — Generate the manifest

```bash
python3 prolog-executor.py --manifest > ~/.hermes/kb-manifest.md
```

Verify the output looks like:

```
## Knowledge Base
Facts: N  Rules: N
Predicates: ...
Known entities: ...
```

If the command fails, check that `knowledge-base.pl` is present in the current directory. The executor looks for it there by default.

---

## Step 5 — Wire the manifest into Hermes prefill

Check whether `~/.hermes/config.yaml` exists:

```bash
ls ~/.hermes/config.yaml 2>/dev/null && echo EXISTS || echo MISSING
```

**If MISSING:** create it:

```bash
cat > ~/.hermes/config.yaml << 'EOF'
prefill_messages_file: ~/.hermes/kb-manifest.md
EOF
```

**If EXISTS:** check whether `prefill_messages_file` is already set:

```bash
grep prefill_messages_file ~/.hermes/config.yaml && echo SET || echo MISSING
```

- If SET: leave it alone and tell the user the existing value — they may want to review it.
- If MISSING: append the line:

```bash
echo 'prefill_messages_file: ~/.hermes/kb-manifest.md' >> ~/.hermes/config.yaml
```

---

## Step 6 — Smoke test

```bash
python3 prolog-executor.py "1 is 1."
```

Expected output:

```json
{"success": true, "bindings": [{}]}
```

Empty bindings `[{}]` means the ground query succeeded. If `success` is `false`, check that `knowledge-base.pl` exists in the current directory.

---

## Done

Tell the user:
- Where the skill was installed (`~/.hermes/skills/prolog-reasoning/`)
- Where the KB lives (current project directory)
- That the manifest is wired into `~/.hermes/config.yaml`
- That they should regenerate the manifest after any KB write: `python3 prolog-executor.py --manifest > ~/.hermes/kb-manifest.md`
