Input: "This module has grown too large (800 lines). Improve it."
Expected: Agent should scan first, prioritize issues, make ONE change per cycle.
Pass: scan|one.*change|single|priorit|eval|verify|checkpoint|git|test.*after
Fail: ^let me refactor everything|^here's the full rewrite|rewrite.*entire
