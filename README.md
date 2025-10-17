# git-audit

A fast, dependency-free extractor of per-developer indicators from a Git repository.

## Features

- **Zero dependencies**: Uses only Python 3 standard library
- **Fast**: Efficient git command execution
- **Comprehensive metrics**: Commits, lines changed, files touched, activity patterns, and more
- **Flexible filtering**: By branch, date range, and path exclusions
- **CSV output**: Easy to analyze in spreadsheets or data tools

## Metrics Collected

Per author/email:
- `commits_non_merge`: Number of non-merge commits
- `merge_commits`: Number of merge commits
- `lines_added`: Total lines added
- `lines_deleted`: Total lines deleted
- `net_lines`: Net lines (added - deleted)
- `files_changed`: Total file changes count
- `unique_files_touched`: Number of unique files modified
- `avg_commit_size_lines`: Average lines changed per commit
- `active_days`: Number of unique days with commits
- `weekend_commit_pct`: Percentage of commits made on weekends
- `first_commit_date`: Date of first commit
- `last_commit_date`: Date of last commit

## Quick Start

### Run directly from GitHub (single line)

```bash
# From current directory (analyzes current git repo)
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/git-audit/main/git-audit.py | python3

# With arguments
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/git-audit/main/git-audit.py | python3 - --all --no-merges --since 2024-01-01

# Save to file
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/git-audit/main/git-audit.py | python3 - --branch main > report.csv
```

### Run locally

```bash
# Download once
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/git-audit/main/git-audit.py -o git-audit.py
chmod +x git-audit.py

# Run it
./git-audit.py --all --no-merges > report.csv
```

Or clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/git-audit.git
cd git-audit
python3 git-audit.py --help
```

## Usage Examples

```bash
# Analyze all branches, exclude merges, from start of 2024
python3 git-audit.py --all --no-merges --since 2024-01-01 > indicators.csv

# Analyze main branch only
python3 git-audit.py --branch main > main-branch-stats.csv

# Exclude vendor and dist directories
python3 git-audit.py --all --exclude 'vendor/' --exclude 'dist/' > clean-stats.csv

# Date range analysis
python3 git-audit.py --since 2024-01-01 --until 2024-12-31 > year-2024.csv

# Analyze current branch (HEAD)
python3 git-audit.py > current-branch.csv
```

## Options

```
--all                    Use all refs (branches, tags)
--branch <name>          Only analyze this branch/ref (e.g., main)
--no-merges              Ignore merge commits for most metrics
--since YYYY-MM-DD       Start date (inclusive)
--until YYYY-MM-DD       End date (inclusive)
--exclude <pathspec>     Exclude paths (repeatable)
```

## Requirements

- Python 3.6+
- Git (must be in a git repository)

## How It Works

The tool executes several optimized git commands to gather statistics:
1. `git log --numstat` for commit and churn metrics
2. `git log --format` for weekend commit detection
3. `git log --merges` for merge commit counts
4. `git log --name-only` for unique file tracking

All data is processed in-memory and output as CSV to stdout.

## License

MIT
