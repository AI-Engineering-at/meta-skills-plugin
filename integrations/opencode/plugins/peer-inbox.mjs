/**
 * OpenCode-local Mattermost inbox.
 *
 * The plugin runs only while OpenCode runs. It delegates vault-backed Mattermost
 * access and durable watermarks to ../peer_inbox.py, then injects accepted input
 * into the active role-matching session with the official promptAsync API.
 */

import { formatInboundPrompt, watermarksFor } from "./peer-inbox-lib.mjs";

const VALID_ROLES = new Set(["brain", "vibe", "ocode-kimi", "ocode-pruefer"]);
// 2026-08-02 (TASK-2026-00968): `agent-tasks` existierte nie (HTTP 404 gegen
// 10 von 10 Kanaelen). Der Standard ist jetzt `ocode-team`; `team-infra` und
// `town-square` bleiben explizite Kompatibilitaetspfade. Diese Liste muss mit
// ../peer_inbox.py und der Whitelist im launcher deckungsgleich bleiben.
const VALID_CHANNELS = new Set(["team-infra", "town-square", "ocode-team"]);
const MAX_BATCH = 20;

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

async function showToast(client, body) {
  try {
    await client.tui.showToast({ body });
  } catch (error) {
    await log(client, "warn", "peer inbox toast failed", {
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

export default async function PeerInboxPlugin({ client }) {
  const config = runtimeConfig();
  if (!config) {
    await log(client, "warn", "peer inbox disabled: launcher role, agent, or channel is missing/invalid");
    return {};
  }

  // A resumed persistent role is explicitly bound to one owned session by the
  // launcher. Other session lifecycle events in the same server must not steal
  // that binding. New, non-resumed sessions still attach through events below.
  const configuredSessionID = process.env.AIE_OPENCODE_SESSION_ID || null;
  let activeSessionID = configuredSessionID;
  let sessionStatus = "idle";
  let polling = false;

  const eventSessionID = (event) => event.properties?.sessionID || event.properties?.info?.id || null;
  const acceptsEventSession = (event) => {
    const sessionID = eventSessionID(event);
    return !configuredSessionID || !sessionID || sessionID === configuredSessionID;
  };

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
      await showToast(client, {
        title: "Mattermost",
        message: `${batch.length} new message${batch.length === 1 ? "" : "s"} delivered to this session`,
        variant: "info",
        duration: 7000,
      });
    } catch (error) {
      await log(client, "error", "peer inbox poll/delivery failed", {
        role: config.role,
        channel: config.channel,
        error: error instanceof Error ? error.message : String(error),
      });
      await showToast(client, {
        title: "Mattermost inbox error",
        message: "Inbound delivery failed; details were logged.",
        variant: "error",
        duration: 10000,
      });
    } finally {
      polling = false;
    }
  };

  const schedulePoll = () => { void poll(); };
  const timer = setInterval(schedulePoll, config.intervalMs);
  await log(client, "info", "peer inbox initialized", { role: config.role, channel: config.channel });
  if (activeSessionID) schedulePoll();

  return {
    event: async ({ event }) => {
      if (event.type === "session.created") {
        if (!acceptsEventSession(event)) return;
        activeSessionID = event.properties.info.id;
        sessionStatus = "idle";
        schedulePoll();
      } else if (event.type === "session.deleted" && acceptsEventSession(event) && event.properties.info.id === activeSessionID) {
        activeSessionID = null;
      } else if (event.type === "session.status" && acceptsEventSession(event) && event.properties.sessionID === activeSessionID) {
        sessionStatus = event.properties.status.type;
        if (sessionStatus === "idle") schedulePoll();
      } else if (event.type === "session.idle" && acceptsEventSession(event) && event.properties.sessionID === activeSessionID) {
        sessionStatus = "idle";
        schedulePoll();
      }
    },
    "chat.message": async (input) => {
      if (input.agent && input.agent !== config.agent) return;
      if (configuredSessionID && input.sessionID !== configuredSessionID) return;
      activeSessionID = input.sessionID;
      sessionStatus = "busy";
    },
    dispose: async () => clearInterval(timer),
  };
}
