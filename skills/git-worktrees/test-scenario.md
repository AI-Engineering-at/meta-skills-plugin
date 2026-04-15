Input: "I need to work on a hotfix while my feature branch has uncommitted changes."
Expected: Agent should create an isolated worktree, not suggest stashing.
Pass: worktree|isolat|git worktree|separate|parallel.*branch|checkout.*new
Fail: ^git stash|^stash your changes|^commit first then switch
