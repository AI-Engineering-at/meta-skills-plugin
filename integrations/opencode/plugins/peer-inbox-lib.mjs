export function watermarksFor(messages = []) {
  const watermarks = {};
  for (const message of messages) {
    const timestamp = Number(message.create_at || 0);
    if (!Number.isFinite(timestamp) || timestamp <= 0) continue;
    watermarks[message.source] = Math.max(watermarks[message.source] || 0, timestamp);
  }
  return watermarks;
}

export function formatInboundPrompt(role = "brain", messages = []) {
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
