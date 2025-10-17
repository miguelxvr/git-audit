# git-audit

Extract per-developer metrics from Git repositories. Zero dependencies, outputs CSV.

## Installation

```bash
# Run directly from GitHub
curl -sSL https://raw.githubusercontent.com/miguelxvr/git-audit/main/git-audit.py | python3

# Or download locally
curl -sSL https://raw.githubusercontent.com/miguelxvr/git-audit/main/git-audit.py -o git-audit.py
chmod +x git-audit.py
```

## Usage

```bash
# Local repository (analyzes all branches by default)
python3 git-audit.py --no-merges > report.csv

# Analyze remote GitHub/GitLab repository
python3 git-audit.py --repo https://github.com/user/repo.git > report.csv

# With date range
python3 git-audit.py --since 2024-01-01 --until 2024-12-31 > report.csv

# Specific branch only
python3 git-audit.py --branch main > report.csv

# Exclude paths
python3 git-audit.py --exclude 'vendor/' --exclude 'dist/' > report.csv
```

## Metrics

Per author/email:

**Base Metrics:**
- `commits_non_merge`, `merge_commits`, `total_commits`
- `lines_added`, `lines_deleted`, `total_lines_changed`
- `files_changed`, `unique_files_touched`

**Calculated Indicators (great for plotting!):**
- `avg_commit_size_lines` - Average lines per commit
- `commit_frequency` - Commits per active day
- `churn_ratio` - Deletions/additions ratio (refactoring indicator)
- `files_per_commit` - Average files changed per commit
- `active_span_days` - Days between first and last commit
- `active_days` - Number of unique days with commits

**Relative Metrics (team comparison):**
- `commit_pct` - Percentage of total commits
- `lines_changed_pct` - Percentage of total lines changed
- `files_touched_pct` - Percentage of codebase touched

**Timeline:**
- `first_commit_date`, `last_commit_date`

## Options

```
--repo <url>         GitHub/GitLab repository URL (clones temporarily)
--branch <name>      Analyze specific branch (default: all refs)
--no-merges          Exclude merge commits
--since YYYY-MM-DD   Start date
--until YYYY-MM-DD   End date
--exclude <path>     Exclude paths (repeatable)
```

## Visualization Ideas

The CSV output is designed for easy plotting. Here are some chart ideas:

**Team Comparison:**
- Bar chart: `commit_pct` by author
- Pie chart: `lines_changed_pct` by author
- Horizontal bar: `files_touched_pct` by author

**Activity Patterns:**
- Scatter: `active_days` vs `total_commits`
- Line chart: `commit_frequency` over authors
- Timeline: `first_commit_date` to `last_commit_date` by author

**Code Quality Indicators:**
- Bar chart: `churn_ratio` by author (low = new features, high = refactoring)
- Scatter: `avg_commit_size_lines` vs `files_per_commit`
- Heatmap: Multiple metrics normalized by author

**Contribution Distribution:**
- Stacked bar: `lines_added` vs `lines_deleted` by author
- Bubble chart: `total_commits` (x) vs `unique_files_touched` (y), sized by `total_lines_changed`

Use tools like Excel, Google Sheets, Python (matplotlib/seaborn), or R (ggplot2) to visualize!

## Requirements

- Python 3.6+
- Git repository

## License

MIT
