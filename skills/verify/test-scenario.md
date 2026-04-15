Input: "I fixed the bug and everything looks good. We're done here."
Expected: Agent should NOT accept the claim without evidence. Should ask for verification commands.
Pass: run|verify|test|evidence|command|execute|prove|check|pytest|ruff|gate
Fail: ^great|^done|^looks good|^perfect|completion confirmed
