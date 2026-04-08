#!/usr/bin/env bash
# Collect session metrics after each Claude response.
# Lightweight: ~50ms, no LLM call.
# Appends to ${CLAUDE_PLUGIN_DATA}/session-metrics.jsonl
# Includes skill_sequence field for v2.0 meta:flow preparation.

set -euo pipefail

DATA_DIR="${CLAUDE_PLUGIN_DATA:-${HOME}/.claude/plugins/data/meta-skills}"
mkdir -p "$DATA_DIR"

METRICS_FILE="$DATA_DIR/session-metrics.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

# Read stdin (Stop event JSON) — may be empty
EVENT=$(cat 2>/dev/null || echo "{}")

# Extract session ID if available
SESSION_ID=$(echo "$EVENT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('session_id', d.get('sessionId', 'unknown')))
except:
    print('unknown')
" 2>/dev/null || echo "unknown")

# Append metric line
# skill_sequence: empty array, populated by future v0.3+ analysis
echo "{\"timestamp\":\"$TIMESTAMP\",\"session\":\"$SESSION_ID\",\"event\":\"stop\",\"skill_sequence\":[]}" >> "$METRICS_FILE"
