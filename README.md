# git-audit

Developer evaluation tool using SPACE framework + Git metrics. Zero dependencies, outputs CSV.

## Quick Start

```bash
# Analyze current repository
python3 git-audit.py --print

# Analyze remote repository
python3 git-audit.py --repo https://github.com/user/repo.git --print

# For educational teams (aggregate multiple GitHub accounts per student)
python3 git-audit.py --repo <URL> --roster students.csv --mapping github_mapping.csv --print
```

## Output

Generates **86 metrics** per developer/student in CSV format:

- **79 Git metrics**: Commits, lines, files (by 7 types: code/docs/config/database/architecture/management/test)
- **6 SPACE scores** (0.0-1.0): Satisfaction, Performance, Activity, Communication, Efficiency, Overall
- **1 AGES level**: Student level (I/II/III/IV) for educational contexts

## Parameters

### Basic Usage

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--print` | Save CSV to file and generate analysis report | `--print` |
| `--output` | Output filename (default: `output.csv`) | `--output team.csv` |
| `--repo` | Clone and analyze remote repository | `--repo https://github.com/user/repo.git` |

### Educational Teams (AGES)

| Parameter | Description | Format |
|-----------|-------------|--------|
| `--roster` | Student roster with AGES levels | CSV: `student_name,ages_level` (I/II/III/IV) |
| `--mapping` | Map GitHub emails to students | CSV: `student_name,author_email` |
| `--survey` | Satisfaction survey responses | CSV: `author_email,q1,q2,...,q14` (1-5 Likert scale) |

**Educational team workflow:**
1. Create `students.csv` with student names and AGES levels (I/II/III/IV)
2. Create `github_mapping.csv` mapping each GitHub email to student name
3. Run: `python3 git-audit.py --repo <URL> --roster students.csv --mapping github_mapping.csv --print`
4. Metrics from multiple GitHub accounts are automatically aggregated per student

### Examples

```bash
# Basic analysis (local repo)
python3 git-audit.py --print

# Remote repository
python3 git-audit.py --repo https://github.com/ConexaoTreinamento/conexao-treinamento.git --print

# Educational team with student aggregation
python3 git-audit.py --repo <URL> --roster students.csv --mapping github_mapping.csv --output team.csv --print

# With satisfaction survey
python3 git-audit.py --repo <URL> --roster students.csv --mapping github_mapping.csv --survey satisfaction.csv --print
```

## Documentation

- 📊 **[METRICS.md](docs/METRICS.md)** - All 86 metrics explained (79 Git + 6 SPACE + 1 AGES level)
- 📚 **[METHODOLOGY.md](docs/METHODOLOGY.md)** - SPACE framework implementation + AGES adaptations
- 🎓 **[ACADEMIC_RESEARCH.md](docs/ACADEMIC_RESEARCH.md)** - Research foundations (DORA, SPACE, MSR)
- 🏫 **[AGES.md](docs/AGES.md)** - AGES educational context (PUCRS)

## Key Features

- ✅ **SPACE Framework** - 5-dimension developer evaluation (Forsgren et al., 2021)
- ✅ **Student Aggregation** - Merge multiple GitHub accounts into single student records
- ✅ **File Type Weights** - 7 categories with domain-specific importance (code: 1.0, docs: 0.5, config: 0.3, etc.)
- ✅ **Bug Fix Detection** - Automatic classification from commit messages
- ✅ **Code Review Tracking** - Credits via commit trailers (`Reviewed-by`, `Co-authored-by`)
- ✅ **Satisfaction Surveys** - External survey integration for SPACE Satisfaction dimension

## License

MIT
