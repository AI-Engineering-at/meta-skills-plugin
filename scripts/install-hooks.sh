#!/usr/bin/env bash
# Install local git hooks for meta-skills-plugin contributors.
#
# Usage: bash scripts/install-hooks.sh
#
# Installs:
#   .git/hooks/pre-commit  — blocks PII (absolute paths, internal IPs)
#                            and reminds about test runs.
set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
    echo "ERROR: not in a git repo"
    exit 1
fi

HOOK_FILE="$REPO_ROOT/.git/hooks/pre-commit"

cat > "$HOOK_FILE" <<'HOOK_EOF'
#!/usr/bin/env bash
# Pre-commit hook for meta-skills-plugin.
# Auto-installed by scripts/install-hooks.sh.
#
# Blocks staged changes that contain:
#   - absolute Windows user paths (C:/Users/<name>/, C:\Users\<name>\)
#   - absolute Linux user paths (/home/<user>/, /Users/<user>/)
#   - internal RFC1918 IPs (10.40.10.x range used by maintainer)
#
# Bypass with `git commit --no-verify` (use sparingly; intentional only).

set -e

# Files to check: only staged + only text files
mapfile -t STAGED < <(git diff --cached --name-only --diff-filter=ACMR)
if [ "${#STAGED[@]}" -eq 0 ]; then
    exit 0
fi

declare -a OFFENDERS
PATTERNS=(
    'C:[/\\]+Users[/\\]+[A-Za-z0-9._-]+'
    '/home/[a-z][a-z0-9_-]+/'
    '/Users/[A-Za-z][A-Za-z0-9._-]+/'
    '\b10\.40\.10\.[0-9]+\b'
)

for f in "${STAGED[@]}"; do
    # Skip binaries and known-allowed reference files
    case "$f" in
        *.png|*.jpg|*.jpeg|*.gif|*.pdf|*.zip|*.tar.gz) continue ;;
        skills/creator/references/export-process.md) continue ;;
    esac
    [ -f "$f" ] || continue

    for pat in "${PATTERNS[@]}"; do
        if git diff --cached -- "$f" | grep -E "^\+" | grep -E "$pat" > /dev/null 2>&1; then
            line=$(git diff --cached -- "$f" | grep -E "^\+" | grep -E "$pat" | head -1)
            OFFENDERS+=("  $f: $line")
        fi
    done
done

if [ "${#OFFENDERS[@]}" -gt 0 ]; then
    echo "PRE-COMMIT BLOCKED: PII / env-specific data detected in staged changes:"
    for o in "${OFFENDERS[@]}"; do
        echo "$o"
    done
    echo ""
    echo "Sanitize before commit, or use \`git commit --no-verify\` if intentional."
    exit 1
fi

exit 0
HOOK_EOF

chmod +x "$HOOK_FILE"
echo "Installed: $HOOK_FILE"
echo "Test it: git commit -m 'test' (with a file containing an absolute user path in staged diff)"
