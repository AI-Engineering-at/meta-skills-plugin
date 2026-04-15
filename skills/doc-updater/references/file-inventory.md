# File Inventory — Expected Counts for Validation

Use these expected counts to detect when files are added or removed.

## Voice Gateway Plugins

**Expected: 9 directories**

| Plugin | Expected Tools |
|--------|---------------|
| system | 3 (get_system_status, get_docker_status, get_stack_audit) |
| web | 2 (web_fetch, web_search) |
| mattermost | 2 (mattermost_send, mattermost_read) |
| cli_bridges | 4 (delegate_to_copilot, delegate_to_gemini, delegate_to_codex, check_bridge_result) |
| file | 2 (file_read, file_list) |
| knowledge | 3 (knowledge_search, summarize_text, knowledge_write) |
| docker_mcp | 5 (docker_service_logs, docker_service_inspect, docker_node_info, docker_image_list, docker_service_scale) |
| fetch_mcp | 3 (http_request, http_health_check, http_json_query) |
| scheduler | 3 (schedule_task, list_scheduled, cancel_task) |

**Total expected tools: 27**

## Test Files

**Expected: 32 files, ~234 test functions**

Check: `ls voice-gateway/tests/test_*.py | wc -l`
Check: `grep -c "def test_" voice-gateway/tests/test_*.py | awk -F: '{s+=$2} END {print s}'`

## Claude Code Config

**Expected:**
- 4 commands in `.claude/commands/`
- 3 skills in `.claude/skills/` (pve-operations, swarm-recovery, doc-updater)
- 3+ agent profiles in `.github/agents/`

## Scripts

**Expected: 18+ files in `scripts/`**
- 1 CLI bridge subdirectory (`cli_bridge/`)
- 3 PowerShell launchers (`.ps1`)
- Remaining: Shell + Python scripts

## Key Directories

| Directory | Expected Subdirs |
|-----------|-----------------|
| `voice-gateway/` | services, channels, memory, context, sessions, tools, plugins, persona, middleware, monitoring, ops, feature_flags, evaluation, training, tests |
| `docs/` | operations, planning, audits, diagrams, echo-log, ops |
| `monitoring/` | (flat, 7+ config files) |
| `codex-prep*/` | 4 rounds: codex-prep, codex-prep-r2, codex-prep-r3, codex-prep-r4 |
