#!/usr/bin/env bash
# generate-manifest.sh
# Regenerates the KB manifest file used by Hermes prefill_messages_file.
#
# Usage:
#   ./generate-manifest.sh [kb_path] [output_path]
#
# Defaults:
#   kb_path     — knowledge-base.pl next to the executor
#   output_path — ~/.hermes/kb-manifest.json
#
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
OUTPUT="${2:-$HOME/.hermes/kb-manifest.json}"

if [ -n "$KB" ]; then
    python3 "$EXECUTOR" --manifest -kb "$KB" > "$OUTPUT"
else
    python3 "$EXECUTOR" --manifest > "$OUTPUT"
fi

echo "Manifest written to $OUTPUT"
