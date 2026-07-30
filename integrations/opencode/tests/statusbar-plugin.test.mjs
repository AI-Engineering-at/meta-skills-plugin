import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { fileURLToPath } from "node:url";

const pluginPath = fileURLToPath(
  new URL("../../../.opencode-plugin/plugins/statusbar.mjs", import.meta.url),
);

test("statusbar requires an admin token from the environment", async () => {
  const source = await readFile(pluginPath, "utf8");

  assert.match(
    source,
    /const BRIDGE_TOKEN = process\.env\.AIE_BRIDGE_ADMIN_TOKEN \|\| "";/,
  );
  assert.doesNotMatch(source, /const BRIDGE_TOKEN = ["'][^"']+["'];/);
  assert.match(source, /if \(!BRIDGE_TOKEN\) return;/);
});
