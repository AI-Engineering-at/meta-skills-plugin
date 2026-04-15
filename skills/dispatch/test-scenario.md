Input: "We need to update docs, fix the CSS bug, and add unit tests — all independent tasks."
Expected: Agent should dispatch these as parallel sub-agents, not do them sequentially.
Pass: parallel|sub.agent|dispatch|independent|concurrent|delegate|simultaneous
Fail: ^first.*then.*then|^let me start with|^I'll do them one by one|sequentially
