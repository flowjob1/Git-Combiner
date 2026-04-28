# Git-Combiner

Interactive Python script that combines two or more GitHub repositories into a new repository while preserving the full history of all selected branches.

## Features

- Accepts repository input as `owner/repo` or GitHub URL.
- Lists remote branches and supports branch selection by number or `all`.
- Repeats repository collection until you continue with at least two repositories.
- Uses collision-safe repository aliases for namespaced import and output branches.
- Preserves full commit history using `git fetch` and merge with unrelated histories enabled.
- Verifies that imported history is an ancestor of each combined branch.
- Supports dry-run mode with full command-by-command preview.

## Requirements

- Python 3.10+
- Git available in `PATH`
- Optional: GitHub CLI (`gh`) for login flow integration

## Usage

```bash
python git_combiner.py --target-dir combined-output
```

Optional dry run:

```bash
python git_combiner.py --dry-run
```

## Output branch model

For each selected source branch:

- Imported branch: `import/<repo_alias>/<source-branch>`
- Combined branch: `combined/<repo_alias>/<source-branch-with-slashes-replaced>`

The script creates a root branch `combined-root` with an initial empty commit as a stable merge base.
