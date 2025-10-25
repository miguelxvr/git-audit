# git-audit

Extract per-developer metrics from Git repositories with comprehensive evaluation indicators. Zero dependencies, outputs CSV.

## Quick Start

```bash
# Generate indicators for current repository
python3 git-audit.py > output.csv

# Generate indicators with analysis report
python3 git-audit.py --print

# Analyze remote repository
python3 git-audit.py --repo https://github.com/user/repo.git --print
```

## Output

Generates **37 metrics** per developer in CSV format:

- Base metrics (commits, lines, files operations)
- Calculated indicators (frequency, ratios, averages)
- Team-relative percentages
- **Evaluation scores** (0.0-1.0): productivity, quality, collaboration, overall

📊 **See [METRICS.md](METRICS.md) for complete documentation**

## Usage

```bash
# Local repository
python3 git-audit.py > report.csv
python3 git-audit.py --print

# Remote repository
python3 git-audit.py --repo https://github.com/user/repo.git --print

# Custom output file
python3 git-audit.py --print --output team_analysis.csv
```

**The script automatically:**
- Analyzes all branches
- Includes merge and non-merge commits
- Collects complete data for accurate indicators
- Generates analysis reports with `--print`

## Options

```
--repo <url>         Clone and analyze remote repository
--print              Save CSV + generate analysis report
--output <file>      Custom output filename (default: output.csv)
```

## Files

- **git-audit.py** - Main script (~1300 lines)
- **METRICS.md** - Complete metrics documentation
- **README.md** - This file

## License

MIT

---

**For detailed metrics documentation**, see [METRICS.md](METRICS.md)
