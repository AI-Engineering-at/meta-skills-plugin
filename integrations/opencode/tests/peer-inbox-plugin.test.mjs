import assert from "node:assert/strict";
import test from "node:test";

import * as peerInboxModule from "../plugins/peer-inbox.mjs";
import { formatInboundPrompt, watermarksFor } from "../plugins/peer-inbox-lib.mjs";

const PeerInboxPlugin = peerInboxModule.default;

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function waitFor(assertion, timeoutMilliseconds = 250) {
  const deadline = Date.now() + timeoutMilliseconds;
  let lastError;
  while (Date.now() < deadline) {
    try {
      assertion();
      return;
    } catch (error) {
      lastError = error;
      await sleep(5);
    }
  }
  throw lastError;
}

function jsonProcess(result) {
  return {
    exited: Promise.resolve(0),
    stdout: new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(JSON.stringify(result)));
        controller.close();
      },
    }),
  };
}

test("exports exactly one OpenCode plugin entry", () => {
  assert.deepEqual(Object.keys(peerInboxModule), ["default"]);
  assert.equal(typeof peerInboxModule.default, "function");
});

test("formats shared and direct messages as an explicit inbound batch", () => {
  const prompt = formatInboundPrompt("brain", [
    { source: "shared", channel: "team-infra", id: "p1", create_at: 100, message: "[joe -> @brain] status?" },
    { source: "dm", channel: "dm", id: "p2", create_at: 200, message: "private follow-up" },
  ]);

  assert.match(prompt, /INCOMING MATTERMOST MESSAGE/);
  assert.match(prompt, /#team-infra/);
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

test("shows a Mattermost toast after delivering inbound messages", async () => {
  const originalEnvironment = {
    AIE_MM_ROLE: process.env.AIE_MM_ROLE,
    AIE_MM_READ_CHANNEL_NAMES: process.env.AIE_MM_READ_CHANNEL_NAMES,
    AIE_OPENCODE_AGENT: process.env.AIE_OPENCODE_AGENT,
    AIE_MM_INBOX_POLL_SECONDS: process.env.AIE_MM_INBOX_POLL_SECONDS,
  };
  const originalBun = globalThis.Bun;
  const toasts = [];
  const logs = [];
  let pollCalls = 0;
  process.env.AIE_MM_ROLE = "brain";
  process.env.AIE_MM_READ_CHANNEL_NAMES = "team-infra";
  process.env.AIE_OPENCODE_AGENT = "brain";
  process.env.AIE_MM_INBOX_POLL_SECONDS = "60";
  globalThis.Bun = {
    spawn: () => {
      pollCalls += 1;
      return jsonProcess(pollCalls === 1
        ? { ok: true, messages: [{ source: "shared", channel: "team-infra", id: "p1", create_at: 100, message: "status?" }] }
        : { ok: true });
    },
  };
  const client = {
    app: { log: async (input) => logs.push(input) },
    tui: { showToast: async (input) => toasts.push(input) },
    session: { promptAsync: async () => ({}) },
  };

  let plugin;
  try {
    plugin = await PeerInboxPlugin({ client });
    await plugin.event({ event: { type: "session.created", properties: { info: { id: "session-1" } } } });
    await waitFor(() => assert.equal(toasts.length, 1));
    assert.deepEqual(toasts[0], {
      body: {
        title: "Mattermost",
        message: "1 new message delivered to this session",
        variant: "info",
        duration: 7000,
      },
    });
  } finally {
    await plugin?.dispose();
    globalThis.Bun = originalBun;
    for (const [name, value] of Object.entries(originalEnvironment)) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
  }
});

test("shows a generic error toast when inbound delivery fails", async () => {
  const originalEnvironment = {
    AIE_MM_ROLE: process.env.AIE_MM_ROLE,
    AIE_MM_READ_CHANNEL_NAMES: process.env.AIE_MM_READ_CHANNEL_NAMES,
    AIE_OPENCODE_AGENT: process.env.AIE_OPENCODE_AGENT,
    AIE_MM_INBOX_POLL_SECONDS: process.env.AIE_MM_INBOX_POLL_SECONDS,
  };
  const originalBun = globalThis.Bun;
  const toasts = [];
  process.env.AIE_MM_ROLE = "brain";
  process.env.AIE_MM_READ_CHANNEL_NAMES = "team-infra";
  process.env.AIE_OPENCODE_AGENT = "brain";
  process.env.AIE_MM_INBOX_POLL_SECONDS = "60";
  globalThis.Bun = {
    spawn: () => jsonProcess({ ok: false, error_type: "NetworkError" }),
  };
  const client = {
    app: { log: async () => {} },
    tui: { showToast: async (input) => toasts.push(input) },
    session: { promptAsync: async () => ({}) },
  };

  let plugin;
  try {
    plugin = await PeerInboxPlugin({ client });
    await plugin.event({ event: { type: "session.created", properties: { info: { id: "session-1" } } } });
    await waitFor(() => assert.equal(toasts.length, 1));
    assert.deepEqual(toasts[0], {
      body: {
        title: "Mattermost inbox error",
        message: "Inbound delivery failed; details were logged.",
        variant: "error",
        duration: 10000,
      },
    });
  } finally {
    await plugin?.dispose();
    globalThis.Bun = originalBun;
    for (const [name, value] of Object.entries(originalEnvironment)) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
  }
});
