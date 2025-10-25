#!/usr/bin/env python3
"""
Enhanced developer evaluation tool with academic research-backed improvements.

Generates 68 comprehensive metrics per developer, including:
- File type categorization (code/docs/config with weighted productivity)
- Bug fix detection (maintenance vs. feature work classification)
- Code review participation tracking (Reviewed-by, Co-authored-by trailers)
- Dynamic threshold calibration (adapts to team size and context)
- Multi-dimensional assessment (productivity, quality, collaboration)

Usage:
  python3 git-audit.py > output.csv
  python3 git-audit.py --repo https://github.com/user/repo.git > output.csv
  python3 git-audit.py --print
  python3 git-audit.py --print --output team_analysis.csv

Options:
  --repo URL : GitHub/GitLab repository URL (clones temporarily)
  --print : Save CSV and generate analysis report
  --output FILE : Output CSV filename (default: output.csv)

Metrics Overview (68 total):

Author Information (2):
  author_name, author_email

Commits Domain (9):
  commits_non_merge, commits_merge, commits_bugfix, commits_feature, commits_total,
  commits_bugfix_ratio, commits_coauthored, commits_freq, commits_team_pct

Lines Domain - Totals (6):
  lines_added, lines_deleted, lines_total, lines_per_commit_avg,
  lines_churn_ratio, lines_team_pct

Lines Domain - By Type (9):
  lines_code_added, lines_code_deleted, lines_code_total,
  lines_docs_added, lines_docs_deleted, lines_docs_total,
  lines_config_added, lines_config_deleted, lines_config_total

Files Domain - Totals (8):
  files_added, files_deleted, files_modified, files_binary,
  files_total, files_touched, files_per_commit_avg, files_team_pct

Files Domain - By Type (12):
  files_code_added, files_code_deleted, files_code_modified, files_code_total,
  files_docs_added, files_docs_deleted, files_docs_modified, files_docs_total,
  files_config_added, files_config_deleted, files_config_modified, files_config_total

Days Domain (4):
  days_active, days_span, commits_first_date, commits_last_date

Collaboration (1):
  reviews_given

Evaluation Indicators (13):
  Productivity: prod_rel, prod_abs, prod_stat, prod_score
  Quality: quality_rel, quality_abs, quality_stat, quality_score
  Collaboration: collab_rel, collab_abs, collab_stat, collab_score

Overall Score (1):
  overall_score (weighted: 33.3% productivity, 33.3% quality, 33.4% collaboration)

Key Features:
  ✅ File Type Weighting: Code 100%, Docs 50%, Config 30%
  ✅ Bug Fix Detection: Patterns like 'fix', 'bug', 'issue #', 'hotfix'
  ✅ Code Review Credits: Reviewed-by, Co-authored-by, Acked-by trailers
  ✅ Dynamic Thresholds: 90th percentile = excellent, 25th = poor (team-adapted)
  ✅ Multi-Method Normalization: Averages relative, absolute, statistical

See METHODOLOGY.md for academic research foundation and design rationale.
See METRICS.md for complete documentation of all 68 metrics.
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

GIT_LOG_FORMAT_HEADER = "%H%x09%an%x09%ae%x09%ad%n%B%n--END-COMMIT--"
GIT_DATE_FORMAT_SHORT = "--date=short"

# Dimension weights (must sum to 1.0)
DIMENSION_WEIGHTS = {
    "productivity": 0.333,
    "quality": 0.333,
    "collaboration": 0.334,
}

OUTPUT_FIELDNAMES = [
    # Author information
    "author_name",
    "author_email",
    # Commits domain
    "commits_non_merge",
    "commits_merge",
    "commits_bugfix",
    "commits_feature",
    "commits_total",
    "commits_bugfix_ratio",
    "commits_coauthored",
    # Lines domain - totals
    "lines_added",
    "lines_deleted",
    "lines_total",
    # Lines domain - by type
    "lines_code_added",
    "lines_code_deleted",
    "lines_code_total",
    "lines_docs_added",
    "lines_docs_deleted",
    "lines_docs_total",
    "lines_config_added",
    "lines_config_deleted",
    "lines_config_total",
    # Files domain - totals
    "files_added",
    "files_deleted",
    "files_modified",
    "files_binary",
    "files_total",
    "files_touched",
    # Files domain - by type
    "files_code_added",
    "files_code_deleted",
    "files_code_modified",
    "files_code_total",
    "files_docs_added",
    "files_docs_deleted",
    "files_docs_modified",
    "files_docs_total",
    "files_config_added",
    "files_config_deleted",
    "files_config_modified",
    "files_config_total",
    # Calculated metrics
    "lines_per_commit_avg",
    "files_per_commit_avg",
    "commits_freq",
    "lines_churn_ratio",
    # Days domain
    "days_active",
    "days_span",
    "commits_first_date",
    "commits_last_date",
    # Collaboration
    "reviews_given",
    # Relative metrics
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
# FILE CATEGORIZATION
# ============================================================================

# File extensions for categorization
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".kts",
    ".scala",
    ".m",
    ".mm",
    ".pl",
    ".pm",
    ".r",
    ".R",
    ".dart",
    ".lua",
    ".sh",
    ".bash",
    ".sql",
    ".htm",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".vue",
    ".svelte",
    ".ex",
    ".exs",
    ".erl",
    ".hrl",
    ".clj",
    ".cljs",
    ".hs",
    ".elm",
    ".ml",
    ".fs",
    ".fsx",
    ".vb",
    ".asm",
    ".s",
}

DOCS_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".adoc",
    ".asciidoc",
    ".tex",
    ".org",
    ".rtf",
    ".pdf",
    ".doc",
    ".docx",
    ".odt",
}

CONFIG_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".config",
    ".properties",
    ".env",
    ".editorconfig",
    ".gitignore",
    ".dockerignore",
    ".eslintrc",
    ".prettierrc",
    ".babelrc",
    ".npmrc",
    ".gemfile",
    "Gemfile.lock",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "Cargo.toml",
    "Cargo.lock",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    "Makefile",
    "CMakeLists.txt",
}


def categorize_file(filename: str) -> str:
    """
    Categorize a file as 'code', 'docs', 'config', or 'other'.

    Args:
        filename: File path or name

    Returns:
        Category string: 'code', 'docs', 'config', or 'other'
    """
    filename_lower = filename.lower()

    # Check for specific filenames (case-insensitive)
    basename = filename_lower.split("/")[-1]
    if basename in {"makefile", "dockerfile", "rakefile", "gemfile", "vagrantfile"}:
        return "config"
    if basename in {"readme", "license", "contributing", "changelog", "authors"}:
        return "docs"

    # Check extension
    for ext in CODE_EXTENSIONS:
        if filename_lower.endswith(ext):
            return "code"

    for ext in DOCS_EXTENSIONS:
        if filename_lower.endswith(ext):
            return "docs"

    for ext in CONFIG_EXTENSIONS:
        if filename_lower.endswith(ext):
            return "config"

    # Default to 'other' (could be binary, test data, etc.)
    return "other"


# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass
class AuthorStats:
    """Aggregate statistics for a single author."""

    author_name: str = ""
    commits_non_merge: int = 0
    commits_merge: int = 0
    commits_bugfix: int = 0

    # Lines by type
    lines_added: int = 0
    lines_deleted: int = 0
    lines_code_added: int = 0
    lines_code_deleted: int = 0
    lines_docs_added: int = 0
    lines_docs_deleted: int = 0
    lines_config_added: int = 0
    lines_config_deleted: int = 0

    # Files by operation
    files_added: int = 0
    files_deleted: int = 0
    files_modified: int = 0
    files_binary: int = 0

    # Files by type and operation
    files_code_added: int = 0
    files_code_deleted: int = 0
    files_code_modified: int = 0
    files_docs_added: int = 0
    files_docs_deleted: int = 0
    files_docs_modified: int = 0
    files_config_added: int = 0
    files_config_deleted: int = 0
    files_config_modified: int = 0

    # Collaboration
    reviews_given: int = 0
    commits_coauthored: int = 0

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

    @property
    def commits_feature(self) -> int:
        """Feature/development commits (non-merge, non-bugfix)."""
        return max(0, self.commits_non_merge - self.commits_bugfix)

    @property
    def commits_bugfix_ratio(self) -> float:
        """Percentage of commits that are bug fixes."""
        if self.commits_non_merge == 0:
            return 0.0
        return round((self.commits_bugfix / self.commits_non_merge) * 100, 2)

    @property
    def lines_code_total(self) -> int:
        """Total code lines changed."""
        return self.lines_code_added + self.lines_code_deleted

    @property
    def lines_docs_total(self) -> int:
        """Total documentation lines changed."""
        return self.lines_docs_added + self.lines_docs_deleted

    @property
    def lines_config_total(self) -> int:
        """Total configuration lines changed."""
        return self.lines_config_added + self.lines_config_deleted

    @property
    def files_code_total(self) -> int:
        """Total code files changed."""
        return (
            self.files_code_added + self.files_code_deleted + self.files_code_modified
        )

    @property
    def files_docs_total(self) -> int:
        """Total documentation files changed."""
        return (
            self.files_docs_added + self.files_docs_deleted + self.files_docs_modified
        )

    @property
    def files_config_total(self) -> int:
        """Total configuration files changed."""
        return (
            self.files_config_added
            + self.files_config_deleted
            + self.files_config_modified
        )

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
            # Author information
            "author_name": self.author_name,
            "author_email": author_email,
            # Commits domain
            "commits_non_merge": self.commits_non_merge,
            "commits_merge": self.commits_merge,
            "commits_bugfix": self.commits_bugfix,
            "commits_feature": self.commits_feature,
            "commits_total": self.commits_total,
            "commits_bugfix_ratio": self.commits_bugfix_ratio,
            "commits_coauthored": self.commits_coauthored,
            # Lines domain - totals
            "lines_added": self.lines_added,
            "lines_deleted": self.lines_deleted,
            "lines_total": self.lines_total,
            # Lines domain - by type
            "lines_code_added": self.lines_code_added,
            "lines_code_deleted": self.lines_code_deleted,
            "lines_code_total": self.lines_code_total,
            "lines_docs_added": self.lines_docs_added,
            "lines_docs_deleted": self.lines_docs_deleted,
            "lines_docs_total": self.lines_docs_total,
            "lines_config_added": self.lines_config_added,
            "lines_config_deleted": self.lines_config_deleted,
            "lines_config_total": self.lines_config_total,
            # Files domain - totals
            "files_added": self.files_added,
            "files_deleted": self.files_deleted,
            "files_modified": self.files_modified,
            "files_binary": self.files_binary,
            "files_total": self.total_files_changed,
            "files_touched": len(self.files),
            # Files domain - by type
            "files_code_added": self.files_code_added,
            "files_code_deleted": self.files_code_deleted,
            "files_code_modified": self.files_code_modified,
            "files_code_total": self.files_code_total,
            "files_docs_added": self.files_docs_added,
            "files_docs_deleted": self.files_docs_deleted,
            "files_docs_modified": self.files_docs_modified,
            "files_docs_total": self.files_docs_total,
            "files_config_added": self.files_config_added,
            "files_config_deleted": self.files_config_deleted,
            "files_config_modified": self.files_config_modified,
            "files_config_total": self.files_config_total,
            # Calculated metrics
            "lines_per_commit_avg": self.lines_per_commit_avg,
            "files_per_commit_avg": self.files_per_commit_avg,
            "commits_freq": self.commits_freq,
            "lines_churn_ratio": self.lines_churn_ratio,
            # Days domain
            "days_active": self.days_active_count,
            "days_span": self.days_span,
            "commits_first_date": self.commits_first_date,
            "commits_last_date": self.commits_last_date,
            # Collaboration
            "reviews_given": self.reviews_given,
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
# DYNAMIC THRESHOLD CALIBRATION
# ============================================================================


def calculate_dynamic_thresholds(stats_dict: Dict[str, "AuthorStats"]) -> Dict:
    """
    Calculate dynamic thresholds based on team distribution.
    Uses percentiles to adapt to repository context instead of fixed values.

    Args:
        stats_dict: Dictionary of author statistics

    Returns:
        Dictionary of dynamic thresholds for absolute normalization
    """
    # Extract values for all authors
    commits_values = [
        s.commits_non_merge for s in stats_dict.values() if s.commits_non_merge > 0
    ]
    merge_commits_values = [s.commits_merge for s in stats_dict.values()]

    # Calculate percentiles (25th = poor, 90th = excellent)
    def safe_percentile(values, p, default):
        if not values:
            return default
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * p / 100)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    p25_commits = safe_percentile(commits_values, 25, 5)
    p90_commits = safe_percentile(commits_values, 90, 50)

    p25_merges = safe_percentile(merge_commits_values, 25, 0)
    p90_merges = safe_percentile(merge_commits_values, 90, 5)

    # Return thresholds adapted to team context
    thresholds = {
        # Productivity: Dynamic based on team distribution
        "commits_excellent": max(p90_commits, 10),  # At least 10
        "commits_poor": max(p25_commits, 1),  # At least 1
        # Collaboration: Dynamic merge commits
        "merge_commits_excellent": max(p90_merges, 3),  # At least 3
        "merge_commits_poor": max(p25_merges, 0),  # At least 0
    }

    return thresholds


# ============================================================================
# EVALUATION INDICATORS - DIMENSION CALCULATORS
# ============================================================================


def calculate_productivity_raw(stats: AuthorStats) -> float:
    """
    Calculate raw productivity indicator based on volume and consistency.
    Weights code contributions higher than docs/config.

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

    # File type weights (code > docs > config)
    code_weight = 1.0
    docs_weight = 0.5
    config_weight = 0.3

    # Calculate weighted lines
    weighted_lines = (
        stats.lines_code_total * code_weight
        + stats.lines_docs_total * docs_weight
        + stats.lines_config_total * config_weight
    )

    # Calculate weighted files
    weighted_files = (
        stats.files_code_total * code_weight
        + stats.files_docs_total * docs_weight
        + stats.files_config_total * config_weight
    )

    # Calculate components (raw values)
    commit_component = stats.commits_non_merge * commit_weight
    lines_component = weighted_lines * lines_weight
    files_component = weighted_files * files_weight
    days_active_component = stats.days_active_count * days_active_weight

    # Sum weighted components
    raw_score = (
        commit_component + lines_component + files_component + days_active_component
    )

    return raw_score


def calculate_quality_raw(stats: AuthorStats) -> float:
    """
    Calculate raw quality indicator based on code practices.
    Lower churn, appropriate commit sizes, focused commits, and bug fix responsiveness.

    Args:
        stats: Author statistics

    Returns:
        Raw quality score (unnormalized, 0-100 scale before normalization)
    """
    # Component 1: Churn ratio (30% weight)
    # Lower is better: 0.0-0.2 is excellent, > 1.5 is poor
    churn = stats.lines_churn_ratio
    if churn <= 0.2:
        churn_score = 100
    elif churn >= 1.5:
        churn_score = 0
    else:
        churn_score = 100 * (1 - ((churn - 0.2) / (1.5 - 0.2)))

    # Component 2: Commit size (20% weight)
    # Optimal range: 50-500 lines per commit
    commit_size = stats.lines_per_commit_avg
    if 50 <= commit_size <= 500:
        size_score = 100
    elif commit_size < 50:
        size_score = max(0, 100 * (commit_size / 50))
    else:  # > 500
        size_score = max(0, 100 * (1 - ((commit_size - 500) / 1500)))

    # Component 3: Files per commit (20% weight)
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

    # Component 5: Bug fix ratio (15% weight)
    # Moderate is best: shows responsiveness without being all reactive
    # 15-35% is optimal range
    bugfix_ratio = stats.commits_bugfix_ratio
    if 15 <= bugfix_ratio <= 35:
        bugfix_score = 100
    elif bugfix_ratio < 15:
        bugfix_score = max(0, 100 * (bugfix_ratio / 15))
    elif bugfix_ratio > 35:
        bugfix_score = max(0, 100 * (1 - ((bugfix_ratio - 35) / 65)))
    else:
        bugfix_score = 50

    # Weighted sum
    quality_score = (
        churn_score * 0.30
        + size_score * 0.20
        + files_score * 0.20
        + merge_score * 0.15
        + bugfix_score * 0.15
    )

    return quality_score


def calculate_collaboration_raw(stats: AuthorStats, shared_files_pct: float) -> float:
    """
    Calculate raw collaboration indicator including code review participation.

    Args:
        stats: Author statistics
        shared_files_pct: Percentage of author's files touched by others

    Returns:
        Raw collaboration score (0-100 scale)
    """
    # Component 1: Merge activity (30% weight)
    # Having some merge commits indicates integration work
    merge_commits = stats.commits_merge
    if merge_commits >= 5:
        merge_score = 100
    elif merge_commits == 0:
        merge_score = 0
    else:
        merge_score = (merge_commits / 5) * 100

    # Component 2: Shared file ownership (30% weight)
    # Higher percentage means more collaboration
    if shared_files_pct >= 50:
        shared_score = 100
    elif shared_files_pct <= 10:
        shared_score = 0
    else:
        shared_score = ((shared_files_pct - 10) / (50 - 10)) * 100

    # Component 3: Code review participation (20% weight)
    # Reviews given and co-authored commits indicate collaboration
    review_participation = stats.reviews_given + stats.commits_coauthored
    if review_participation >= 10:
        review_score = 100
    elif review_participation == 0:
        review_score = 0
    else:
        review_score = (review_participation / 10) * 100

    # Component 4: Active span consistency (20% weight)
    # Longer engagement indicates sustained collaboration
    active_span = stats.days_span
    if active_span >= 60:
        span_score = 100
    elif active_span <= 7:
        span_score = 0
    else:
        span_score = ((active_span - 7) / (60 - 7)) * 100

    # Weighted sum
    collaboration_score = (
        merge_score * 0.30
        + shared_score * 0.30
        + review_score * 0.20
        + span_score * 0.20
    )

    return collaboration_score


# ============================================================================
# STATISTICS GATHERING
# ============================================================================


def is_bugfix_commit(message: str) -> bool:
    """
    Detect if a commit is a bug fix based on commit message patterns.

    Args:
        message: Commit message text

    Returns:
        True if commit appears to be a bug fix
    """
    message_lower = message.lower()
    bugfix_patterns = [
        "fix",
        "bug",
        "issue #",
        "issues #",
        "#",
        "hotfix",
        "patch",
        "resolve",
        "closes #",
        "close #",
        "fixes #",
        "fixed #",
        "repair",
        "correct",
        "defect",
    ]
    return any(pattern in message_lower for pattern in bugfix_patterns)


def extract_review_credits(
    message: str, author_email: str, stats_dict: Dict[str, AuthorStats]
) -> None:
    """
    Extract code review participation from commit message trailers.

    Args:
        message: Commit message text
        author_email: Primary commit author
        stats_dict: Dictionary to update with review credits
    """
    # Parse trailers like "Reviewed-by: Name <email>"
    review_patterns = [
        r"Reviewed-by:\s*(?:[^<]*<)?([^>@\s]+@[^>\s]+)",
        r"Co-authored-by:\s*(?:[^<]*<)?([^>@\s]+@[^>\s]+)",
        r"Acked-by:\s*(?:[^<]*<)?([^>@\s]+@[^>\s]+)",
    ]

    for pattern in review_patterns:
        matches = re.findall(pattern, message, re.IGNORECASE | re.MULTILINE)
        for email in matches:
            reviewer_email = normalize_author(email.strip())
            if reviewer_email != author_email:
                # Credit the reviewer
                if reviewer_email not in stats_dict:
                    stats_dict[reviewer_email] = AuthorStats()

                if "co-authored-by" in pattern.lower():
                    stats_dict[author_email].commits_coauthored += 1
                    stats_dict[reviewer_email].commits_coauthored += 1
                else:
                    stats_dict[reviewer_email].reviews_given += 1


def parse_commit_log(git_output: str, stats_dict: Dict[str, AuthorStats]) -> None:
    """
    Parse git log output with --numstat to extract commit and churn metrics.
    Also detects bug fixes, code review participation, and categorizes files by type.

    Args:
        git_output: Raw output from git log --numstat with full messages
        stats_dict: Dictionary to update with statistics
    """
    current_commit: Optional[Tuple[str, str, str, str]] = None
    current_message: List[str] = []
    in_message = False

    for line in git_output.splitlines():
        # Check for commit message end marker
        if line == "--END-COMMIT--":
            # Process commit message
            if current_commit and current_message:
                full_message = "\n".join(current_message)
                author_email = current_commit[2]

                # Check for bug fix
                if is_bugfix_commit(full_message):
                    stats_dict[author_email].commits_bugfix += 1

                # Extract review credits
                extract_review_credits(full_message, author_email, stats_dict)

            current_message = []
            in_message = False
            continue

        # Parse commit header line (hash, name, email, date)
        if line.count("\t") == 3:
            # Start new commit
            sha, author_name, author_email, commit_date = line.split("\t")
            author_email = normalize_author(author_email)
            current_commit = (sha, author_name, author_email, commit_date)
            in_message = True  # Start collecting message

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
            continue

        # Parse numstat line (additions, deletions, filename)
        if line and current_commit and line.count("\t") == 2 and not in_message:
            additions, deletions, filepath = line.split("\t")
            author_email = current_commit[2]
            stats = stats_dict[author_email]

            # Categorize file
            file_category = categorize_file(filepath)

            # Binary files show as "- -" in numstat
            if additions == "-" and deletions == "-":
                stats.files_binary += 1
            else:
                # Text files: count line changes
                added_count = 0
                deleted_count = 0

                if additions != "-":
                    try:
                        added_count = int(additions)
                        stats.lines_added += added_count
                    except ValueError:
                        pass

                if deletions != "-":
                    try:
                        deleted_count = int(deletions)
                        stats.lines_deleted += deleted_count
                    except ValueError:
                        pass

                # Track by file type
                if file_category == "code":
                    stats.lines_code_added += added_count
                    stats.lines_code_deleted += deleted_count
                elif file_category == "docs":
                    stats.lines_docs_added += added_count
                    stats.lines_docs_deleted += deleted_count
                elif file_category == "config":
                    stats.lines_config_added += added_count
                    stats.lines_config_deleted += deleted_count

            stats.total_files_changed += 1
            continue

        # Collect commit message lines
        if in_message:
            current_message.append(line)


def calculate_file_operations(
    common_args: List[str],
    stats_dict: Dict[str, AuthorStats],
    cwd: Optional[str] = None,
) -> None:
    """
    Calculate file operation types (added/deleted/modified) for each author.
    Also categorizes files by type (code/docs/config).

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
            parts = line.split("\t")
            status = parts[0].strip()
            filepath = parts[1] if len(parts) > 1 else ""
            stats = stats_dict[current_author]

            # Categorize file
            file_category = categorize_file(filepath)

            # A = Added, M = Modified, D = Deleted
            # R = Renamed (count as modified), C = Copied (count as added)
            if status.startswith("A") or status.startswith("C"):
                stats.files_added += 1
                if file_category == "code":
                    stats.files_code_added += 1
                elif file_category == "docs":
                    stats.files_docs_added += 1
                elif file_category == "config":
                    stats.files_config_added += 1
            elif status.startswith("D"):
                stats.files_deleted += 1
                if file_category == "code":
                    stats.files_code_deleted += 1
                elif file_category == "docs":
                    stats.files_docs_deleted += 1
                elif file_category == "config":
                    stats.files_config_deleted += 1
            elif status.startswith("M") or status.startswith("R"):
                stats.files_modified += 1
                if file_category == "code":
                    stats.files_code_modified += 1
                elif file_category == "docs":
                    stats.files_docs_modified += 1
                elif file_category == "config":
                    stats.files_config_modified += 1


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

        print(f"{i:2d}. {dev['author_email']:40s} | Overall: {overall:.3f}")
        print(
            f"    Productivity: {prod:.3f} | Quality: {qual:.3f} | "
            f"Collaboration: {collab:.3f}"
        )
        print()


def analyze_dimension(data: List[Dict], dimension: str) -> None:
    """Analyze a specific dimension across normalization methods."""
    print(f"\n{dimension.upper()} DIMENSION ANALYSIS:")
    print("=" * 80)

    # Map dimension names to abbreviated field prefixes
    dimension_map = {
        "productivity": "prod",
        "quality": "quality",
        "collaboration": "collab",
    }

    prefix = dimension_map.get(dimension, dimension)

    fields = [
        f"{prefix}_rel",
        f"{prefix}_abs",
        f"{prefix}_stat",
        f"{prefix}_score",
    ]

    for field_name in fields:
        values = [float(row[field_name]) for row in data]
        avg = sum(values) / len(values)
        min_val = min(values)
        max_val = max(values)

        # Find top performer
        top = max(data, key=lambda x: float(x[field_name]))

        method = field_name.split("_")[-1].capitalize()
        if method == "Rel":
            method = "Relative"
        elif method == "Abs":
            method = "Absolute"
        elif method == "Stat":
            method = "Statistical"

        norm_method = f"{method:15s}"
        range_str = f"Range=[{min_val:.3f}, {max_val:.3f}]"
        print(f"\n{norm_method}: Avg={avg:.3f}, {range_str}")
        print(f"  Top: {top['author_email']} ({float(top[field_name]):.3f})")


def compare_normalizations(data: List[Dict], author: str) -> None:
    """Compare normalization methods for a specific author."""
    dev = next((d for d in data if d["author_email"] == author), None)
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
        print(f"\n{name:15s}: {top['author_email']:40s} ({score:.3f})")


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
        compare_normalizations(rows, rows[0]["author_email"])

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

    # Step 1: Calculate dynamic thresholds adapted to team context
    dynamic_thresholds = calculate_dynamic_thresholds(stats_dict)

    # Step 2: Calculate raw dimension scores for all authors
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

    # Step 3: Prepare lists for normalization
    productivity_values = list(productivity_raw.values())
    quality_values = list(quality_raw.values())
    collaboration_values = list(collaboration_raw.values())

    # Step 4: Calculate normalized scores for each author
    for author_email, stats in stats_dict.items():
        # Get raw scores
        prod_raw = productivity_raw[author_email]
        qual_raw = quality_raw[author_email]
        collab_raw = collaboration_raw[author_email]

        # --- PRODUCTIVITY INDICATORS ---
        # Relative (min-max within team)
        productivity_relative = normalize_relative(prod_raw, productivity_values)

        # Absolute (dynamic thresholds adapted to team)
        # Uses percentile-based thresholds instead of fixed values
        prod_absolute = normalize_absolute(
            stats.commits_non_merge,
            dynamic_thresholds["commits_excellent"],
            dynamic_thresholds["commits_poor"],
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
