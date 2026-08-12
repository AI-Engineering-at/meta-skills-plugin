#!/usr/bin/env python3
"""Role-bound Mattermost inbox for the OpenCode peer plugin.

This helper never prints a credential. It resolves the selected role through the
existing aie-mm-mcp vault path, returns only newly addressed messages, and stores
per-role/per-channel watermarks under ~/.aie/opencode-peer-inbox/.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


VALID_ROLES = frozenset({"brain", "vibe", "ocode-kimi", "ocode-pruefer"})
# 2026-08-02 (TASK-2026-00968): `agent-tasks` raus — der Kanal existierte nie.
# Gemessen gegen 10 von 10 Kanaelen (3 oeffentlich + 7 privat + 0 archiviert):
# kein Treffer. Kritisch fuer diese Datei: `search_posts("in:agent-tasks")` in
# _fetch() liefert HTTP 200 mit order=0 — identisch zu einem existierenden, aber
# ruhigen Kanal. Der Posteingang meldete deshalb dauerhaft {"ok": true,
# "messages": []} statt eines Fehlers. Ein nicht existierender Kanal darf hier
# gar nicht erst waehlbar sein.
VALID_CHANNELS = frozenset({"team-infra", "town-square", "ocode-team"})
STATE_ROOT = Path.home() / ".aie" / "opencode-peer-inbox"
_BRACKET_RE = re.compile(r"^\[(?P<sender>[^\]]+)\]")
_ARROW_RE = re.compile(r"\s*(?:->|→)\s*")
_MENTION_RE = re.compile(r"@([A-Za-z][\w.-]*)")


def _require_supported(role: str, channel: str) -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"unsupported role: {role}")
    if channel not in VALID_CHANNELS:
        raise ValueError(f"unsupported channel: {channel}")


def _recipients(message: str) -> list[str]:
    """Return explicit recipients from the peer address prefix, or an empty list.

    Two accepted forms (2026-08-13):
    - canonical peer form: ``[sender -> @role ...]`` (used by agents and tests), and
    - bare leading mention: ``@role ...`` at the start of the message (human
      sender). A mention in the middle of a sentence is NOT an address, so
      ``gib es @brain bitte`` stays undelivered on purpose.
    """
    text = message.lstrip()
    match = _BRACKET_RE.match(text)
    if not match:
        leading = _MENTION_RE.match(text)
        return [leading.group(1).lower()] if leading else []
    inner = match.group("sender")
    parts = _ARROW_RE.split(inner, maxsplit=1)
    if len(parts) == 2:
        return [token.lower() for token in _MENTION_RE.findall(parts[1])]
    return [token.lower() for token in _MENTION_RE.findall(message)]


def select_addressed_posts(
    posts: list[dict[str, Any]], *, role: str, channel_id: str, watermark_ms: int
) -> list[dict[str, Any]]:
    """Pure shared-channel filter: newer, selected channel, addressed role only."""
    selected = []
    for post in posts:
        if int(post.get("create_at", 0) or 0) <= watermark_ms:
            continue
        if post.get("channel_id") != channel_id:
            continue
        if role not in _recipients(str(post.get("message", ""))):
            continue
        selected.append(post)
    return sorted(selected, key=lambda post: (int(post.get("create_at", 0)), str(post.get("id", ""))))


def select_direct_posts(
    posts: list[dict[str, Any]], *, sender_ids: set[str], watermark_ms: int
) -> list[dict[str, Any]]:
    """Pure DM filter: only newer messages written by an allowed counterpart."""
    selected = [
        post for post in posts
        if int(post.get("create_at", 0) or 0) > watermark_ms
        and post.get("user_id") in sender_ids
    ]
    return sorted(selected, key=lambda post: (int(post.get("create_at", 0)), str(post.get("id", ""))))


def initial_watermark(posts: list[dict[str, Any]]) -> int:
    return max([0] + [int(post.get("create_at", 0) or 0) for post in posts])


def allowed_dm_users(role: str) -> tuple[str, str]:
    _require_supported(role, "team-infra")
    return ("joe", "vibe") if role == "brain" else ("joe", "brain")


def select_team(teams: list[dict[str, Any]], requested_name: str) -> dict[str, Any]:
    if not teams:
        raise RuntimeError("Mattermost identity has no visible teams")
    return next((team for team in teams if team.get("name") == requested_name), teams[0])


def acknowledge(state: dict[str, Any], watermark_ms: int) -> dict[str, Any]:
    updated = dict(state)
    updated["watermark_ms"] = max(int(updated.get("watermark_ms", 0) or 0), int(watermark_ms))
    return updated


def _state_path(role: str, channel: str) -> Path:
    return STATE_ROOT / f"{role}-{channel}.json"


def _load_state(role: str, channel: str) -> dict[str, Any] | None:
    path = _state_path(role, channel)
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("role") != role or value.get("channel") != channel:
        raise ValueError(f"invalid inbox state: {path}")
    value.setdefault("shared", {"watermark_ms": 0})
    value.setdefault("dm", {"watermark_ms": 0})
    return value


def _save_state(role: str, channel: str, state: dict[str, Any]) -> None:
    STATE_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = _state_path(role, channel)
    payload = dict(state)
    payload.update({"role": role, "channel": channel, "updated_at": datetime.now(timezone.utc).isoformat()})
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=STATE_ROOT, prefix=f".{path.name}.", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.chmod(0o600)
    temporary.replace(path)


def _mm_modules():
    source = Path.home() / "code-aie" / "aie-mm-mcp" / "src"
    if not source.is_dir():
        raise RuntimeError(f"aie-mm-mcp source unavailable: {source}")
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from aie_mm_mcp import client, security  # type: ignore
    return client, security


async def _fetch(role: str, channel: str, state: dict[str, Any] | None) -> dict[str, Any]:
    client_mod, security_mod = _mm_modules()
    import httpx

    token = security_mod.resolve_token(role=role)
    base_url = security_mod.validate_base_url(security_mod.DEFAULT_BASE_URL)
    shared_watermark = int((state or {}).get("shared", {}).get("watermark_ms", 0) or 0)
    dm_watermark = int((state or {}).get("dm", {}).get("watermark_ms", 0) or 0)
    # Search syntax is date-granular. Query the preceding UTC day and filter precisely
    # against the millisecond watermark below.
    since = max(shared_watermark, dm_watermark)
    after = datetime.fromtimestamp(since / 1000, timezone.utc).date() - timedelta(days=1) if since else datetime.now(timezone.utc).date() - timedelta(days=1)

    async with httpx.AsyncClient() as http:
        mm = client_mod.MMClient(base_url, token.value, client=http)
        teams = await mm.list_teams_for_me()
        team = select_team(teams, os.environ.get("AIE_MM_TEAM_SLUG", "ai-engineering"))
        shared_page = await mm.search_posts(team["id"], f"in:{channel} after:{after.isoformat()}", per_page=200)
        shared_raw = [
            shared_page["posts"][post_id]
            for post_id in shared_page.get("order", [])
            if post_id in shared_page.get("posts", {})
        ]

        me = await mm.whoami()
        counterparts = [await mm.get_user(username) for username in allowed_dm_users(role)]
        dms = await mm.list_dm_channels(me["id"])
        dm_raw: list[dict[str, Any]] = []
        for counterpart in counterparts:
            participants = {me["id"], counterpart["id"]}
            dm_channel = next(
                (item for item in dms if participants.issubset(set(str(item.get("name", "")).split("__")))),
                None,
            )
            if dm_channel:
                dm_page = await mm.get_channel_posts(
                    dm_channel["id"], per_page=200, since=dm_watermark or None
                )
                dm_raw.extend(
                    dm_page["posts"][post_id]
                    for post_id in dm_page.get("order", [])
                    if post_id in dm_page.get("posts", {})
                )

    if state is None:
        # Baseline on first attachment: historic peer traffic must not be replayed as a new
        # request. Posts created after this server-side read remain newer than the baseline.
        baseline = int(time.time() * 1000)
        return {
            "initialized": True,
            "state": {"shared": {"watermark_ms": baseline}, "dm": {"watermark_ms": baseline}},
            "messages": [],
        }

    channel_ids = {post.get("channel_id") for post in shared_raw if post.get("channel_id")}
    if len(channel_ids) > 1:
        raise RuntimeError("shared search returned multiple channel ids")
    shared_selected = select_addressed_posts(
        shared_raw,
        role=role,
        channel_id=next(iter(channel_ids), ""),
        watermark_ms=shared_watermark,
    )
    dm_selected = select_direct_posts(
        dm_raw,
        sender_ids={counterpart["id"] for counterpart in counterparts},
        watermark_ms=dm_watermark,
    )
    messages = [
        {"source": "shared", "channel": channel, "id": post.get("id"), "create_at": post.get("create_at"), "message": post.get("message", "")}
        for post in shared_selected
    ] + [
        {"source": "dm", "channel": "dm", "id": post.get("id"), "create_at": post.get("create_at"), "message": post.get("message", "")}
        for post in dm_selected
    ]
    messages.sort(key=lambda item: (int(item.get("create_at", 0) or 0), str(item.get("id", ""))))
    return {"initialized": False, "messages": messages}


def _poll(role: str, channel: str) -> dict[str, Any]:
    _require_supported(role, channel)
    state = _load_state(role, channel)
    result = asyncio.run(_fetch(role, channel, state))
    if result["initialized"]:
        _save_state(role, channel, result["state"])
    return {"ok": True, **result}


def _ack(role: str, channel: str, shared_watermark: int | None, dm_watermark: int | None) -> dict[str, Any]:
    _require_supported(role, channel)
    state = _load_state(role, channel)
    if state is None:
        raise ValueError("inbox has not been initialized")
    if shared_watermark is not None:
        state["shared"] = acknowledge(state["shared"], shared_watermark)
    if dm_watermark is not None:
        state["dm"] = acknowledge(state["dm"], dm_watermark)
    _save_state(role, channel, state)
    return {"ok": True, "shared_watermark": state["shared"]["watermark_ms"], "dm_watermark": state["dm"]["watermark_ms"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenCode role-bound Mattermost inbox")
    parser.add_argument("action", choices=("poll", "ack"))
    parser.add_argument("--role", required=True, choices=sorted(VALID_ROLES))
    parser.add_argument("--channel", required=True, choices=sorted(VALID_CHANNELS))
    parser.add_argument("--shared-watermark", type=int)
    parser.add_argument("--dm-watermark", type=int)
    args = parser.parse_args(argv)
    try:
        result = _poll(args.role, args.channel) if args.action == "poll" else _ack(
            args.role, args.channel, args.shared_watermark, args.dm_watermark
        )
    except Exception as error:
        result = {"ok": False, "error_type": type(error).__name__, "error": str(error)}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
