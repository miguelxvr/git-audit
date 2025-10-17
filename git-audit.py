#!/usr/bin/env python3
"""
A fast, dependency-free extractor of per-developer indicators from a Git repository.

Usage examples:
  python3 git-audit.py --no-merges --since 2024-01-01 > indicators.csv
  python3 git-audit.py --branch main --exclude 'vendor/' --exclude 'dist/'
  python3 git-audit.py --repo https://github.com/user/repo.git > indicators.csv

Key options:
  --repo URL                   : GitHub/GitLab repository URL (clones temporarily)
  --branch <name>              : analyze specific branch (default: all refs)
  --no-merges                  : ignore merge commits for most metrics
  --since / --until YYYY-MM-DD : time window filter
  --exclude PATHSPEC           : repeatable; excludes subtree(s); supports pathspecs

Metrics (per author/email):
  Base metrics: commits_non_merge, merge_commits, total_commits, lines_added,
    lines_deleted, total_lines_changed, files_changed, unique_files_touched
  Calculated indicators: avg_commit_size_lines, commit_frequency, churn_ratio,
    files_per_commit, active_span_days, active_days
  Relative metrics: commit_pct, lines_changed_pct, files_touched_pct
  Dates: first_commit_date, last_commit_date
"""

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# ============================================================================
# CONSTANTS
# ============================================================================

GIT_LOG_FORMAT_HEADER = "%H%x09%an%x09%ae%x09%ad"
GIT_DATE_FORMAT_SHORT = "--date=short"

OUTPUT_FIELDNAMES = [
    "author",
    "commits_non_merge",
    "merge_commits",
    "total_commits",
    "lines_added",
    "lines_deleted",
    "total_lines_changed",
    "files_changed",
    "unique_files_touched",
    "avg_commit_size_lines",
    "active_days",
    "commit_frequency",
    "churn_ratio",
    "files_per_commit",
    "active_span_days",
    "first_commit_date",
    "last_commit_date",
    "commit_pct",
    "lines_changed_pct",
    "files_touched_pct",
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
    unique_files: Set[str] = field(default_factory=set)
    first_commit_date: str = ""
    last_commit_date: str = ""

    @property
    def active_days_count(self) -> int:
        """Count of unique days with activity."""
        return len(self.active_days)

    @property
    def total_commits(self) -> int:
        """Total commits including merges."""
        return self.commits_non_merge + self.merge_commits

    @property
    def total_lines_changed(self) -> int:
        """Total lines changed (additions + deletions)."""
        return self.lines_added + self.lines_deleted

    @property
    def avg_commit_size_lines(self) -> float:
        """Average lines changed per commit."""
        if self.commits_non_merge == 0:
            return 0.0
        return round(self.total_lines_changed / self.commits_non_merge, 2)

    @property
    def commit_frequency(self) -> float:
        """Commits per active day."""
        if self.active_days_count == 0:
            return 0.0
        return round(self.commits_non_merge / self.active_days_count, 2)

    @property
    def churn_ratio(self) -> float:
        """Code churn ratio (deletions / additions). Lower = more new code."""
        if self.lines_added == 0:
            return 0.0
        return round(self.lines_deleted / self.lines_added, 2)

    @property
    def files_per_commit(self) -> float:
        """Average files changed per commit."""
        if self.commits_non_merge == 0:
            return 0.0
        return round(self.files_changed / self.commits_non_merge, 2)

    @property
    def active_span_days(self) -> int:
        """Number of days between first and last commit."""
        if not self.first_commit_date or not self.last_commit_date:
            return 0
        try:
            from datetime import datetime

            first = datetime.strptime(self.first_commit_date, "%Y-%m-%d")
            last = datetime.strptime(self.last_commit_date, "%Y-%m-%d")
            return (last - first).days
        except:
            return 0

    def to_dict(
        self, author_email: str, relative_metrics: Optional[Dict] = None
    ) -> Dict:
        """
        Convert to dictionary for output.

        Args:
            author_email: Author email address
            relative_metrics: Optional dict with relative percentages
        """
        result = {
            "author": author_email,
            "commits_non_merge": self.commits_non_merge,
            "merge_commits": self.merge_commits,
            "total_commits": self.total_commits,
            "lines_added": self.lines_added,
            "lines_deleted": self.lines_deleted,
            "total_lines_changed": self.total_lines_changed,
            "files_changed": self.files_changed,
            "unique_files_touched": len(self.unique_files),
            "avg_commit_size_lines": self.avg_commit_size_lines,
            "active_days": self.active_days_count,
            "commit_frequency": self.commit_frequency,
            "churn_ratio": self.churn_ratio,
            "files_per_commit": self.files_per_commit,
            "active_span_days": self.active_span_days,
            "first_commit_date": self.first_commit_date,
            "last_commit_date": self.last_commit_date,
        }

        # Add relative metrics if provided
        if relative_metrics:
            result.update(relative_metrics)
        else:
            result.update(
                {
                    "commit_pct": 0.0,
                    "lines_changed_pct": 0.0,
                    "files_touched_pct": 0.0,
                }
            )

        return result


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


def is_valid_git_url(url: str) -> bool:
    """
    Validate if a string is a valid Git repository URL.

    Args:
        url: URL string to validate

    Returns:
        True if URL appears to be a valid Git repository URL
    """
    # Match GitHub, GitLab, and other common Git hosting patterns
    patterns = [
        r"^https?://github\.com/[\w\-]+/[\w\-\.]+(?:\.git)?$",
        r"^git@github\.com:[\w\-]+/[\w\-\.]+(?:\.git)?$",
        r"^https?://gitlab\.com/[\w\-]+/[\w\-\.]+(?:\.git)?$",
        r"^git@gitlab\.com:[\w\-]+/[\w\-\.]+(?:\.git)?$",
        r"^https?://[^\s]+\.git$",
        r"^git@[^\s]+\.git$",
    ]

    return any(re.match(pattern, url.strip(), re.IGNORECASE) for pattern in patterns)


def clone_repository(repo_url: str, temp_dir: str) -> None:
    """
    Clone a Git repository to a temporary directory.

    Args:
        repo_url: URL of the repository to clone
        temp_dir: Path to temporary directory

    Raises:
        subprocess.CalledProcessError: If git clone fails
    """
    sys.stderr.write(f"Cloning repository: {repo_url}\n")
    try:
        subprocess.run(
            ["git", "clone", "--quiet", repo_url, temp_dir],
            check=True,
            capture_output=True,
            text=True,
        )
        sys.stderr.write(f"Repository cloned to: {temp_dir}\n")
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Failed to clone repository: {e.stderr}\n")
        raise


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


def calculate_merge_commits(
    common_args: List[str],
    stats_dict: Dict[str, AuthorStats],
    cwd: Optional[str] = None,
) -> None:
    """
    Calculate merge commit counts for each author.

    Args:
        common_args: Common git log arguments (refs, dates, pathspecs)
        stats_dict: Dictionary to update with statistics
        cwd: Working directory for git commands
    """
    log_args = ["log"] + common_args + ["--merges", "--format=%ae"]

    output = run_git(log_args, cwd=cwd)

    for line in output.splitlines():
        author_email = normalize_author(line.strip())
        if author_email not in stats_dict:
            stats_dict[author_email] = AuthorStats()
        stats_dict[author_email].merge_commits += 1


def calculate_unique_files(
    common_args: List[str],
    no_merges: bool,
    stats_dict: Dict[str, AuthorStats],
    cwd: Optional[str] = None,
) -> None:
    """
    Calculate unique files touched by each author.

    Args:
        common_args: Common git log arguments (refs, dates, pathspecs)
        no_merges: Whether to exclude merge commits
        stats_dict: Dictionary to update with statistics
        cwd: Working directory for git commands
    """
    log_args = ["log"] + common_args + ["--name-only", "--format=%ae"]
    if no_merges:
        log_args.append("--no-merges")

    output = run_git(log_args, cwd=cwd)
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
    common_args: List[str], no_merges: bool, cwd: Optional[str] = None
) -> Dict[str, AuthorStats]:
    """
    Gather all statistics from the git repository.

    Args:
        common_args: Common git log arguments (refs, dates, pathspecs)
        no_merges: Whether to exclude merge commits
        cwd: Working directory for git commands

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

    git_output = run_git(log_args, cwd=cwd)
    parse_commit_log(git_output, stats_dict)

    # Calculate merge commits
    calculate_merge_commits(common_args, stats_dict, cwd=cwd)

    # Calculate unique files touched
    calculate_unique_files(common_args, no_merges, stats_dict, cwd=cwd)

    return stats_dict


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================


def calculate_relative_metrics(stats_dict: Dict[str, AuthorStats]) -> Dict[str, Dict]:
    """
    Calculate relative metrics (percentages) for each author.

    Args:
        stats_dict: Dictionary of author statistics

    Returns:
        Dictionary mapping author emails to their relative metrics
    """
    # Calculate totals
    total_commits = sum(s.total_commits for s in stats_dict.values())
    total_lines_changed = sum(s.total_lines_changed for s in stats_dict.values())

    # Get all unique files across all authors
    all_files = set()
    for stats in stats_dict.values():
        all_files.update(stats.unique_files)
    total_unique_files = len(all_files)

    # Calculate percentages for each author
    relative_metrics = {}
    for author_email, stats in stats_dict.items():
        commit_pct = (
            0.0
            if total_commits == 0
            else round((stats.total_commits / total_commits) * 100, 2)
        )
        lines_changed_pct = (
            0.0
            if total_lines_changed == 0
            else round((stats.total_lines_changed / total_lines_changed) * 100, 2)
        )
        files_touched_pct = (
            0.0
            if total_unique_files == 0
            else round((len(stats.unique_files) / total_unique_files) * 100, 2)
        )

        relative_metrics[author_email] = {
            "commit_pct": commit_pct,
            "lines_changed_pct": lines_changed_pct,
            "files_touched_pct": files_touched_pct,
        }

    return relative_metrics


def build_output_rows(stats_dict: Dict[str, AuthorStats]) -> List[Dict]:
    """
    Build list of output rows from statistics dictionary.

    Args:
        stats_dict: Dictionary of author statistics

    Returns:
        List of dictionaries ready for output
    """
    # Calculate relative metrics for all authors
    relative_metrics = calculate_relative_metrics(stats_dict)

    # Build rows
    rows = []
    for author_email in sorted(stats_dict.keys()):
        stats = stats_dict[author_email]
        rows.append(stats.to_dict(author_email, relative_metrics.get(author_email)))

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

    # Repository source
    parser.add_argument(
        "--repo",
        help="GitHub/GitLab repository URL (will clone temporarily if not local)",
    )

    # Scope options
    parser.add_argument(
        "--branch", help="Only analyze this branch/ref (default: all refs)"
    )

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

    # Add revision range (default to --all unless specific branch specified)
    if args.branch:
        common_args.append(args.branch)
    else:
        common_args.append("--all")

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

    # Handle repository cloning if URL provided
    temp_dir = None
    original_cwd = None
    working_dir = None

    try:
        if args.repo:
            # Validate URL
            if not is_valid_git_url(args.repo):
                sys.stderr.write(f"Error: Invalid Git repository URL: {args.repo}\n")
                sys.exit(1)

            # Create temporary directory and clone
            temp_dir = tempfile.mkdtemp(prefix="git-audit-")
            clone_repository(args.repo, temp_dir)
            working_dir = temp_dir
        else:
            # Use current directory
            working_dir = None

        # Build configuration
        pathspecs = build_pathspecs(args.exclude)

        # Build common git arguments
        common_args = build_common_git_args(args, pathspecs)

        # Gather all statistics
        # Note: run_git function already supports cwd parameter
        # We need to pass working_dir to gather_all_statistics
        stats_dict = gather_all_statistics(
            common_args=common_args,
            no_merges=args.no_merges,
            cwd=working_dir,
        )

        # Build output rows
        rows = build_output_rows(stats_dict)

        # Write output to stdout as CSV
        write_csv_output(rows, sys.stdout)

    finally:
        # Clean up temporary directory if created
        if temp_dir and os.path.exists(temp_dir):
            sys.stderr.write(f"Cleaning up temporary directory: {temp_dir}\n")
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
