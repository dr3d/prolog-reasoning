#!/usr/bin/env bash
# generate-manifest.sh
# Regenerates the KB manifest file used by Hermes prefill_messages_file.
#
# Usage:
#   ./generate-manifest.sh [kb_path]
#
# Defaults:
#   kb_path — ~/.hermes/knowledge-base.pl (global KB)
#
# Output: JSON written to ~/.hermes/kb-manifest.json by the executor.
# Output format: JSON array of {role, content} dicts required by Hermes:
#   [{"role": "user", "content": "..."}, {"role": "assistant", "content": "Understood..."}]
#
# Add to Hermes config.yaml (must be nested under agent:):
#   agent:
#     prefill_messages_file: ~/.hermes/kb-manifest.json
#
# Call this after any KB write so the manifest stays current.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXECUTOR="$SCRIPT_DIR/../prolog-executor.py"
KB="${1:-}"

# NOTE: do not redirect stdout — the executor writes JSON directly to
# ~/.hermes/kb-manifest.json. Redirecting stdout would overwrite that file
# with plain text, breaking Hermes prefill_messages_file.
if [ -n "$KB" ]; then
    python3 "$EXECUTOR" --manifest -kb "$KB"
else
    python3 "$EXECUTOR" --manifest
fi
