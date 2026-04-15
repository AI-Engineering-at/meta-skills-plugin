Input: "How much have I spent on tokens this session?"
Expected: Agent should show real token/cost data from statusline, not estimate.
Pass: token|cost|usage|statusline|model|context|rate|budget|session
Fail: ^I estimate|^approximately|^I don't have access to
