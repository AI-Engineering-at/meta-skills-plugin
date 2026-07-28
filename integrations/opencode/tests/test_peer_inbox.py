"""Unit tests for the role-bound Mattermost inbox helper.

The helper must stay transport-safe: pure filtering and watermark decisions are
tested without a token, vault, or network call.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "peer_inbox.py"
SPEC = importlib.util.spec_from_file_location("peer_inbox", MODULE)
assert SPEC and SPEC.loader
peer_inbox = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(peer_inbox)


def test_select_addressed_posts_delivers_a_message_addressed_to_both_peers():
    posts = [
        {
            "id": "old",
            "create_at": 100,
            "channel_id": "wanted",
            "message": "[vibe -> @brain] old",
        },
        {
            "id": "wrong-role",
            "create_at": 300,
            "channel_id": "wanted",
            "message": "[vibe -> @vibe] private",
        },
        {
            "id": "both",
            "create_at": 300,
            "channel_id": "wanted",
            "message": "[joe -> @brain @vibe] both need to see this",
        },
        {
            "id": "right",
            "create_at": 400,
            "channel_id": "wanted",
            "message": "[vibe -> @brain] please review",
        },
    ]

    selected = peer_inbox.select_addressed_posts(
        posts, role="brain", channel_id="wanted", watermark_ms=100
    )

    assert [post["id"] for post in selected] == ["both", "right"]


def test_select_direct_posts_accepts_only_messages_from_the_configured_user():
    posts = [
        {"id": "self", "create_at": 300, "user_id": "brain-id", "message": "sent"},
        {"id": "other", "create_at": 400, "user_id": "other-id", "message": "ignore"},
        {"id": "joe", "create_at": 500, "user_id": "joe-id", "message": "DM to Brain"},
    ]

    selected = peer_inbox.select_direct_posts(
        posts, sender_id="joe-id", watermark_ms=100
    )

    assert [post["id"] for post in selected] == ["joe"]


def test_initial_watermark_uses_latest_seen_post_without_delivering_history():
    assert peer_inbox.initial_watermark([
        {"create_at": 400}, {"create_at": 900}, {"create_at": 600}
    ]) == 900
    assert peer_inbox.initial_watermark([]) == 0


def test_acknowledge_never_moves_watermark_backwards():
    state = {"watermark_ms": 900}

    updated = peer_inbox.acknowledge(state, 400)

    assert updated["watermark_ms"] == 900


def test_select_team_prefers_requested_member_team_and_falls_back_to_first_member_team():
    teams = [{"id": "one", "name": "other"}, {"id": "two", "name": "ai-engineering"}]

    assert peer_inbox.select_team(teams, "ai-engineering")["id"] == "two"
    assert peer_inbox.select_team(teams, "missing")["id"] == "one"
