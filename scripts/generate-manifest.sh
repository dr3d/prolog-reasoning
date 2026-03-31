#!/usr/bin/env bash
# generate-manifest.sh
# Regenerates the KB manifest file used by Hermes prefill_messages_file.
#
# Usage:
#   ./generate-manifest.sh [kb_path] [output_path]
#
# Defaults:
#   kb_path     — knowledge-base.pl next to the executor
#   output_path — ~/.hermes/kb-manifest.md
#
# Add to Hermes config:
#   prefill_messages_file: /Users/you/.hermes/kb-manifest.md
#
# Call this after any KB write so the manifest stays current.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXECUTOR="$SCRIPT_DIR/../prolog-executor.py"
KB="${1:-}"
OUTPUT="${2:-$HOME/.hermes/kb-manifest.md}"

if [ -n "$KB" ]; then
    python3 "$EXECUTOR" --manifest "$KB" > "$OUTPUT"
else
    python3 "$EXECUTOR" --manifest > "$OUTPUT"
fi

echo "Manifest written to $OUTPUT"
