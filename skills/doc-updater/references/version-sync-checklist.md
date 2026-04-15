# Version Sync Checklist — Field-by-Field Map

Every version string location across the project. Use `grep` to find and update.

## Primary (MUST update on every version bump)

| File | Field | grep Pattern | Example |
|------|-------|-------------|---------|
| `pyproject.toml` | version | `version = "` | `version = "2.0.0"` |
| `CLAUDE.md` | Status line | `LIVE v` | `LIVE v2.0.0` |
| `CLAUDE.md` | Arch diagram | `AI PRODUCTIVITY STACK v` | `v2.0.0` |
| `CLAUDE.md` | Service table VG | `voice-gateway.*RUNNING` | `2.0.0` |
| `CLAUDE.md` | VG tree header | `v[0-9]\.` | `(v2.0.0)` |
| `CLAUDE.md` | Deploy commands | `voice-gateway:[0-9]\.` | `:2.0.0` |
| `CLAUDE.md` | Footer | `v[0-9]\..* LIVE` | `v2.0.0 LIVE` |
| `voice-gateway/main.py` | /health | `"version":` | `"2.0.0"` |
| `voice-gateway/agent.md` | header | `Version.*:` | `2.0.0` |

## Secondary (update on version bump)

| File | Field | grep Pattern |
|------|-------|-------------|
| `INDEX.md` | header | `Version.*:` |
| `README.md` | badge stack | `badge/stack-` |
| `README.md` | badge VG | `badge/voice_gateway-` |
| `docs/VERSION-MATRIX.md` | header | `Phantom-AI v` |
| `docs/VERSION-MATRIX.md` | VG row | `Voice Gateway.*Production` |
| `docs/CURRENT.md` | header | `Version.*:` |

## Count Fields (update when plugins/tests change)

| File | Field | Verification Command |
|------|-------|---------------------|
| `CLAUDE.md` | Plugin count | `ls -d voice-gateway/plugins/*/` |
| `CLAUDE.md` | Tool count | `grep -c "  - name:" voice-gateway/plugins/*/plugin.yaml` |
| `CLAUDE.md` | Test file count | `ls voice-gateway/tests/test_*.py \| wc -l` |
| `CLAUDE.md` | Test function count | `grep -c "def test_" voice-gateway/tests/test_*.py` |
| `INDEX.md` | Plugin Registry table | Same as above |
| `INDEX.md` | Test Registry table | Same as above |
| `README.md` | Feature line | Same as above |

## Path Fields (should always be /opt/phantom-ai/)

| File | Old | New |
|------|-----|-----|
| `CLAUDE.md` deploy section | `/root/ai-stack/` | `/opt/phantom-ai/` |
| `scripts/deploy-voice-gateway.sh` | Check DEPLOY_DIR | `/opt/phantom-ai/` |
