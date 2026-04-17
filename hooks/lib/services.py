"""Shared service clients for Claude Code hooks.

All HTTP calls use urllib (stdlib) — zero external dependencies.
All methods are fail-safe: return empty/None on error, never raise.
Timeout: configurable per client. Health checks use half the client timeout (min 2s).

Usage:
    from lib.services import HonchoClient, OpenNotebookClient, log_error
"""
import contextlib
import json
import logging
import os
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

# --- Structured error log (consolidated with hook_wrapper.py) ---
_ERROR_LOG = Path(os.environ.get(
    "CLAUDE_PLUGIN_DATA",
    Path.home() / ".claude" / "plugins" / "data" / "meta-skills"
)) / "hook-errors.log"

logger = logging.getLogger("hooks")

def log_error(hook_name: str, error: str, context: str = "") -> None:
    """Append structured error to hook-errors.log. Never raises."""
    try:
        _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).isoformat()
        entry = json.dumps({
            "timestamp": ts,
            "hook": hook_name,
            "error": str(error)[:500],
            "context": context[:200],
        }, ensure_ascii=False)
        with _ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")
        # Rotate at 2MB
        if _ERROR_LOG.stat().st_size > 2 * 1024 * 1024:
            rotated = _ERROR_LOG.with_suffix(f".{int(datetime.now(UTC).timestamp())}.log")
            _ERROR_LOG.rename(rotated)
    except Exception:
        pass


def _http_request(
    url: str,
    method: str = "GET",
    body: dict | None = None,
    timeout: float = 5.0,
) -> dict | None:
    """Execute HTTP request. Returns parsed JSON or None on any failure."""
    try:
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            if not raw.strip():
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body_text = ""
        with contextlib.suppress(Exception):
            body_text = e.read().decode("utf-8", errors="replace")[:200]
        log_error("http", f"HTTP {e.code} {method} {url}: {body_text}", url)
        return None
    except urllib.error.URLError as e:
        log_error("http", f"URLError {method} {url}: {e.reason}", url)
        return None
    except Exception as e:
        log_error("http", f"Exception {method} {url}: {e}", url)
        return None


# ---------------------------------------------------------------------------
# Vault Reader
# ---------------------------------------------------------------------------

_VAULT_SCRIPT = Path.home() / "Documents" / "phantom-ai" / ".claude" / "credentials" / "vault.py"

def vault_get(agent: str, service: str, key: str) -> str | None:
    """Read a value from vault.py. Returns None on failure."""
    if not _VAULT_SCRIPT.exists():
        return None
    try:
        result = subprocess.run(
            ["python3", str(_VAULT_SCRIPT), "get", agent, service, key],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        log_error("vault", f"vault.py get {agent} {service} {key}: {e}")
    return None


# ---------------------------------------------------------------------------
# Honcho Client
# ---------------------------------------------------------------------------

class HonchoClient:
    """Fail-safe Honcho v3 API client.

    All methods return empty defaults on failure, never raise.
    """

    def __init__(self, timeout: float = 5.0):
        self._timeout = timeout
        self._base_url = vault_get("shared", "honcho", "HONCHO_URL") or "http://honcho.local:8055"
        self._workspace = vault_get("shared", "honcho", "WORKSPACE_ID") or "ai-engineering"
        self._base_url = self._base_url.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self._base_url}/v3/workspaces/{self._workspace}{path}"

    def is_healthy(self) -> bool:
        """Quick connectivity check (GET workspace, expect 405 = alive).

        Uses half the client timeout (min 2s) for fast fail detection.
        """
        health_timeout = max(2.0, self._timeout / 2)
        try:
            req = urllib.request.Request(self._url(""), method="GET")
            urllib.request.urlopen(req, timeout=health_timeout)
            return True
        except urllib.error.HTTPError as e:
            # 405 Method Not Allowed = server is alive, just wrong method
            return e.code in (200, 405)
        except Exception:
            return False

    def search_peer(self, peer_id: str, query: str, limit: int = 5) -> list:
        """Search messages for a peer. Returns list of content strings.

        Search uses full client timeout — embedding queries can take 5-10s.
        """
        result = _http_request(
            self._url(f"/peers/{peer_id}/search"),
            method="POST",
            body={"query": query, "limit": limit},
            timeout=self._timeout,
        )
        if not result or not isinstance(result, list):
            return []
        contents = []
        for item in result:
            content = item.get("content", "")
            # Parse JSON content (audit_logger stores JSON strings)
            if content.startswith("{"):
                try:
                    parsed = json.loads(content)
                    # Prefer human-readable summary over raw JSON
                    content = parsed.get("summary", parsed.get("input_summary", content))
                except (json.JSONDecodeError, ValueError):
                    pass
            if content and len(content) > 10:
                contents.append(content[:300])
        return contents

    def get_peer_context(self, peer_id: str) -> str:
        """Get derived context for a peer. Returns empty string on failure."""
        result = _http_request(
            self._url(f"/peers/{peer_id}/context"),
            method="GET",
            timeout=self._timeout,
        )
        if not result:
            return ""
        # Context can be a string or dict with content field
        if isinstance(result, str):
            return result[:1000]
        return str(result.get("content", result.get("context", "")))[:1000]

    def create_session(self, session_id: str, peer_id: str, metadata: dict | None = None) -> bool:
        """Create or resume a session. Returns True on success."""
        # Sanitize session_id for Honcho (alphanumeric, hyphens, underscores only)
        clean_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        if not clean_id:
            clean_id = "unknown"
        result = _http_request(
            self._url("/sessions"),
            method="POST",
            body={
                "id": clean_id,
                "metadata": metadata or {},
                "peers": {peer_id: {}},
            },
            timeout=self._timeout,
        )
        return result is not None

    def add_message(self, session_id: str, peer_id: str, content: str) -> bool:
        """Add a message to a session. Returns True on success."""
        clean_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        if not clean_id:
            clean_id = "unknown"
        result = _http_request(
            self._url(f"/sessions/{clean_id}/messages"),
            method="POST",
            body={
                "messages": [{
                    "content": content[:25000],  # Honcho max
                    "peer_id": peer_id,
                }]
            },
            timeout=self._timeout,
        )
        return result is not None


# ---------------------------------------------------------------------------
# open-notebook Client
# ---------------------------------------------------------------------------

class OpenNotebookClient:
    """Fail-safe open-notebook API client.

    Uses text search (no LLM models required) for hook-speed queries.
    """

    NOTEBOOK_ID = "notebook:zkxy9fiwelrolgbr2upc"

    def __init__(self, timeout: float = 5.0):
        self._timeout = timeout
        self._base_url = (
            vault_get("_shared", "open-notebook", "OPEN_NOTEBOOK_API")
            or "http://open-notebook.local:5055"
        ).rstrip("/")

    def is_healthy(self) -> bool:
        """Quick connectivity check. Uses half client timeout (min 2s)."""
        health_timeout = max(2.0, self._timeout / 2)
        result = _http_request(
            f"{self._base_url}/api/config",
            method="GET",
            timeout=health_timeout,
        )
        return result is not None

    def search_text(self, query: str, limit: int = 5) -> list:
        """Full-text search across sources and notes.

        Returns list of dicts with 'title' and 'relevance'.
        Uses text search (no embedding model needed, instant).
        """
        result = _http_request(
            f"{self._base_url}/api/search",
            method="POST",
            body={
                "query": query,
                "type": "text",
                "limit": limit,
                "search_sources": True,
                "search_notes": True,
            },
            timeout=self._timeout,
        )
        if not result or not isinstance(result, dict):
            return []
        return result.get("results", [])

    def create_source(self, title: str, content: str, embed: bool = True) -> bool:
        """Create a text source in the AI Engineering KB.

        Returns True on success.
        """
        result = _http_request(
            f"{self._base_url}/api/sources/json",
            method="POST",
            body={
                "type": "text",
                "title": title,
                "content": content[:50000],
                "notebooks": [self.NOTEBOOK_ID],
                "embed": embed,
                "async_processing": True,
            },
            timeout=self._timeout,
        )
        return result is not None


# ---------------------------------------------------------------------------
# Project Detection
# ---------------------------------------------------------------------------

def detect_peer_id(cwd: str | None = None) -> str:
    """Determine Honcho peer_id from working directory."""
    cwd = cwd or str(Path.cwd())
    cwd_lower = cwd.lower().replace("\\", "/")
    if "phantom-ai" in cwd_lower:
        return "claude-phi"
    if "playbook01" in cwd_lower or "playbook" in cwd_lower:
        return "claude-pb"
    return "claude-hq"


def detect_project_name(cwd: str | None = None) -> str:
    """Extract project name from working directory."""
    cwd = cwd or str(Path.cwd())
    parts = cwd.replace("\\", "/").split("/")
    # Find the project directory (after Documents/)
    for i, part in enumerate(parts):
        if part.lower() == "documents" and i + 1 < len(parts):
            return parts[i + 1]
    return parts[-1] if parts else "unknown"


def get_git_changes_summary(max_lines: int = 20) -> str:
    """Get a summary of git changes in the current session.

    Uses git diff --stat and recent commits. Returns empty string on failure.
    """
    lines = []
    try:
        # Uncommitted changes
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=str(Path.cwd()),
        )
        if result.returncode == 0 and result.stdout.strip():
            lines.append("Uncommitted changes:")
            for line in result.stdout.strip().split("\n")[:max_lines]:
                lines.append(f"  {line}")

        # Last 5 commits from today
        today = datetime.now().strftime("%Y-%m-%d")
        result = subprocess.run(
            ["git", "log", "--oneline", f"--since={today}", "--max-count=5"],
            capture_output=True, text=True, timeout=5,
            cwd=str(Path.cwd()),
        )
        if result.returncode == 0 and result.stdout.strip():
            lines.append("Today's commits:")
            for line in result.stdout.strip().split("\n"):
                lines.append(f"  {line}")
    except Exception as e:
        log_error("git", f"get_git_changes_summary: {e}")

    return "\n".join(lines)
