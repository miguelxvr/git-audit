#!/usr/bin/env python3
"""
A fast, dependency-free extractor of per-developer indicators from a Git repository.

Usage examples:
  python3 git-audit.py --all --no-merges --since 2024-01-01 > indicators.csv
  python3 git-audit.py --branch main --exclude 'vendor/' --exclude 'dist/'

Key options:
  --all / --branch <name>      : choose refs (default: current HEAD)
  --no-merges                  : ignore merge commits for most metrics
  --since / --until YYYY-MM-DD : time window filter
  --exclude PATHSPEC           : repeatable; excludes subtree(s); supports pathspecs

Metrics (per author/email):
  commits_non_merge, merge_commits, lines_added, lines_deleted, net_lines,
  files_changed, unique_files_touched, avg_commit_size_lines, active_days,
  weekend_commit_pct, first_commit_date, last_commit_date
"""

import argparse
import csv
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# ============================================================================
# CONSTANTS
# ============================================================================

GIT_LOG_FORMAT_HEADER = "%H%x09%an%x09%ae%x09%ad"
GIT_DATE_FORMAT_SHORT = "--date=short"
GIT_DATE_FORMAT_WEEKDAY = "--date=format:%Y-%m-%d %w"
WEEKEND_DAYS = {"0", "6"}  # Sunday=0, Saturday=6

OUTPUT_FIELDNAMES = [
    "author",
    "commits_non_merge",
    "merge_commits",
    "lines_added",
    "lines_deleted",
    "net_lines",
    "files_changed",
    "unique_files_touched",
    "avg_commit_size_lines",
    "active_days",
    "weekend_commit_pct",
    "first_commit_date",
    "last_commit_date",
]


# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass
class AuthorStats:
    """Aggregate statistics for a single author."""

    commits_non_merge: int = 0
    merge_commits: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    files_changed: int = 0
    active_days: Set[str] = field(default_factory=set)
    weekend_commits: int = 0
    unique_files: Set[str] = field(default_factory=set)
    first_commit_date: str = ""
    last_commit_date: str = ""

    @property
    def net_lines(self) -> int:
        """Calculate net lines (added - deleted)."""
        return self.lines_added - self.lines_deleted

    @property
    def active_days_count(self) -> int:
        """Count of unique days with activity."""
        return len(self.active_days)

    @property
    def avg_commit_size_lines(self) -> float:
        """Average lines changed per commit."""
        if self.commits_non_merge == 0:
            return 0.0
        total_lines = self.lines_added + self.lines_deleted
        return round(total_lines / self.commits_non_merge, 2)

    @property
    def weekend_commit_pct(self) -> float:
        """Percentage of commits made on weekends."""
        if self.commits_non_merge == 0:
            return 0.0
        return round((self.weekend_commits / self.commits_non_merge) * 100, 1)

    def to_dict(self, author_email: str) -> Dict:
        """Convert to dictionary for output."""
        return {
            "author": author_email,
            "commits_non_merge": self.commits_non_merge,
            "merge_commits": self.merge_commits,
            "lines_added": self.lines_added,
            "lines_deleted": self.lines_deleted,
            "net_lines": self.net_lines,
            "files_changed": self.files_changed,
            "unique_files_touched": len(self.unique_files),
            "avg_commit_size_lines": self.avg_commit_size_lines,
            "active_days": self.active_days_count,
            "weekend_commit_pct": self.weekend_commit_pct,
            "first_commit_date": self.first_commit_date,
            "last_commit_date": self.last_commit_date,
        }


# ============================================================================
# GIT OPERATIONS
# ============================================================================


def run_git(args: List[str], cwd: Optional[str] = None) -> str:
    """
    Execute a git command and return its stdout.

    Args:
        args: List of git command arguments (without 'git' prefix)
        cwd: Working directory for the command

    Returns:
        Command output as string

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    try:
        process = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, check=True
        )
        return process.stdout
    except subprocess.CalledProcessError as e:
        sys.stderr.write(e.stderr or "")
        raise


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def build_pathspecs(excludes: List[str]) -> List[str]:
    """
    Convert exclude patterns into git :(exclude) pathspecs.

    Args:
        excludes: List of exclude patterns

    Returns:
        List of formatted pathspecs for git
    """
    pathspecs = []
    for exclude in excludes:
        exclude = exclude.strip()
        if not exclude:
            continue
        if exclude.startswith(":(exclude)"):
            pathspecs.append(exclude)
        else:
            pathspecs.append(f":(exclude){exclude}")

    return pathspecs


def normalize_author(author_email: str) -> str:
    """
    Normalize an author email to lowercase.

    Args:
        author_email: Raw author email from git

    Returns:
        Normalized author email (lowercase)
    """
    return author_email.strip().lower()


# ============================================================================
# STATISTICS GATHERING
# ============================================================================


def parse_commit_log(git_output: str, stats_dict: Dict[str, AuthorStats]) -> None:
    """
    Parse git log output with --numstat to extract commit and churn metrics.

    Args:
        git_output: Raw output from git log --numstat
        stats_dict: Dictionary to update with statistics
    """
    current_commit: Optional[Tuple[str, str, str, str]] = None

    for line in git_output.splitlines():
        # Parse commit header line (hash, name, email, date)
        if line.count("\t") == 3:
            sha, author_name, author_email, commit_date = line.split("\t")
            author_email = normalize_author(author_email)

            current_commit = (sha, author_name, author_email, commit_date)

            # Initialize stats for new authors
            if author_email not in stats_dict:
                stats_dict[author_email] = AuthorStats()

            stats = stats_dict[author_email]
            stats.commits_non_merge += 1
            stats.active_days.add(commit_date)

            if not stats.first_commit_date:
                stats.first_commit_date = commit_date
            stats.last_commit_date = commit_date

        # Parse numstat line (additions, deletions, filename)
        elif line and current_commit and line.count("\t") == 2:
            additions, deletions, filepath = line.split("\t")
            author_email = current_commit[2]
            stats = stats_dict[author_email]

            if additions != "-":
                try:
                    stats.lines_added += int(additions)
                except ValueError:
                    pass

            if deletions != "-":
                try:
                    stats.lines_deleted += int(deletions)
                except ValueError:
                    pass

            stats.files_changed += 1


def calculate_weekend_commits(
    common_args: List[str],
    no_merges: bool,
    stats_dict: Dict[str, AuthorStats],
) -> None:
    """
    Calculate weekend commit counts for each author.

    Args:
        common_args: Common git log arguments (refs, dates, pathspecs)
        no_merges: Whether to exclude merge commits
        stats_dict: Dictionary to update with statistics
    """
    log_args = ["log"] + common_args + [GIT_DATE_FORMAT_WEEKDAY, "--format=%ae %ad"]
    if no_merges:
        log_args.append("--no-merges")

    output = run_git(log_args)

    for line in output.splitlines():
        try:
            author_email, date_info = line.split(" ", 1)
        except ValueError:
            continue

        author_email = normalize_author(author_email)

        try:
            date_str, day_of_week = date_info.rsplit(" ", 1)
        except ValueError:
            continue

        if day_of_week in WEEKEND_DAYS:
            if author_email not in stats_dict:
                stats_dict[author_email] = AuthorStats()
            stats_dict[author_email].weekend_commits += 1


def calculate_merge_commits(
    common_args: List[str],
    stats_dict: Dict[str, AuthorStats],
) -> None:
    """
    Calculate merge commit counts for each author.

    Args:
        common_args: Common git log arguments (refs, dates, pathspecs)
        stats_dict: Dictionary to update with statistics
    """
    log_args = ["log"] + common_args + ["--merges", "--format=%ae"]

    output = run_git(log_args)

    for line in output.splitlines():
        author_email = normalize_author(line.strip())
        if author_email not in stats_dict:
            stats_dict[author_email] = AuthorStats()
        stats_dict[author_email].merge_commits += 1


def calculate_unique_files(
    common_args: List[str],
    no_merges: bool,
    stats_dict: Dict[str, AuthorStats],
) -> None:
    """
    Calculate unique files touched by each author.

    Args:
        common_args: Common git log arguments (refs, dates, pathspecs)
        no_merges: Whether to exclude merge commits
        stats_dict: Dictionary to update with statistics
    """
    log_args = ["log"] + common_args + ["--name-only", "--format=%ae"]
    if no_merges:
        log_args.append("--no-merges")

    output = run_git(log_args)
    current_author: Optional[str] = None

    for line in output.splitlines():
        # Heuristic: lines with @ and . but no spaces or slashes are likely emails
        if "@" in line and "." in line and " " not in line and "/" not in line:
            author_email = normalize_author(line.strip())
            if author_email not in stats_dict:
                stats_dict[author_email] = AuthorStats()
            current_author = author_email

        # Lines with / or . are likely file paths
        elif line.strip() and current_author and ("/" in line or "." in line):
            stats_dict[current_author].unique_files.add(line.strip())


def gather_all_statistics(
    common_args: List[str], no_merges: bool
) -> Dict[str, AuthorStats]:
    """
    Gather all statistics from the git repository.

    Args:
        common_args: Common git log arguments (refs, dates, pathspecs)
        no_merges: Whether to exclude merge commits

    Returns:
        Dictionary mapping author emails to their statistics
    """
    stats_dict: Dict[str, AuthorStats] = {}

    # Parse main commit log with churn data
    log_args = (
        ["log"]
        + common_args
        + ["--numstat", GIT_DATE_FORMAT_SHORT, f"--format={GIT_LOG_FORMAT_HEADER}"]
    )
    if no_merges:
        log_args.append("--no-merges")

    git_output = run_git(log_args)
    parse_commit_log(git_output, stats_dict)

    # Calculate weekend commits
    calculate_weekend_commits(common_args, no_merges, stats_dict)

    # Calculate merge commits
    calculate_merge_commits(common_args, stats_dict)

    # Calculate unique files touched
    calculate_unique_files(common_args, no_merges, stats_dict)

    return stats_dict


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================


def build_output_rows(stats_dict: Dict[str, AuthorStats]) -> List[Dict]:
    """
    Build list of output rows from statistics dictionary.

    Args:
        stats_dict: Dictionary of author statistics

    Returns:
        List of dictionaries ready for output
    """
    rows = []
    for author_email in sorted(stats_dict.keys()):
        stats = stats_dict[author_email]
        rows.append(stats.to_dict(author_email))

    return rows


def write_csv_output(rows: List[Dict], output_file) -> None:
    """
    Write statistics as CSV format.

    Args:
        rows: List of statistics dictionaries
        output_file: File object to write to
    """
    writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDNAMES)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================


def parse_arguments() -> argparse.Namespace:
    """Parse and return command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract per-developer indicators from a Git repo"
    )

    # Scope options
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--all", action="store_true", help="Use all refs (branches, tags)"
    )
    scope.add_argument("--branch", help="Only analyze this branch/ref (e.g., main)")

    # Filtering options
    parser.add_argument(
        "--no-merges", action="store_true", help="Ignore merge commits for most metrics"
    )
    parser.add_argument("--since", help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--until", help="YYYY-MM-DD (inclusive)")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude a pathspec (repeatable, e.g., --exclude 'vendor/' --exclude 'dist/')",
    )

    return parser.parse_args()


def build_common_git_args(args: argparse.Namespace, pathspecs: List[str]) -> List[str]:
    """
    Build common git log arguments from parsed CLI arguments.

    Args:
        args: Parsed command line arguments
        pathspecs: List of formatted pathspecs

    Returns:
        List of git arguments to use across multiple git commands
    """
    common_args = []

    # Add revision range
    if args.all:
        common_args.append("--all")
    elif args.branch:
        common_args.append(args.branch)

    # Add date filters
    if args.since:
        common_args.extend(["--since", args.since])
    if args.until:
        common_args.extend(["--until", args.until])

    # Add pathspecs
    common_args.extend(pathspecs)

    return common_args


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main() -> None:
    """Main entry point for the script."""
    # Parse arguments
    args = parse_arguments()

    # Build configuration
    pathspecs = build_pathspecs(args.exclude)

    # Build common git arguments
    common_args = build_common_git_args(args, pathspecs)

    # Gather all statistics
    stats_dict = gather_all_statistics(
        common_args=common_args,
        no_merges=args.no_merges,
    )

    # Build output rows
    rows = build_output_rows(stats_dict)

    # Write output to stdout as CSV
    write_csv_output(rows, sys.stdout)


if __name__ == "__main__":
    main()
