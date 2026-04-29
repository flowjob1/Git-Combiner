[PLANS]
- 2026-04-28T00:00Z [USER] Implement full interactive Python solution to combine multiple GitHub repositories with selected branches and preserved history.
- 2026-04-28T00:00Z [USER] Deliver a best-of-both-worlds patch that keeps stable merge-base behavior and closes reliability gaps.
- 2026-04-28T00:00Z [USER] Extend flow to optionally publish the combined repository to GitHub after successful local creation.
- 2026-04-28T00:00Z [USER] Deliver a best-of-both-worlds follow-up that fixes remaining publish-flow edge cases.

[DECISIONS]
- 2026-04-28T00:00Z [CODE] Keep `combined-root` orphan base for deterministic, isolated per-branch merges.
- 2026-04-28T00:00Z [CODE] Adopt `shutil.which` for git/gh detection and add collision-safe alias resolution.
- 2026-04-28T00:00Z [CODE] Make GitHub publish optional and provider-adaptive: prefer `gh` when present, fallback to GitHub API token flow when `gh` is unavailable.
- 2026-04-28T00:00Z [CODE] Run publish flow only after successful non-dry-run verification.
- 2026-04-28T00:00Z [CODE] Push only `combined-root` and generated `combined/*` branches instead of `--all`.

[PROGRESS]
- 2026-04-28T00:00Z [TOOL] Added robust branch-fetch error handling and non-empty target directory inspection with `OSError` handling.
- 2026-04-28T00:00Z [TOOL] Upgraded dry-run to print exact command sequence used for real execution.
- 2026-04-28T00:00Z [TOOL] Implemented post-combine interactive publish path with repository-name prompt, visibility prompt, remote creation, and git push steps.
- 2026-04-28T00:00Z [TOOL] Hardened publish path by securing token input and constraining pushed branches.

[DISCOVERIES]
- 2026-04-28T00:00Z [TOOL] Previous implementation lacked recovery on `git ls-remote` failures inside collection loop.
- 2026-04-28T00:00Z [CODE] Automatic GitHub repository creation is not possible with plain git only; fallback requires GitHub API token flow when `gh` is missing.

[OUTCOMES]
- 2026-04-28T00:00Z [CODE] Combined best traits: stable combined-root strategy plus portability, safer aliases, and improved operator visibility.
- 2026-04-28T00:00Z [CODE] Optional publishing now avoids dry-run prompts, uses hidden token entry, and pushes only intended output branches.
