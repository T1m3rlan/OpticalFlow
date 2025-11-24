#!/usr/bin/env python3
"""
Archive git branches (create tar.gz snapshots) while keeping the most recent ones.

By default the script keeps the latest local branch (based on committer date)
and archives the rest into `archives/branches`. A manifest is maintained so
it's easy to track what was archived and when.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class BranchInfo:
    name: str
    commit: str
    committer_date: dt.datetime


class GitError(RuntimeError):
    """Raised when a git command fails."""


def run_git(args: Sequence[str], *, capture_output: bool = True) -> str:
    """Run a git command and return stdout (stripped) when requested."""
    result = subprocess.run(
        ["git", *args],
        capture_output=capture_output,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed with code {result.returncode}: {result.stderr.strip()}"
        )
    if capture_output:
        return result.stdout.strip()
    return ""


def discover_branches(scope: str) -> List[BranchInfo]:
    """Return branches ordered by committer date (desc)."""
    ref_map = {
        "local": "refs/heads",
        "remote": "refs/remotes",
        "all": "refs",
    }
    refspec = ref_map[scope]
    fmt = "%(refname:short)|%(committerdate:iso8601)|%(objectname)"
    raw = run_git(
        ["for-each-ref", "--sort=-committerdate", f"--format={fmt}", refspec]
    )
    if not raw:
        return []

    branches: List[BranchInfo] = []
    for line in raw.splitlines():
        try:
            name, date_str, commit = line.split("|")
        except ValueError as exc:  # pragma: no cover - defensive
            raise GitError(f"Unexpected for-each-ref output: {line}") from exc

        # Git outputs timezone as +HHMM, so parse manually.
        parsed_date = dt.datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S %z")
        branches.append(BranchInfo(name=name, commit=commit, committer_date=parsed_date))
    return branches


def sanitize_branch_name(name: str) -> str:
    """Convert branch name into filesystem-friendly token."""
    safe = name.replace("/", "__")
    return safe.replace(" ", "_")


def archive_branch(branch: BranchInfo, output_dir: pathlib.Path, *, force: bool) -> pathlib.Path:
    """Create a tar.gz snapshot for the given branch."""
    timestamp = branch.committer_date.strftime("%Y%m%d-%H%M%S")
    safe_name = sanitize_branch_name(branch.name)
    archive_name = f"{safe_name}-{branch.commit[:8]}-{timestamp}.tar.gz"
    archive_path = output_dir / archive_name

    if archive_path.exists() and not force:
        raise FileExistsError(
            f"{archive_path} already exists. Use --force to overwrite."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    run_git(
        ["archive", "--format=tar.gz", "-o", str(archive_path), branch.name],
        capture_output=False,
    )
    return archive_path


def delete_branch(branch: BranchInfo) -> None:
    """Delete a local branch after it has been archived."""
    run_git(["branch", "-D", branch.name])


def load_manifest(path: pathlib.Path) -> List[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text())


def write_manifest(path: pathlib.Path, entries: Iterable[dict]) -> None:
    data = sorted(entries, key=lambda item: item["archived_at"], reverse=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Archive git branches into compressed snapshots."
    )
    parser.add_argument(
        "--scope",
        choices=("local", "remote", "all"),
        default="local",
        help="Which refs to consider when determining branches (default: local).",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=1,
        help="Number of most recent branches to keep unarchived (default: 1).",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=pathlib.Path("archives/branches"),
        help="Directory where archives and manifest will be stored.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing archives if file names collide.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete archived local branches after snapshotting.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        repo_root = pathlib.Path(run_git(["rev-parse", "--show-toplevel"]))
    except GitError as exc:
        parser.error(str(exc))

    branches = discover_branches(args.scope)
    if not branches:
        print("No branches found for the given scope.")
        return 0

    keep_count = max(args.keep, 0)
    to_archive = branches[keep_count:]
    kept = branches[:keep_count]

    if not to_archive:
        print(f"Nothing to archive. Only {len(branches)} branch(es) exist.")
        return 0

    archives_dir = repo_root / args.output_dir
    manifest_path = archives_dir / "manifest.json"
    manifest = load_manifest(manifest_path)

    print(f"Keeping {len(kept)} branch(es): " + ", ".join(b.name for b in kept))
    print(f"Archiving {len(to_archive)} branch(es): " + ", ".join(b.name for b in to_archive))

    for branch in to_archive:
        archive_path = archive_branch(branch, archives_dir, force=args.force)
        entry = {
            "branch": branch.name,
            "commit": branch.commit,
            "committer_date": branch.committer_date.isoformat(),
            "archive": str(archive_path.relative_to(repo_root)),
            "archived_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        manifest.append(entry)
        print(f"✔ Archived {branch.name} -> {entry['archive']}")

        if args.delete and args.scope == "local":
            delete_branch(branch)
            print(f"✖ Deleted local branch {branch.name}")

    write_manifest(manifest_path, manifest)
    print(f"Manifest updated at {manifest_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
