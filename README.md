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

Generates **68 metrics** per developer in CSV format:

- Base metrics (commits, lines by type, file operations by type, collaboration)
- Calculated indicators (frequency, ratios, averages, bug fix ratio)
- Team-relative percentages
- **Evaluation scores** (0.0-1.0): productivity, quality, collaboration, overall

📊 **See [METRICS.md](METRICS.md) for complete metrics reference**
📚 **See [METHODOLOGY.md](METHODOLOGY.md) for implementation methodology**
🎓 **See [ACADEMIC_RESEARCH.md](ACADEMIC_RESEARCH.md) for academic foundations and framework comparisons**

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

- **git-audit.py** - Main script (enhanced with file categorization, bug fix detection, code review tracking, dynamic thresholds)
- **METRICS.md** - Complete metrics reference (68 metrics)
- **METHODOLOGY.md** - Implementation methodology and design decisions
- **METHODOLOGY_AGES.md** - Specialized methodology for AGES educational teams
- **ACADEMIC_RESEARCH.md** - Academic foundations, framework comparisons, and bibliography (50+ citations)
- **TEAM_FORMATION.md** - AGES team structure and progression model
- **README.md** - This file

## Key Features

✅ **File Type Categorization** - Distinguishes code, documentation, and configuration contributions
✅ **Bug Fix Detection** - Identifies maintenance vs. feature work from commit messages
✅ **Code Review Tracking** - Credits reviewers via commit trailers (`Reviewed-by`, `Co-authored-by`)
✅ **Dynamic Thresholds** - Context-aware evaluation adapted to team size and norms
✅ **Multi-Dimensional Assessment** - Productivity, Quality, Collaboration (backed by academic research)

## Documentation

📊 **[METRICS.md](METRICS.md)** - Detailed reference for all 68 metrics
📚 **[METHODOLOGY.md](METHODOLOGY.md)** - Implementation details and design decisions
🎓 **[ACADEMIC_RESEARCH.md](ACADEMIC_RESEARCH.md)** - Academic frameworks (DORA, SPACE, MSR) and 50+ research citations
🎯 **[METHODOLOGY_AGES.md](METHODOLOGY_AGES.md)** - Specialized methodology for educational teams (AGES)
👥 **[TEAM_FORMATION.md](TEAM_FORMATION.md)** - AGES team structure and progression model

## License

MIT
