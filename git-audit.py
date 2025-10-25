#!/usr/bin/env python3
"""
A fast, dependency-free extractor of per-developer evaluation indicators from Git.

The script automatically analyzes all branches and commits to generate comprehensive
developer evaluation indicators. No filtering is needed - the script intelligently
collects and processes the right data for accurate metrics.

Usage:
  python3 git-audit.py > indicators.csv
  python3 git-audit.py --repo https://github.com/user/repo.git > indicators.csv
  python3 git-audit.py --print
  python3 git-audit.py --print --output my_data.csv

Options:
  --repo URL : GitHub/GitLab repository URL (clones temporarily)
  --print : Save output to file and automatically generate analysis report
  --output FILE : Output CSV filename (default: output.csv)

Metrics (per author/email):
  Author info: author_name, author_email
  Base metrics: commits_non_merge, commits_merge, lines_added, lines_deleted,
    files_added, files_deleted, files_modified, files_binary, files_touched,
    days_active
  Aggregated metrics: commits_total, lines_total, files_total
  Calculated indicators: lines_per_commit_avg, commits_freq, lines_churn_ratio,
    files_per_commit_avg, days_span
  Relative metrics: commits_team_pct, lines_team_pct, files_team_pct
  Dates: commits_first_date, commits_last_date

Evaluation Indicators (0.0 to 1.0 scale):
  Productivity: prod_rel, prod_abs, prod_stat, prod_score
  Quality: quality_rel, quality_abs, quality_stat, quality_score
  Collaboration: collab_rel, collab_abs, collab_stat, collab_score
  Overall: overall_score

  Three normalization methods:
    - Relative: min-max within team
    - Absolute: predefined thresholds
    - Statistical: percentile-based
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

# ============================================================================
# EVALUATION INDICATOR THRESHOLDS (for absolute normalization)
# ============================================================================

# Productivity thresholds (excellent = high performance, poor = low performance)
PRODUCTIVITY_THRESHOLDS = {
    "commits_excellent": 50,
    "commits_poor": 5,
    "lines_excellent": 10000,
    "lines_poor": 500,
    "files_excellent": 100,
    "files_poor": 10,
    "active_days_excellent": 30,
    "active_days_poor": 3,
}

# Quality thresholds (note: some are inverted - lower is better)
QUALITY_THRESHOLDS = {
    "churn_ratio_excellent": 0.2,  # Lower is better (more new code)
    "churn_ratio_poor": 1.5,  # Higher is worse (more deletions)
    "commit_size_excellent_min": 50,  # Not too small
    "commit_size_excellent_max": 500,  # Not too large
    "commit_size_poor_min": 5,
    "commit_size_poor_max": 2000,
    "files_per_commit_excellent": 3,  # Focused commits
    "files_per_commit_poor": 15,  # Too scattered
    "merge_ratio_excellent": 0.1,  # Lower is better (fewer merge issues)
    "merge_ratio_poor": 0.4,  # Higher indicates complexity
}

# Collaboration thresholds
COLLABORATION_THRESHOLDS = {
    "merge_commits_excellent": 5,
    "merge_commits_poor": 0,
    "shared_files_pct_excellent": 50,  # % of files touched by others
    "shared_files_pct_poor": 10,
    "active_span_excellent": 60,  # Days of sustained engagement
    "active_span_poor": 7,
}

# Dimension weights (must sum to 1.0)
DIMENSION_WEIGHTS = {
    "productivity": 0.333,
    "quality": 0.333,
    "collaboration": 0.334,
}

OUTPUT_FIELDNAMES = [
    "author_name",
    "author_email",
    "commits_non_merge",
    "commits_merge",
    "commits_total",
    "lines_added",
    "lines_deleted",
    "lines_total",
    "files_added",
    "files_deleted",
    "files_modified",
    "files_binary",
    "files_total",
    "files_touched",
    "lines_per_commit_avg",
    "days_active",
    "commits_freq",
    "lines_churn_ratio",
    "files_per_commit_avg",
    "days_span",
    "commits_first_date",
    "commits_last_date",
    "commits_team_pct",
    "lines_team_pct",
    "files_team_pct",
    # Evaluation indicators - Productivity
    "prod_rel",
    "prod_abs",
    "prod_stat",
    "prod_score",
    # Evaluation indicators - Quality
    "quality_rel",
    "quality_abs",
    "quality_stat",
    "quality_score",
    # Evaluation indicators - Collaboration
    "collab_rel",
    "collab_abs",
    "collab_stat",
    "collab_score",
    # Overall aggregate score
    "overall_score",
]


# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass
class AuthorStats:
    """Aggregate statistics for a single author."""

    author_name: str = ""
    commits_non_merge: int = 0
    commits_merge: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    files_added: int = 0
    files_deleted: int = 0
    files_modified: int = 0
    files_binary: int = 0
    total_files_changed: int = 0
    days_active: Set[str] = field(default_factory=set)
    files: Set[str] = field(default_factory=set)
    commits_first_date: str = ""
    commits_last_date: str = ""

    @property
    def days_active_count(self) -> int:
        """Count of unique days with activity."""
        return len(self.days_active)

    @property
    def commits_total(self) -> int:
        """Total commits including merges."""
        return self.commits_non_merge + self.commits_merge

    @property
    def lines_total(self) -> int:
        """Total lines changed (additions + deletions)."""
        return self.lines_added + self.lines_deleted

    @property
    def lines_per_commit_avg(self) -> float:
        """Average lines changed per commit."""
        if self.commits_non_merge == 0:
            return 0.0
        return round(self.lines_total / self.commits_non_merge, 2)

    @property
    def commits_freq(self) -> float:
        """Commits per active day."""
        if self.days_active_count == 0:
            return 0.0
        return round(self.commits_non_merge / self.days_active_count, 2)

    @property
    def lines_churn_ratio(self) -> float:
        """Code churn ratio (deletions / additions). Lower = more new code."""
        if self.lines_added == 0:
            return 0.0
        return round(self.lines_deleted / self.lines_added, 2)

    @property
    def files_per_commit_avg(self) -> float:
        """Average files changed per commit."""
        if self.commits_non_merge == 0:
            return 0.0
        return round(self.total_files_changed / self.commits_non_merge, 2)

    @property
    def days_span(self) -> int:
        """Number of days between first and last commit."""
        if not self.commits_first_date or not self.commits_last_date:
            return 0
        try:
            from datetime import datetime

            first = datetime.strptime(self.commits_first_date, "%Y-%m-%d")
            last = datetime.strptime(self.commits_last_date, "%Y-%m-%d")
            return (last - first).days
        except (ValueError, TypeError):
            return 0

    def to_dict(
        self, author_email: str, relative_metrics: Optional[Dict] = None
    ) -> Dict:
        """
        Convert to dictionary for output.

        Args:
            author_email: Author email address
            relative_metrics: Optional dict with relative percentages and evaluation indicators
        """
        result = {
            "author_name": self.author_name,
            "author_email": author_email,
            "commits_non_merge": self.commits_non_merge,
            "commits_merge": self.commits_merge,
            "commits_total": self.commits_total,
            "lines_added": self.lines_added,
            "lines_deleted": self.lines_deleted,
            "lines_total": self.lines_total,
            "files_added": self.files_added,
            "files_deleted": self.files_deleted,
            "files_modified": self.files_modified,
            "files_binary": self.files_binary,
            "files_total": self.total_files_changed,
            "files_touched": len(self.files),
            "lines_per_commit_avg": self.lines_per_commit_avg,
            "days_active": self.days_active_count,
            "commits_freq": self.commits_freq,
            "lines_churn_ratio": self.lines_churn_ratio,
            "files_per_commit_avg": self.files_per_commit_avg,
            "days_span": self.days_span,
            "commits_first_date": self.commits_first_date,
            "commits_last_date": self.commits_last_date,
        }

        # Add relative metrics and evaluation indicators if provided
        if relative_metrics:
            result.update(relative_metrics)
        else:
            # Default values for relative metrics
            result.update(
                {
                    "commits_team_pct": 0.0,
                    "lines_team_pct": 0.0,
                    "files_team_pct": 0.0,
                }
            )
            # Default values for evaluation indicators
            result.update(
                {
                    "prod_rel": 0.0,
                    "prod_abs": 0.0,
                    "prod_stat": 0.0,
                    "prod_score": 0.0,
                    "quality_rel": 0.0,
                    "quality_abs": 0.0,
                    "quality_stat": 0.0,
                    "quality_score": 0.0,
                    "collab_rel": 0.0,
                    "collab_abs": 0.0,
                    "collab_stat": 0.0,
                    "collab_score": 0.0,
                    "overall_score": 0.0,
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
# EVALUATION INDICATORS - NORMALIZATION FUNCTIONS
# ============================================================================


def normalize_relative(value: float, values_list: List[float]) -> float:
    """
    Normalize value using min-max normalization relative to the team.

    Args:
        value: The value to normalize
        values_list: List of all values from the team

    Returns:
        Normalized value between 0.0 and 1.0
    """
    if not values_list or len(values_list) == 0:
        return 0.0

    min_val = min(values_list)
    max_val = max(values_list)

    if max_val == min_val:
        return 1.0 if value >= max_val else 0.0

    normalized = (value - min_val) / (max_val - min_val)
    return round(max(0.0, min(1.0, normalized)), 3)


def normalize_absolute(
    value: float, excellent: float, poor: float, inverted: bool = False
) -> float:
    """
    Normalize value using absolute thresholds.

    Args:
        value: The value to normalize
        excellent: Threshold for excellent performance
        poor: Threshold for poor performance
        inverted: If True, lower values are better (e.g., churn_ratio)

    Returns:
        Normalized value between 0.0 and 1.0
    """
    if inverted:
        # For inverted metrics (lower is better), swap the logic
        if value <= excellent:
            return 1.0
        elif value >= poor:
            return 0.0
        else:
            normalized = 1.0 - ((value - excellent) / (poor - excellent))
    else:
        # For normal metrics (higher is better)
        if value >= excellent:
            return 1.0
        elif value <= poor:
            return 0.0
        else:
            normalized = (value - poor) / (excellent - poor)

    return round(max(0.0, min(1.0, normalized)), 3)


def normalize_absolute_range(
    value: float,
    excellent_min: float,
    excellent_max: float,
    poor_min: float,
    poor_max: float,
) -> float:
    """
    Normalize value using absolute thresholds with an optimal range.
    Used for metrics where both too low and too high are bad (e.g., commit_size).

    Args:
        value: The value to normalize
        excellent_min: Lower bound of excellent range
        excellent_max: Upper bound of excellent range
        poor_min: Lower bound of poor range (below this is worst)
        poor_max: Upper bound of poor range (above this is worst)

    Returns:
        Normalized value between 0.0 and 1.0
    """
    # If in excellent range, score is 1.0
    if excellent_min <= value <= excellent_max:
        return 1.0

    # If below excellent range
    if value < excellent_min:
        if value <= poor_min:
            return 0.0
        else:
            normalized = (value - poor_min) / (excellent_min - poor_min)
            return round(max(0.0, min(1.0, normalized)), 3)

    # If above excellent range
    if value > excellent_max:
        if value >= poor_max:
            return 0.0
        else:
            normalized = 1.0 - ((value - excellent_max) / (poor_max - excellent_max))
            return round(max(0.0, min(1.0, normalized)), 3)

    return 1.0


def normalize_statistical(value: float, values_list: List[float]) -> float:
    """
    Normalize value using statistical percentile ranking.
    Handles outliers better than simple min-max.

    Args:
        value: The value to normalize
        values_list: List of all values from the team

    Returns:
        Normalized value between 0.0 and 1.0 (percentile rank)
    """
    if not values_list or len(values_list) == 0:
        return 0.0

    # Sort values
    sorted_values = sorted(values_list)

    # Find percentile rank
    count_below = sum(1 for v in sorted_values if v < value)
    count_equal = sum(1 for v in sorted_values if v == value)

    # Percentile rank formula: (count_below + 0.5 * count_equal) / total
    percentile = (count_below + 0.5 * count_equal) / len(sorted_values)

    return round(max(0.0, min(1.0, percentile)), 3)


# ============================================================================
# EVALUATION INDICATORS - DIMENSION CALCULATORS
# ============================================================================


def calculate_productivity_raw(stats: AuthorStats) -> float:
    """
    Calculate raw productivity indicator based on volume and consistency.

    Args:
        stats: Author statistics

    Returns:
        Raw productivity score (unnormalized)
    """
    # Component weights
    commit_weight = 0.40
    lines_weight = 0.30
    files_weight = 0.20
    days_active_weight = 0.10

    # Calculate components (raw values)
    commit_component = stats.commits_non_merge * commit_weight
    lines_component = stats.lines_total * lines_weight
    files_component = len(stats.files) * files_weight
    days_active_component = stats.days_active_count * days_active_weight

    # Sum weighted components
    raw_score = (
        commit_component + lines_component + files_component + days_active_component
    )

    return raw_score


def calculate_quality_raw(stats: AuthorStats) -> float:
    """
    Calculate raw quality indicator based on code practices.
    Lower churn, appropriate commit sizes, focused commits.

    Args:
        stats: Author statistics

    Returns:
        Raw quality score (unnormalized, 0-100 scale before normalization)
    """
    # Start with a base score of 100
    quality_score = 100.0

    # Component 1: Churn ratio (35% weight)
    # Lower is better: 0.0-0.2 is excellent, > 1.5 is poor
    churn = stats.lines_churn_ratio
    if churn <= 0.2:
        churn_score = 100
    elif churn >= 1.5:
        churn_score = 0
    else:
        churn_score = 100 * (1 - ((churn - 0.2) / (1.5 - 0.2)))

    # Component 2: Commit size (25% weight)
    # Optimal range: 50-500 lines per commit
    commit_size = stats.lines_per_commit_avg
    if 50 <= commit_size <= 500:
        size_score = 100
    elif commit_size < 50:
        size_score = max(0, 100 * (commit_size / 50))
    else:  # > 500
        size_score = max(0, 100 * (1 - ((commit_size - 500) / 1500)))

    # Component 3: Files per commit (25% weight)
    # Lower is better: 1-3 is excellent, > 15 is poor
    files_per = stats.files_per_commit_avg
    if files_per <= 3:
        files_score = 100
    elif files_per >= 15:
        files_score = 0
    else:
        files_score = 100 * (1 - ((files_per - 3) / (15 - 3)))

    # Component 4: Merge commit ratio (15% weight)
    # Lower is better
    if stats.commits_total > 0:
        merge_ratio = stats.commits_merge / stats.commits_total
    else:
        merge_ratio = 0

    if merge_ratio <= 0.1:
        merge_score = 100
    elif merge_ratio >= 0.4:
        merge_score = 0
    else:
        merge_score = 100 * (1 - ((merge_ratio - 0.1) / (0.4 - 0.1)))

    # Weighted sum
    quality_score = (
        churn_score * 0.35 + size_score * 0.25 + files_score * 0.25 + merge_score * 0.15
    )

    return quality_score


def calculate_collaboration_raw(stats: AuthorStats, shared_files_pct: float) -> float:
    """
    Calculate raw collaboration indicator.

    Args:
        stats: Author statistics
        shared_files_pct: Percentage of author's files touched by others

    Returns:
        Raw collaboration score (0-100 scale)
    """
    # Component 1: Merge activity (40% weight)
    # Having some merge commits indicates integration work
    merge_commits = stats.commits_merge
    if merge_commits >= 5:
        merge_score = 100
    elif merge_commits == 0:
        merge_score = 0
    else:
        merge_score = (merge_commits / 5) * 100

    # Component 2: Shared file ownership (35% weight)
    # Higher percentage means more collaboration
    if shared_files_pct >= 50:
        shared_score = 100
    elif shared_files_pct <= 10:
        shared_score = 0
    else:
        shared_score = ((shared_files_pct - 10) / (50 - 10)) * 100

    # Component 3: Active span consistency (25% weight)
    # Longer engagement indicates sustained collaboration
    active_span = stats.days_span
    if active_span >= 60:
        span_score = 100
    elif active_span <= 7:
        span_score = 0
    else:
        span_score = ((active_span - 7) / (60 - 7)) * 100

    # Weighted sum
    collaboration_score = merge_score * 0.40 + shared_score * 0.35 + span_score * 0.25

    return collaboration_score


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
            # Store author name (use first occurrence)
            if not stats.author_name:
                stats.author_name = author_name
            stats.commits_non_merge += 1
            stats.days_active.add(commit_date)

            if not stats.commits_first_date:
                stats.commits_first_date = commit_date
            stats.commits_last_date = commit_date

        # Parse numstat line (additions, deletions, filename)
        elif line and current_commit and line.count("\t") == 2:
            additions, deletions, filepath = line.split("\t")
            author_email = current_commit[2]
            stats = stats_dict[author_email]

            # Binary files show as "- -" in numstat
            if additions == "-" and deletions == "-":
                stats.files_binary += 1
            else:
                # Text files: count line changes
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

            stats.total_files_changed += 1


def calculate_file_operations(
    common_args: List[str],
    stats_dict: Dict[str, AuthorStats],
    cwd: Optional[str] = None,
) -> None:
    """
    Calculate file operation types (added/deleted/modified) for each author.

    Args:
        common_args: Common git log arguments (refs, dates, pathspecs)
        stats_dict: Dictionary to update with statistics
        cwd: Working directory for git commands
    """
    log_args = ["log"] + common_args + ["--name-status", "--no-merges", "--format=%ae"]

    output = run_git(log_args, cwd=cwd)
    current_author: Optional[str] = None

    for line in output.splitlines():
        # Heuristic: lines with @ and . but no spaces or slashes are likely emails
        if "@" in line and "." in line and " " not in line and "/" not in line:
            current_author = normalize_author(line.strip())
            if current_author not in stats_dict:
                stats_dict[current_author] = AuthorStats()
        # Parse status lines (format: "A\tfilename" or "M\tfilename" or "D\tfilename")
        elif line and current_author and "\t" in line:
            status = line.split("\t")[0].strip()
            stats = stats_dict[current_author]

            # A = Added, M = Modified, D = Deleted
            # R = Renamed (count as modified), C = Copied (count as added)
            if status.startswith("A") or status.startswith("C"):
                stats.files_added += 1
            elif status.startswith("D"):
                stats.files_deleted += 1
            elif status.startswith("M") or status.startswith("R"):
                stats.files_modified += 1


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
        stats_dict[author_email].commits_merge += 1


def calculate_files_touched(
    common_args: List[str],
    no_merges: bool,
    stats_dict: Dict[str, AuthorStats],
    cwd: Optional[str] = None,
) -> None:
    """
    Calculate files touched by each author.

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
            stats_dict[current_author].files.add(line.strip())


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

    # Calculate file operations (added/deleted/modified)
    calculate_file_operations(common_args, stats_dict, cwd=cwd)

    # Calculate files touched
    calculate_files_touched(common_args, no_merges, stats_dict, cwd=cwd)

    return stats_dict


# ============================================================================
# ANALYSIS AND PLOTTING FUNCTIONS
# ============================================================================


def print_summary_report(data: List[Dict]) -> None:
    """Print a summary report of developer indicators."""
    print("=" * 80)
    print("DEVELOPER EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Total Developers: {len(data)}\n")

    # Sort by overall score
    sorted_data = sorted(data, key=lambda x: float(x["overall_score"]), reverse=True)

    print("OVERALL RANKINGS:")
    print("-" * 80)
    for i, dev in enumerate(sorted_data, 1):
        overall = float(dev["overall_score"])
        prod = float(dev["prod_score"])
        qual = float(dev["quality_score"])
        collab = float(dev["collab_score"])

        print(f"{i:2d}. {dev['author']:40s} | Overall: {overall:.3f}")
        print(
            f"    Productivity: {prod:.3f} | Quality: {qual:.3f} | "
            f"Collaboration: {collab:.3f}"
        )
        print()


def analyze_dimension(data: List[Dict], dimension: str) -> None:
    """Analyze a specific dimension across normalization methods."""
    print(f"\n{dimension.upper()} DIMENSION ANALYSIS:")
    print("=" * 80)

    fields = [
        f"{dimension}_relative",
        f"{dimension}_absolute",
        f"{dimension}_statistical",
        f"{dimension}_score",
    ]

    for field_name in fields:
        values = [float(row[field_name]) for row in data]
        avg = sum(values) / len(values)
        min_val = min(values)
        max_val = max(values)

        # Find top performer
        top = max(data, key=lambda x: float(x[field_name]))

        method = field_name.split("_")[-1].capitalize()
        norm_method = f"{method:15s}"
        range_str = f"Range=[{min_val:.3f}, {max_val:.3f}]"
        print(f"\n{norm_method}: Avg={avg:.3f}, {range_str}")
        print(f"  Top: {top['author']} ({float(top[field_name]):.3f})")


def compare_normalizations(data: List[Dict], author: str) -> None:
    """Compare normalization methods for a specific author."""
    dev = next((d for d in data if d["author"] == author), None)
    if not dev:
        print(f"Author '{author}' not found")
        return

    print(f"\nNORMALIZATION COMPARISON FOR: {author}")
    print("=" * 80)

    for dimension in ["productivity", "quality", "collaboration"]:
        print(f"\n{dimension.capitalize()}:")
        rel = float(dev[f"{dimension}_relative"])
        abs_ = float(dev[f"{dimension}_absolute"])
        stat = float(dev[f"{dimension}_statistical"])
        score = float(dev[f"{dimension}_score"])

        print(f"  Relative:    {rel:.3f}")
        print(f"  Absolute:    {abs_:.3f}")
        print(f"  Statistical: {stat:.3f}")
        print(f"  → Average:   {score:.3f}")


def identify_strengths_weaknesses(data: List[Dict]) -> None:
    """Identify top performers in each dimension."""
    print("\n" + "=" * 80)
    print("DIMENSION LEADERS:")
    print("=" * 80)

    dimensions = [
        ("Productivity", "prod_score"),
        ("Quality", "quality_score"),
        ("Collaboration", "collab_score"),
    ]

    for name, field_key in dimensions:
        top = max(data, key=lambda x: float(x[field_key]))
        score = float(top[field_key])
        print(f"\n{name:15s}: {top['author']:40s} ({score:.3f})")


def generate_analysis_report(rows: List[Dict]) -> None:
    """Generate complete analysis report from statistics rows."""
    if not rows:
        print("No data to analyze")
        return

    # Print various analyses
    print_summary_report(rows)
    analyze_dimension(rows, "productivity")
    analyze_dimension(rows, "quality")
    analyze_dimension(rows, "collaboration")
    identify_strengths_weaknesses(rows)

    # Compare normalizations for first author
    if rows:
        compare_normalizations(rows, rows[0]["author"])

    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)


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
    total_commits = sum(s.commits_total for s in stats_dict.values())
    total_lines = sum(s.lines_total for s in stats_dict.values())

    # Get all unique files across all authors
    all_files = set()
    for stats in stats_dict.values():
        all_files.update(stats.files)
    total_files = len(all_files)

    # Calculate percentages for each author
    relative_metrics = {}
    for author_email, stats in stats_dict.items():
        commits_team_pct = (
            0.0
            if total_commits == 0
            else round((stats.commits_total / total_commits) * 100, 2)
        )
        lines_team_pct = (
            0.0
            if total_lines == 0
            else round((stats.lines_total / total_lines) * 100, 2)
        )
        files_team_pct = (
            0.0
            if total_files == 0
            else round((len(stats.files) / total_files) * 100, 2)
        )

        relative_metrics[author_email] = {
            "commits_team_pct": commits_team_pct,
            "lines_team_pct": lines_team_pct,
            "files_team_pct": files_team_pct,
        }

    return relative_metrics


def calculate_shared_files_percentage(
    author_files: Set[str],
    all_authors_stats: Dict[str, AuthorStats],
    current_author: str,
) -> float:
    """
    Calculate what percentage of an author's files are also touched by others.

    Args:
        author_files: Set of files touched by the author
        all_authors_stats: Dictionary of all author statistics
        current_author: Current author email to exclude from comparison

    Returns:
        Percentage of shared files (0-100)
    """
    if not author_files:
        return 0.0

    # Find files touched by other authors
    other_authors_files = set()
    for author_email, stats in all_authors_stats.items():
        if author_email != current_author:
            other_authors_files.update(stats.files)

    # Count how many of current author's files are also in others' files
    shared_files = author_files.intersection(other_authors_files)
    shared_pct = (len(shared_files) / len(author_files)) * 100

    return round(shared_pct, 2)


def calculate_evaluation_indicators(
    stats_dict: Dict[str, AuthorStats],
) -> Dict[str, Dict]:
    """
    Calculate evaluation indicators for all authors across three dimensions
    with three normalization methods each.

    Args:
        stats_dict: Dictionary of author statistics

    Returns:
        Dictionary mapping author emails to their evaluation indicators
    """
    evaluation_indicators = {}

    # Step 1: Calculate raw dimension scores for all authors
    productivity_raw = {}
    quality_raw = {}
    collaboration_raw = {}

    for author_email, stats in stats_dict.items():
        # Calculate shared files percentage for collaboration
        shared_files_pct = calculate_shared_files_percentage(
            stats.files, stats_dict, author_email
        )

        # Calculate raw scores
        productivity_raw[author_email] = calculate_productivity_raw(stats)
        quality_raw[author_email] = calculate_quality_raw(stats)
        collaboration_raw[author_email] = calculate_collaboration_raw(
            stats, shared_files_pct
        )

    # Step 2: Prepare lists for normalization
    productivity_values = list(productivity_raw.values())
    quality_values = list(quality_raw.values())
    collaboration_values = list(collaboration_raw.values())

    # Step 3: Calculate normalized scores for each author
    for author_email, stats in stats_dict.items():
        # Get raw scores
        prod_raw = productivity_raw[author_email]
        qual_raw = quality_raw[author_email]
        collab_raw = collaboration_raw[author_email]

        # --- PRODUCTIVITY INDICATORS ---
        # Relative (min-max within team)
        productivity_relative = normalize_relative(prod_raw, productivity_values)

        # Absolute (predefined thresholds)
        # For productivity, we use a simplified threshold based on commits
        prod_absolute = normalize_absolute(
            stats.commits_non_merge,
            PRODUCTIVITY_THRESHOLDS["commits_excellent"],
            PRODUCTIVITY_THRESHOLDS["commits_poor"],
            inverted=False,
        )

        # Statistical (percentile)
        productivity_statistical = normalize_statistical(prod_raw, productivity_values)

        # Average productivity score
        productivity_score = round(
            (productivity_relative + prod_absolute + productivity_statistical) / 3, 3
        )

        # --- QUALITY INDICATORS ---
        # Relative (min-max within team)
        quality_relative = normalize_relative(qual_raw, quality_values)

        # Absolute (already calculated in 0-100 scale, normalize to 0-1)
        quality_absolute = round(qual_raw / 100, 3)

        # Statistical (percentile)
        quality_statistical = normalize_statistical(qual_raw, quality_values)

        # Average quality score
        quality_score = round(
            (quality_relative + quality_absolute + quality_statistical) / 3, 3
        )

        # --- COLLABORATION INDICATORS ---
        # Relative (min-max within team)
        collaboration_relative = normalize_relative(collab_raw, collaboration_values)

        # Absolute (already calculated in 0-100 scale, normalize to 0-1)
        collaboration_absolute = round(collab_raw / 100, 3)

        # Statistical (percentile)
        collaboration_statistical = normalize_statistical(
            collab_raw, collaboration_values
        )

        # Average collaboration score
        collaboration_score = round(
            (
                collaboration_relative
                + collaboration_absolute
                + collaboration_statistical
            )
            / 3,
            3,
        )

        # --- OVERALL AGGREGATE SCORE ---
        developer_score_overall = round(
            (
                productivity_score * DIMENSION_WEIGHTS["productivity"]
                + quality_score * DIMENSION_WEIGHTS["quality"]
                + collaboration_score * DIMENSION_WEIGHTS["collaboration"]
            ),
            3,
        )

        # Store all indicators
        evaluation_indicators[author_email] = {
            # Productivity
            "prod_rel": productivity_relative,
            "prod_abs": prod_absolute,
            "prod_stat": productivity_statistical,
            "prod_score": productivity_score,
            # Quality
            "quality_rel": quality_relative,
            "quality_abs": quality_absolute,
            "quality_stat": quality_statistical,
            "quality_score": quality_score,
            # Collaboration
            "collab_rel": collaboration_relative,
            "collab_abs": collaboration_absolute,
            "collab_stat": collaboration_statistical,
            "collab_score": collaboration_score,
            # Overall
            "overall_score": developer_score_overall,
        }

    return evaluation_indicators


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

    # Calculate evaluation indicators for all authors
    evaluation_indicators = calculate_evaluation_indicators(stats_dict)

    # Build rows
    rows = []
    for author_email in sorted(stats_dict.keys()):
        stats = stats_dict[author_email]
        # Merge relative metrics and evaluation indicators
        combined_metrics = {
            **relative_metrics.get(author_email, {}),
            **evaluation_indicators.get(author_email, {}),
        }
        rows.append(stats.to_dict(author_email, combined_metrics))

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
        description="Extract per-developer evaluation indicators from a Git repository",
        epilog="The script automatically analyzes all branches and commits to generate "
        "accurate evaluation indicators. No filtering options are needed.",
    )

    # Repository source
    parser.add_argument(
        "--repo",
        help="GitHub/GitLab repository URL (will clone temporarily)",
    )

    # Print/analysis option
    parser.add_argument(
        "--print",
        action="store_true",
        help="Save output to file and automatically generate analysis report",
    )

    parser.add_argument(
        "--output",
        default="output.csv",
        help="Output CSV filename (default: output.csv). Used with --print or standalone.",
    )

    return parser.parse_args()


def build_common_git_args() -> List[str]:
    """
    Build common git log arguments for indicator generation.

    Returns:
        List of git arguments to use across multiple git commands.
        Always analyzes all branches for comprehensive indicators.
    """
    # Always analyze all branches and commits for accurate indicators
    return ["--all"]


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main() -> None:
    """Main entry point for the script."""
    # Parse arguments
    args = parse_arguments()

    # Handle repository cloning if URL provided
    temp_dir = None
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

        # Build common git arguments (always analyze all branches)
        common_args = build_common_git_args()

        # Gather all statistics (no filtering - full data for accurate indicators)
        stats_dict = gather_all_statistics(
            common_args=common_args,
            no_merges=False,  # Always include merge commits for collaboration metrics
            cwd=working_dir,
        )

        # Build output rows
        rows = build_output_rows(stats_dict)

        # Determine output destination
        output_arg = hasattr(args, "output") and args.output != "output.csv"
        if args.print or output_arg:
            # Write to file
            output_file = args.output
            sys.stderr.write(f"Writing output to: {output_file}\n")
            with open(output_file, "w", newline="") as f:
                write_csv_output(rows, f)
            sys.stderr.write(f"Output saved to: {output_file}\n")

            # If --print specified, generate analysis report
            if args.print:
                sys.stderr.write("\n")
                try:
                    generate_analysis_report(rows)
                except Exception as e:
                    sys.stderr.write(f"Error generating analysis: {e}\n")
        else:
            # Write output to stdout as CSV
            write_csv_output(rows, sys.stdout)

    finally:
        # Clean up temporary directory if created
        if temp_dir and os.path.exists(temp_dir):
            sys.stderr.write(f"Cleaning up temporary directory: {temp_dir}\n")
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
