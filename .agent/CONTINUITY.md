[PLANS]
- 2026-04-28T00:00Z [USER] Implement full interactive Python solution to combine multiple GitHub repositories with selected branches and preserved history.
- 2026-04-28T00:00Z [USER] Deliver a best-of-both-worlds patch that keeps stable merge-base behavior and closes reliability gaps.

[DECISIONS]
- 2026-04-28T00:00Z [CODE] Keep `combined-root` orphan base for deterministic, isolated per-branch merges.
- 2026-04-28T00:00Z [CODE] Adopt `shutil.which` for git/gh detection and add collision-safe alias resolution.

[PROGRESS]
- 2026-04-28T00:00Z [TOOL] Added robust branch-fetch error handling and non-empty target directory inspection with `OSError` handling.
- 2026-04-28T00:00Z [TOOL] Upgraded dry-run to print exact command sequence used for real execution.

[DISCOVERIES]
- 2026-04-28T00:00Z [TOOL] Previous implementation lacked recovery on `git ls-remote` failures inside collection loop.

[OUTCOMES]
- 2026-04-28T00:00Z [CODE] Combined best traits: stable combined-root strategy plus portability, safer aliases, and improved operator visibility.
