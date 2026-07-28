import assert from "node:assert/strict";
import test from "node:test";

import { formatInboundPrompt, watermarksFor } from "../plugins/peer-inbox.mjs";

test("formats shared and direct messages as an explicit inbound batch", () => {
  const prompt = formatInboundPrompt("brain", [
    { source: "shared", channel: "agent-tasks", id: "p1", create_at: 100, message: "[joe -> @brain] status?" },
    { source: "dm", channel: "dm", id: "p2", create_at: 200, message: "private follow-up" },
  ]);

  assert.match(prompt, /INCOMING MATTERMOST MESSAGE/);
  assert.match(prompt, /#agent-tasks/);
  assert.match(prompt, /Joe DM/);
  assert.match(prompt, /status\?/);
  assert.match(prompt, /private follow-up/);
});

test("produces independent acknowledgement watermarks per source", () => {
  assert.deepEqual(watermarksFor([
    { source: "shared", create_at: 300 },
    { source: "shared", create_at: 100 },
    { source: "dm", create_at: 250 },
  ]), { shared: 300, dm: 250 });
});
