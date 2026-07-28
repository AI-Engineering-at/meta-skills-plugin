/**
 * OpenCode-local Mattermost inbox.
 *
 * The plugin runs only while OpenCode runs. It delegates vault-backed Mattermost
 * access and durable watermarks to ../peer_inbox.py, then injects accepted input
 * into the active role-matching session with the official promptAsync API.
 */

const VALID_ROLES = new Set(["brain", "vibe"]);
const VALID_CHANNELS = new Set(["agent-tasks", "town-square"]);
const MAX_BATCH = 20;

export function watermarksFor(messages) {
  const watermarks = {};
  for (const message of messages) {
    const timestamp = Number(message.create_at || 0);
    if (!Number.isFinite(timestamp) || timestamp <= 0) continue;
    watermarks[message.source] = Math.max(watermarks[message.source] || 0, timestamp);
  }
  return watermarks;
}

export function formatInboundPrompt(role, messages) {
  const entries = messages.map((message) => {
    const source = message.source === "dm" ? "Joe DM" : `#${message.channel}`;
    return `### ${source} · ${message.id}\n${message.message}`;
  });
  return [
    "## INCOMING MATTERMOST MESSAGE",
    `You are the ${role} peer. These messages arrived after the current session started.`,
    "Treat them as real peer input. Follow peer-comms: verify relevant state, reply through the configured Mattermost MCP if a reply is required, and put durable decisions/evidence in Gitea.",
    "Do not fetch, print, or ask for credentials. Do not claim that a delivery occurred without a Mattermost receipt.",
    "",
    ...entries,
  ].join("\n");
}

function runtimeConfig() {
  const role = process.env.AIE_MM_ROLE;
  const channel = process.env.AIE_MM_READ_CHANNEL_NAMES;
  const agent = process.env.AIE_OPENCODE_AGENT;
  if (!VALID_ROLES.has(role) || !VALID_CHANNELS.has(channel) || agent !== role) return null;
  const seconds = Math.max(5, Math.min(60, Number(process.env.AIE_MM_INBOX_POLL_SECONDS || 10)));
  return { role, channel, agent, intervalMs: seconds * 1000 };
}

function helperCommand(config, action, watermarks = {}) {
  const helper = new URL("../peer_inbox.py", import.meta.url).pathname;
  const python = process.env.AIE_MM_INBOX_PYTHON || "/Users/mackbook/code-aie/aie-mm-mcp/.venv/bin/python";
  const command = [python, helper, action, "--role", config.role, "--channel", config.channel];
  if (watermarks.shared) command.push("--shared-watermark", String(watermarks.shared));
  if (watermarks.dm) command.push("--dm-watermark", String(watermarks.dm));
  return command;
}

async function invokeHelper(config, action, watermarks) {
  const processHandle = Bun.spawn(helperCommand(config, action, watermarks), {
    stdout: "pipe",
    stderr: "pipe",
    env: process.env,
  });
  const [exitCode, stdout] = await Promise.all([
    processHandle.exited,
    new Response(processHandle.stdout).text(),
  ]);
  let result;
  try {
    result = JSON.parse(stdout);
  } catch {
    throw new Error(`peer inbox returned non-JSON (exit ${exitCode})`);
  }
  if (exitCode !== 0 || !result.ok) {
    throw new Error(`peer inbox ${action} failed: ${result.error_type || "unknown"}`);
  }
  return result;
}

async function log(client, level, message, extra = {}) {
  await client.app.log({ body: { service: "aie-peer-inbox", level, message, extra } });
}

export const PeerInboxPlugin = async ({ client }) => {
  const config = runtimeConfig();
  if (!config) {
    await log(client, "warn", "peer inbox disabled: launcher role, agent, or channel is missing/invalid");
    return {};
  }

  let activeSessionID = null;
  let sessionStatus = "idle";
  let polling = false;

  const poll = async () => {
    if (polling || !activeSessionID || sessionStatus !== "idle") return;
    polling = true;
    const targetSessionID = activeSessionID;
    try {
      const inbox = await invokeHelper(config, "poll");
      if (inbox.initialized || !Array.isArray(inbox.messages) || inbox.messages.length === 0) return;
      if (targetSessionID !== activeSessionID || sessionStatus !== "idle") return;

      const batch = inbox.messages.slice(0, MAX_BATCH);
      const result = await client.session.promptAsync({
        path: { id: targetSessionID },
        body: { agent: config.agent, parts: [{ type: "text", text: formatInboundPrompt(config.role, batch) }] },
      });
      if (result.error) throw new Error("OpenCode rejected inbound prompt");
      sessionStatus = "busy";
      await invokeHelper(config, "ack", watermarksFor(batch));
      await log(client, "info", "peer inbox delivered messages", {
        role: config.role,
        channel: config.channel,
        sessionID: targetSessionID,
        count: batch.length,
        sources: [...new Set(batch.map((item) => item.source))],
      });
    } catch (error) {
      await log(client, "error", "peer inbox poll/delivery failed", {
        role: config.role,
        channel: config.channel,
        error: error instanceof Error ? error.message : String(error),
      });
    } finally {
      polling = false;
    }
  };

  const schedulePoll = () => { void poll(); };
  const timer = setInterval(schedulePoll, config.intervalMs);
  await log(client, "info", "peer inbox initialized", { role: config.role, channel: config.channel });

  return {
    event: async ({ event }) => {
      if (event.type === "session.created") {
        activeSessionID = event.properties.info.id;
        sessionStatus = "idle";
        schedulePoll();
      } else if (event.type === "session.deleted" && event.properties.info.id === activeSessionID) {
        activeSessionID = null;
      } else if (event.type === "session.status" && event.properties.sessionID === activeSessionID) {
        sessionStatus = event.properties.status.type;
        if (sessionStatus === "idle") schedulePoll();
      } else if (event.type === "session.idle" && event.properties.sessionID === activeSessionID) {
        sessionStatus = "idle";
        schedulePoll();
      }
    },
    "chat.message": async (input) => {
      if (input.agent && input.agent !== config.agent) return;
      activeSessionID = input.sessionID;
      sessionStatus = "busy";
    },
    dispose: async () => clearInterval(timer),
  };
};
