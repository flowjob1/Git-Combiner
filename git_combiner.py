#!/usr/bin/env python3
"""Interactive utility to combine multiple GitHub repositories preserving full branch history."""

from __future__ import annotations

import argparse
import getpass
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


REPO_PATTERN = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)?"
    r"(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)
NON_ALNUM_PATTERN = re.compile(r"[^A-Za-z0-9]+")


@dataclass(frozen=True)
class RepoSpec:
    owner: str
    repo: str

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}.git"


@dataclass(frozen=True)
class RepoSelection:
    repo: RepoSpec
    alias: str
    branches: list[str]


class GitCommandError(RuntimeError):
    """Raised when a git command fails."""


def run_command(
    command: Sequence[str],
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command),
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=capture,
    )
    if check and result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or "No output from command."
        raise GitCommandError(f"Command failed: {' '.join(command)}\n{details}")
    return result


def ensure_git_installed() -> None:
    if shutil.which("git") is None:
        raise SystemExit("Git is not installed or not available in PATH.")
    run_command(["git", "--version"])


def check_or_prompt_auth() -> None:
    if shutil.which("gh") is None:
        print("GitHub CLI (gh) not found. Continuing; git credential flow may prompt later.")
        return

    auth = run_command(["gh", "auth", "status"], check=False)
    if auth.returncode == 0:
        print("GitHub CLI authentication is already active.")
        return

    print("GitHub CLI is not authenticated. Starting login flow...")
    login = run_command(["gh", "auth", "login"], check=False, capture=False)
    if login.returncode != 0:
        raise SystemExit("GitHub login failed. Please authenticate and rerun.")


def prompt_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Value cannot be empty.")


def prompt_repo_name() -> str:
    pattern = re.compile(r"^[A-Za-z0-9_.-]+$")
    while True:
        value = prompt_non_empty("Enter the new GitHub repository name: ")
        if pattern.match(value):
            return value
        print("Invalid name. Use only letters, digits, '.', '_' or '-'.")


def parse_repo_input(raw: str) -> RepoSpec:
    value = raw.strip()
    match = REPO_PATTERN.match(value)
    if not match:
        raise ValueError("Invalid repository format. Use user/repo or a GitHub URL.")
    return RepoSpec(owner=match.group("owner"), repo=match.group("repo"))


def normalize_alias(value: str) -> str:
    alias = NON_ALNUM_PATTERN.sub("_", value).strip("_").lower()
    return alias or "repo"


def resolve_unique_alias(repo: RepoSpec, used: set[str]) -> str:
    base = normalize_alias(f"{repo.owner}_{repo.repo}")
    if base not in used:
        used.add(base)
        return base

    index = 2
    while True:
        candidate = f"{base}_{index}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def list_remote_branches(repo_url: str) -> list[str]:
    output = run_command(["git", "ls-remote", "--heads", repo_url]).stdout
    branches: list[str] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        ref = parts[1]
        prefix = "refs/heads/"
        if ref.startswith(prefix):
            branches.append(ref[len(prefix):])
    return sorted(set(branches))


def prompt_repo() -> RepoSpec:
    while True:
        raw = input("Enter repository (user/repo or https://github.com/user/repo): ").strip()
        try:
            return parse_repo_input(raw)
        except ValueError as error:
            print(error)


def prompt_branch_selection(branches: Sequence[str]) -> list[str]:
    if not branches:
        raise SystemExit("No branches found in repository.")

    print("Available branches:")
    for index, branch in enumerate(branches, start=1):
        print(f"{index}. {branch}")

    while True:
        selection = input("Select branches by numbers (e.g., 1,3) or 'all': ").strip().lower()
        if selection == "all":
            return list(branches)

        tokens = [item.strip() for item in selection.split(",") if item.strip()]
        if not tokens:
            print("No valid selection entered.")
            continue

        numbers: list[int] = []
        valid = True
        for token in tokens:
            if not token.isdigit():
                valid = False
                break
            number = int(token)
            if number < 1 or number > len(branches):
                valid = False
                break
            numbers.append(number)

        if not valid:
            print("Invalid selection. Use comma-separated numbers from the list.")
            continue

        unique = sorted(set(numbers))
        return [branches[number - 1] for number in unique]


def prompt_yes_no(prompt: str) -> bool:
    while True:
        answer = input(f"{prompt} [y/n]: ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer with y or n.")


def collect_repositories() -> list[RepoSelection]:
    selections: list[RepoSelection] = []
    used_aliases: set[str] = set()

    while True:
        repo = prompt_repo()
        if any(item.repo.slug.lower() == repo.slug.lower() for item in selections):
            print("Repository already added. Please choose a different one.")
            continue

        try:
            branches = list_remote_branches(repo.url)
        except GitCommandError as error:
            print(f"Failed to query branches for {repo.slug}: {error}")
            continue

        if not branches:
            print(f"No branches found in repository: {repo.slug}")
            continue

        selected = prompt_branch_selection(branches)
        alias = resolve_unique_alias(repo, used_aliases)
        print(f"Using alias '{alias}' for repository {repo.slug}.")
        selections.append(RepoSelection(repo=repo, alias=alias, branches=selected))

        if len(selections) >= 2 and not prompt_yes_no("Add another repository?"):
            return selections

        if len(selections) < 2:
            print("At least two repositories are required.")


def sanitize_branch_name(value: str) -> str:
    return value.replace("/", "__")


def init_target_repo(path: Path, execute) -> None:
    execute(["git", "init"], cwd=path)
    execute(["git", "checkout", "--orphan", "combined-root"], cwd=path)
    execute(["git", "commit", "--allow-empty", "-m", "Initialize combined repository"], cwd=path)


def combine_repositories(target: Path, selections: Sequence[RepoSelection], dry_run: bool = False) -> None:
    target.mkdir(parents=True, exist_ok=True)

    def execute(command: Sequence[str], cwd: Path | None = None) -> None:
        location = str(cwd) if cwd else "."
        print(f"[{location}] $ {' '.join(command)}")
        if not dry_run:
            run_command(command, cwd=cwd)

    init_target_repo(target, execute)

    for index, selection in enumerate(selections, start=1):
        remote_name = f"src_{index}"
        execute(["git", "remote", "add", remote_name, selection.repo.url], cwd=target)
        execute(["git", "fetch", remote_name, "--prune"], cwd=target)

        for branch in selection.branches:
            remote_ref = f"refs/remotes/{remote_name}/{branch}"
            import_branch = f"import/{selection.alias}/{branch}"
            combined_branch = f"combined/{selection.alias}/{sanitize_branch_name(branch)}"

            execute(["git", "show-ref", "--verify", remote_ref], cwd=target)
            execute(["git", "branch", import_branch, remote_ref], cwd=target)
            execute(["git", "checkout", "-B", combined_branch, "combined-root"], cwd=target)
            execute(
                [
                    "git",
                    "merge",
                    "--allow-unrelated-histories",
                    "--no-ff",
                    "-m",
                    f"Merge {selection.repo.slug} branch {branch}",
                    import_branch,
                ],
                cwd=target,
            )

    execute(["git", "checkout", "combined-root"], cwd=target)


def verify_result(target: Path, selections: Sequence[RepoSelection]) -> None:
    for selection in selections:
        for branch in selection.branches:
            import_branch = f"import/{selection.alias}/{branch}"
            combined_branch = f"combined/{selection.alias}/{sanitize_branch_name(branch)}"
            run_command(["git", "show-ref", "--verify", f"refs/heads/{combined_branch}"], cwd=target)
            run_command(["git", "merge-base", "--is-ancestor", import_branch, combined_branch], cwd=target)


def github_api_request(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    url = f"https://api.github.com{path}"
    body = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "git-combiner",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API request failed ({error.code}): {details}") from error
    except urllib.error.URLError as error:
        raise SystemExit(f"GitHub API request failed: {error}") from error


def ensure_github_token() -> str:
    while True:
        token = getpass.getpass("Enter a GitHub personal access token (repo scope): ").strip()
        if not token:
            print("Token cannot be empty.")
            continue
        user = github_api_request("GET", "/user", token)
        login = user.get("login")
        if login:
            print(f"Authenticated as GitHub user: {login}")
            return token
        print("Token validation failed. Please try again.")


def create_github_repo_with_gh(repo_name: str, private_repo: bool) -> str:
    visibility = "--private" if private_repo else "--public"
    run_command(["gh", "repo", "create", repo_name, visibility, "--confirm"])
    owner = run_command(["gh", "api", "user", "--jq", ".login"]).stdout.strip()
    if not owner:
        raise SystemExit("Failed to resolve authenticated GitHub user via gh.")
    return f"https://github.com/{owner}/{repo_name}.git"


def create_github_repo_with_api(repo_name: str, private_repo: bool) -> str:
    token = ensure_github_token()
    created = github_api_request(
        "POST",
        "/user/repos",
        token,
        {"name": repo_name, "private": private_repo},
    )
    clone_url = created.get("clone_url")
    if not clone_url:
        raise SystemExit("GitHub API did not return a clone URL for the created repository.")
    return clone_url


def publish_combined_repo(target: Path, selections: Sequence[RepoSelection], dry_run: bool) -> None:
    if not prompt_yes_no("Do you want to push the combined repository to GitHub?"):
        return

    repo_name = prompt_repo_name()
    private_repo = prompt_yes_no("Create the new GitHub repository as private?")
    has_gh = shutil.which("gh") is not None

    if has_gh:
        print("Using GitHub CLI (gh) for authentication and repository creation.")
        if not dry_run:
            check_or_prompt_auth()
            remote_url = create_github_repo_with_gh(repo_name, private_repo)
        else:
            remote_url = f"https://github.com/<authenticated-user>/{repo_name}.git"
    else:
        print("GitHub CLI (gh) not found. Using GitHub API token flow for repository creation.")
        if not dry_run:
            remote_url = create_github_repo_with_api(repo_name, private_repo)
        else:
            remote_url = f"https://github.com/<token-user>/{repo_name}.git"

    def execute(command: Sequence[str]) -> None:
        print(f"[{target}] $ {' '.join(command)}")
        if not dry_run:
            run_command(command, cwd=target)

    if not dry_run:
        existing_origin = run_command(
            ["git", "remote", "get-url", "origin"], cwd=target, check=False
        )
        if existing_origin.returncode == 0:
            raise SystemExit("Remote 'origin' already exists in target repository.")

    execute(["git", "remote", "add", "origin", remote_url])
    execute(["git", "push", "-u", "origin", "combined-root"])
    for selection in selections:
        for branch in selection.branches:
            combined_branch = f"combined/{selection.alias}/{sanitize_branch_name(branch)}"
            execute(["git", "push", "-u", "origin", combined_branch])
    print(f"Repository published to {remote_url}")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Combine multiple GitHub repositories preserving branch history.")
    parser.add_argument(
        "--target-dir",
        default="combined-output",
        help="Directory where the combined repository will be created.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show planned git actions without executing them.")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    ensure_git_installed()

    selections = collect_repositories()
    target = Path(args.target_dir).resolve()

    if target.exists() and not args.dry_run:
        try:
            if any(target.iterdir()):
                raise SystemExit(f"Target directory is not empty: {target}")
        except OSError as error:
            raise SystemExit(f"Unable to inspect target directory {target}: {error}") from error

    combine_repositories(target, selections, dry_run=args.dry_run)

    if not args.dry_run:
        verify_result(target, selections)
        print(f"Combination finished successfully in: {target}")
        publish_combined_repo(target, selections, args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
