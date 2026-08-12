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


def test_select_direct_posts_accepts_joe_and_the_other_peer_only():
    posts = [
        {"id": "self", "create_at": 300, "user_id": "brain-id", "message": "sent"},
        {"id": "other", "create_at": 400, "user_id": "other-id", "message": "ignore"},
        {"id": "joe", "create_at": 500, "user_id": "joe-id", "message": "DM to Brain"},
        {"id": "peer", "create_at": 600, "user_id": "vibe-id", "message": "Peer DM"},
    ]

    selected = peer_inbox.select_direct_posts(
        posts, sender_ids={"joe-id", "vibe-id"}, watermark_ms=100
    )

    assert [post["id"] for post in selected] == ["joe", "peer"]


def test_allowed_dm_users_includes_joe_and_the_other_peer():
    assert peer_inbox.allowed_dm_users("brain") == ("joe", "vibe")
    assert peer_inbox.allowed_dm_users("vibe") == ("joe", "brain")
    assert peer_inbox.allowed_dm_users("ocode-kimi") == ("joe", "brain")
    assert peer_inbox.allowed_dm_users("ocode-pruefer") == ("joe", "brain")


def test_runtime_roles_and_channels_are_exactly_the_ocode_team_contract():
    assert peer_inbox.VALID_ROLES == frozenset(
        {"brain", "vibe", "ocode-kimi", "ocode-pruefer"}
    )
    assert peer_inbox.VALID_CHANNELS == frozenset(
        {"team-infra", "town-square", "ocode-team"}
    )


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


def test_select_addressed_posts_accepts_bare_leading_mention_for_human_sender():
    posts = [
        {
            "id": "bare",
            "create_at": 200,
            "channel_id": "wanted",
            "message": "@brain staus ? wo stehen wir ?",
        },
        {
            "id": "mid-sentence",
            "create_at": 300,
            "channel_id": "wanted",
            "message": "gib es @brain bitte",
        },
        {
            "id": "no-mention",
            "create_at": 400,
            "channel_id": "wanted",
            "message": "protokoll vom standup",
        },
    ]

    selected = peer_inbox.select_addressed_posts(
        posts, role="brain", channel_id="wanted", watermark_ms=100
    )

    assert [post["id"] for post in selected] == ["bare"]
