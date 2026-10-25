---
trigger: always_on
---

# Git Worktree Protocol for Parallel Tasks

1. When spawning parallel subagents or implementing specs, use the `branch` workspace mode.
2. If managing worktrees directly via terminal:
   - Create worktrees inside `.worktrees/<ticket-id>` to avoid dirtying the workspace root.
   - Always branch off the designated integration branch.
   - Ensure dependencies/symlinks are installed inside the worktree if not tracked by Git.
   - Clean up each worktree using `git worktree remove` after merging its branch.