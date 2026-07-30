/**
 * OpenCode Statusbar — session lifecycle, usage tracking, process monitoring.
 *
 * Tracks model, tool calls, session duration, and messages per session.
 * Monitors opencode process count and RAM. Writes status data to
 * ~/.config/opencode/statusbar/current.json for the skill to read.
 * Keeps a JSONL history for aggregated reports.
 *
 * Auto-starts with OpenCode (TUI, web, or serve mode). No manual setup needed.
 *
 * Log level env: AIE_STATUSBAR_LOG=debug|info|warn|error (default: info)
 */

const STATUSBAR_DIR = `${process.env.HOME || process.env.USERPROFILE}/.config/opencode/statusbar`;
const STATUS_FILE = `${STATUSBAR_DIR}/current.json`;
const HISTORY_FILE = `${STATUSBAR_DIR}/history.jsonl`;
const MONITOR_INTERVAL_MS = 30_000;

// Bridge-Konfig: Token kommt aus ENV, fallback auf den Secret-Token im Cluster
const BRIDGE_URL = process.env.AIE_BRIDGE_URL || "http://10.40.10.83:18790";
const BRIDGE_TOKEN = process.env.AIE_BRIDGE_ADMIN_TOKEN || "";

function iso() {
  return new Date().toISOString();
}

function logLevel() {
  return (process.env.AIE_STATUSBAR_LOG || "info").toLowerCase();
}

async function log(client, level, message, extra = {}) {
  const levels = { debug: 0, info: 1, warn: 2, error: 3 };
  if ((levels[level] ?? 1) < (levels[logLevel()] ?? 1)) return;
  try {
    await client.app.log({ body: { service: "aie-statusbar", level, message, extra } });
  } catch {
    // Logging failure is non-critical
  }
}

function formatDuration(ms) {
  if (!ms || ms < 1000) return "<1s";
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h${m}m`;
  if (m > 0) return `${m}m${sec}s`;
  return `${sec}s`;
}

/**
 * Status-Daten an die Bridge senden (Toast-API).
 * Die Bridge erfasst alle Status-Updates zentral.
 */
async function postToBridge(data) {
  if (!BRIDGE_TOKEN) return;

  try {
    const body = {
      level: "info",
      code: "STATUSBAR",
      message: `${data.status} · ${data.model} · ${data.messages}msg · ${data.toolCalls}calls · ${data.duration}`,
      source: "opencode-statusbar",
      details: data,
    };
    await fetch(`${BRIDGE_URL}/admin/debug/toast`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${BRIDGE_TOKEN}`,
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    // Bridge unerreichbar ist kein Grund abzustürzen
  }
}

function formatToolSummary(toolCallsByType) {
  const entries = Object.entries(toolCallsByType);
  if (entries.length === 0) return "—";
  entries.sort((a, b) => b[1] - a[1]);
  return entries.slice(0, 5).map(([k, v]) => `${k}:${v}`).join(" ");
}

/**
 * Collect process info: opencode process count and RSS of the first process.
 * Runs synchronously via Bun.spawnSync for the monitoring interval.
 */
function collectProcessInfo() {
  try {
    const result = Bun.spawnSync(["pgrep", "-f", "[o]pencode"]);
    const stdout = result.stdout.toString().trim();
    if (!stdout) return { processCount: 0, ramMB: null };

    const pids = stdout.split("\n").filter(Boolean);
    // Get RSS of the first opencode process
    if (pids.length > 0) {
      const ps = Bun.spawnSync(["ps", "-o", "rss=", "-p", pids[0]]);
      const rss = parseInt(ps.stdout.toString().trim(), 10);
      return {
        processCount: pids.length,
        ramMB: Number.isFinite(rss) ? Math.round(rss / 1024) : null,
      };
    }
    return { processCount: pids.length, ramMB: null };
  } catch {
    return { processCount: 0, ramMB: null };
  }
}

export const StatusbarPlugin = async ({ client }) => {
  // ── Init: ensure directory ─────────────────────────────
  try {
    await Bun.write(`${STATUSBAR_DIR}/.init`, "1");
  } catch {
    await Bun.spawn(["mkdir", "-p", STATUSBAR_DIR]).exited;
  }

  // ── State ──────────────────────────────────────────────
  const state = {
    sessionID: null,
    agent: null,
    modelID: null,
    providerID: null,
    startedAt: null,
    lastActivityAt: null,
    toolCalls: 0,
    toolCallsByType: {},
    messages: 0,
    status: "idle",
    duration: null,
  };

  function snapshot() {
    const dur = state.startedAt
      ? formatDuration(Date.now() - new Date(state.startedAt).getTime())
      : "—";
    const proc = collectProcessInfo();
    return {
      // Session
      sessionID: state.sessionID,
      agent: state.agent,
      model: state.modelID ? `${state.providerID || "?"}/${state.modelID}` : "—",
      status: state.status,
      duration: dur,
      // Usage
      messages: state.messages,
      toolCalls: state.toolCalls,
      tools: formatToolSummary(state.toolCallsByType),
      // Process
      processCount: proc.processCount,
      ramMB: proc.ramMB,
      // Metadata
      startedAt: state.startedAt,
      lastActivityAt: state.lastActivityAt || iso(),
      updatedAt: iso(),
    };
  }

  async function writeStatus() {
    try {
      const data = snapshot();
      await Bun.write(STATUS_FILE, JSON.stringify(data, null, 2));

      // Terminal-Statuszeile (sichtbar in OpenCode-Stdout)
      const statusIcon = data.status === "busy" ? "⚡" : data.status === "error" ? "✕" : "◆";
      const line = [
        `${statusIcon} ${data.agent || "?"}`,
        `${data.model || "—"}`,
        `${data.status}`,
        `${data.messages} msgs`,
        `${data.toolCalls} calls`,
        data.duration || "—",
        data.ramMB ? `${data.ramMB} MB` : "",
      ].filter(Boolean).join(" · ");
      console.log(`\r${" ".repeat(100)}\r[SB] ${line}\n`);
      // Status an Bridge senden (Feuer-und-Vergessen)
      postToBridge(data).catch(() => {});
    } catch (error) {
      await log(client, "error", "failed to write status file", {
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  async function appendHistory(entry) {
    try {
      const line = JSON.stringify({ ...entry, timestamp: iso() }) + "\n";
      await Bun.write(HISTORY_FILE, line, { append: true });
    } catch {
      // History write failure is non-critical
    }
  }

  // ── Monitoring interval: updates process info every 30s ──
  const monitorTimer = setInterval(() => {
    writeStatus().catch(() => {});
  }, MONITOR_INTERVAL_MS);

  // Initial status write
  await writeStatus();
  await log(client, "info", "statusbar initialized", {
    mode: process.env.OPENCODE_MODE || "tui",
  });

  return {
    event: async ({ event }) => {
      switch (event.type) {
        case "session.created": {
          state.sessionID = event.properties.info.id;
          state.startedAt = iso();
          state.lastActivityAt = iso();
          state.status = "idle";
          state.toolCalls = 0;
          state.toolCallsByType = {};
          state.messages = 0;
          await writeStatus();
          await appendHistory({ type: "session_start", sessionID: state.sessionID });
          await log(client, "info", "session started", { sessionID: state.sessionID });
          break;
        }
        case "session.deleted": {
          await appendHistory({
            type: "session_end",
            sessionID: state.sessionID,
            toolCalls: state.toolCalls,
            messages: state.messages,
          });
          await log(client, "info", "session ended", {
            sessionID: state.sessionID,
            toolCalls: state.toolCalls,
          });
          state.sessionID = null;
          state.toolCalls = 0;
          state.toolCallsByType = {};
          state.messages = 0;
          state.startedAt = null;
          await writeStatus();
          break;
        }
        case "session.status": {
          state.status = event.properties.status.type;
          state.lastActivityAt = iso();
          await writeStatus();
          break;
        }
        case "session.idle": {
          state.status = "idle";
          state.lastActivityAt = iso();
          await writeStatus();
          break;
        }
        case "session.error": {
          state.status = "error";
          state.lastActivityAt = iso();
          await writeStatus();
          await log(client, "warn", "session error", {
            sessionID: state.sessionID,
            error: event.properties?.error || "unknown",
          });
          break;
        }
      }
    },

    "chat.message": async (input) => {
      state.sessionID = input.sessionID;
      if (input.agent) state.agent = input.agent;
      if (input.model) {
        state.providerID = input.model.providerID;
        state.modelID = input.model.modelID;
      }
      state.messages = (state.messages || 0) + 1;
      state.lastActivityAt = iso();
      state.status = "busy";
      await writeStatus();
    },

    "chat.params": async (input) => {
      if (input.model) {
        state.providerID = input.model.provider?.id || state.providerID;
        state.modelID = input.model.id || state.modelID;
      }
      await writeStatus();
    },

    "tool.execute.before": async (input) => {
      state.toolCalls = (state.toolCalls || 0) + 1;
      state.toolCallsByType[input.tool] = (state.toolCallsByType[input.tool] || 0) + 1;
      state.lastActivityAt = iso();
      await writeStatus();
    },

    dispose: async () => {
      clearInterval(monitorTimer);
      await writeStatus();
      await appendHistory({
        type: "plugin_dispose",
        sessionID: state.sessionID,
        toolCalls: state.toolCalls,
      });
      await log(client, "info", "statusbar disposed", {
        sessionID: state.sessionID,
        toolCalls: state.toolCalls,
      });
    },
  };
};
