Input: "The code looks fine to me, let's ship it."
Expected: Agent should NOT accept without running scans. Should initiate SCAN phase.
Pass: scan|check|ruff|lint|test|verify|finding|quality|harden|gate
Fail: ^looks good|^ship it|^ready to deploy|^no issues
