# Git-audit Methodology

## 1. Introduction

Git-audit is a developer evaluation tool based on Git repository mining that employs a multi-dimensional assessment framework. Unlike simplistic metrics (e.g., lines of code), git-audit evaluates developers across three complementary dimensions—**Productivity**, **Quality**, and **Collaboration**—using multiple normalization methods to reduce bias and provide context-aware insights.

### Core Philosophy

1. **Multi-dimensional assessment**: No single metric captures developer contribution
2. **Context-aware evaluation**: Metrics interpreted relative to team and project norms
3. **Bias reduction**: Multiple normalization methods averaged to minimize individual biases
4. **Actionable insights**: Metrics designed to identify strengths and improvement areas

## 2. Three-Dimension Model

Git-audit evaluates developers across three core dimensions, each backed by extensive academic research (see ACADEMIC_RESEARCH.md for detailed citations).

### 2.1 Productivity Dimension (40% of Overall Score)

**Purpose**: Measures contribution volume and consistency

**Components**:
- Commits: 40% weight
- Lines changed: 30% weight (weighted by file type)
- Files touched: 20% weight (weighted by file type)
- Active days: 10% weight

**File Type Weighting**:
- Code: 100% (full value)
- Documentation: 50% (valuable but less technical)
- Configuration: 30% (necessary but often mechanical)

**Rationale**: Volume alone is insufficient. We balance quantity (commits, lines, files) with consistency (active days) and weight contributions by technical complexity.

### 2.2 Quality Dimension (30% of Overall Score)

**Purpose**: Assesses code practices and maintainability

**Components**:
- Code churn ratio: 30% weight (lower is better)
- Commit size: 20% weight (50-500 lines optimal)
- Files per commit: 20% weight (1-3 files optimal)
- Merge commit ratio: 15% weight (lower is better)
- Bug fix ratio: 15% weight (15-35% optimal)

**Rationale**: Quality encompasses multiple practices. Low churn indicates new development over rework. Appropriately-sized commits are easier to review. Balanced bug fix ratio shows responsiveness without being entirely reactive.

### 2.3 Collaboration Dimension (30% of Overall Score)

**Purpose**: Evaluates team integration and knowledge sharing

**Components**:
- Merge activity: 30% weight
- Shared file ownership: 30% weight
- Code review participation: 20% weight
- Activity span: 20% weight

**Rationale**: Modern development is team-based. Shared ownership reduces bottlenecks. Code review participation recognizes quality contributions beyond authorship. Sustained engagement indicates commitment.

## 3. Implementation Details

### 3.1 File Type Categorization

**Motivation**: Not all changed lines have equal value. Documentation updates, configuration changes, and source code modifications represent different contribution types.

**Categories**:

**Code Files** (100% weight):
- Extensions: `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.java`, `.c`, `.cpp`, `.cs`, `.go`, `.rs`, `.rb`, `.php`, `.swift`, `.kt`, `.scala`, `.sh`, `.sql`, `.html`, `.css`, `.vue`, and 40+ more
- Full technical weight in productivity calculation

**Documentation Files** (50% weight):
- Extensions: `.md`, `.txt`, `.rst`, `.adoc`, `.tex`
- Special files: `README`, `LICENSE`, `CONTRIBUTING`, `CHANGELOG`
- Half weight recognizes value while preventing inflation

**Configuration Files** (30% weight):
- Extensions: `.json`, `.yaml`, `.xml`, `.toml`, `.ini`, `.env`
- Special files: `Makefile`, `Dockerfile`, `package.json`, `pom.xml`
- Lower weight reflects mechanical nature

**Implementation**: During parsing, each file is categorized and line/file counts are tracked separately by type. Productivity calculation applies weights to prevent documentation contributors from appearing disproportionately productive.

### 3.2 Work Type Detection (Bug Fix vs. Feature)

**Motivation**: Bug fixes indicate maintenance/quality work; features indicate development velocity. Both are valuable but represent different skills.

**Detection Method**: Parse commit messages for patterns

**Bug Fix Patterns**:
- Keywords: `fix`, `bug`, `hotfix`, `patch`, `repair`, `correct`, `defect`
- Issue references: `issue #`, `closes #`, `fixes #`, `resolves #`

**Metrics Generated**:
- `commits_bugfix`: Count of bug fix commits
- `commits_feature`: Non-merge, non-bugfix commits
- `commits_bugfix_ratio`: Percentage maintenance work

**Quality Integration**: Bugfix ratio contributes 15% to quality score. Optimal range is 15-35%, indicating:
- Too low (<15%): May not be addressing technical debt
- Optimal (15-35%): Balanced maintenance and development
- Too high (>35%): Primarily reactive work

**Implementation**: Each commit message is analyzed during parsing. A commit is flagged as bugfix if any pattern matches (case-insensitive).

### 3.3 Code Review Participation

**Motivation**: Modern development relies on code review. Reviewers contribute to quality without authoring commits.

**Detection Method**: Parse commit message trailers

**Recognized Trailers**:
- `Reviewed-by: Name <email>`: Explicit review credit
- `Co-authored-by: Name <email>`: Pair programming or joint work
- `Acked-by: Name <email>`: Acknowledgment of review

**Metrics Generated**:
- `reviews_given`: Times author reviewed others' code
- `commits_coauthored`: Pair programming contributions

**Collaboration Integration**: Review participation contributes 20% to collaboration score, recognizing that reviewers improve code quality even without commit authorship.

**Implementation**: Commit message trailers are parsed with regex patterns. Credits are attributed to the reviewer's email address extracted from the trailer.

### 3.4 Dynamic Threshold Calibration

**Motivation**: Fixed thresholds (e.g., "50 commits = excellent") are context-blind. A startup team of 3 has different norms than a 100-person enterprise team.

**Method**: Calculate team distribution percentiles instead of using fixed values

**Threshold Calculation**:
- **Excellent**: 90th percentile of team (minimum 10)
- **Poor**: 25th percentile of team (minimum 1)

**Example**:
- Small team (3 devs, 10-30 commits each):
  - 90th percentile = 27 commits → "excellent" threshold = 27
  - 25th percentile = 12 commits → "poor" threshold = 12

- Large team (50 devs, 50-300 commits each):
  - 90th percentile = 260 commits → "excellent" threshold = 260
  - 25th percentile = 80 commits → "poor" threshold = 80

**Applied To**: Absolute normalization method for productivity and collaboration dimensions

**Implementation**: Before calculating evaluation indicators, team statistics are analyzed to derive dynamic thresholds. These replace the previously fixed values.

## 4. Normalization Methods

Git-audit uses three complementary normalization methods, averaging them to reduce individual method biases.

### 4.1 Relative Normalization (Min-Max)

**Method**: Compares developer to team best/worst

**Formula**: `(value - min) / (max - min)`

**Advantages**:
- Fair within-team comparison
- Intuitive interpretation (0 = worst, 1 = best)
- No external benchmarks needed

**Disadvantages**:
- Sensitive to outliers
- Small teams have compressed ranges
- Doesn't indicate absolute performance level

### 4.2 Absolute Normalization (Dynamic Thresholds)

**Method**: Compares to team-adapted percentile thresholds

**Formula**: `clamp((value - poor) / (excellent - poor), 0, 1)`

**Advantages**:
- Interpretable reference points
- Adapts to team context
- Provides actionable targets

**Disadvantages**:
- Requires careful threshold selection
- May not fit all contexts perfectly
- Can plateau at extremes

### 4.3 Statistical Normalization (Percentile Rank)

**Method**: Ranks developer within team distribution

**Formula**: `percentile_rank(value) / 100`

**Advantages**:
- Robust to outliers
- Captures relative standing
- Works well with skewed distributions

**Disadvantages**:
- Non-linear scale
- Less intuitive interpretation
- Requires sufficient sample size

### 4.4 Why Average All Three?

Each normalization method has inherent biases:
- **Relative** is outlier-sensitive
- **Absolute** depends on threshold selection
- **Statistical** is non-linear

By averaging all three methods, we:
1. Reduce individual method biases
2. Provide more stable, fair evaluation
3. Capture multiple perspectives on performance
4. Align with multi-criteria decision analysis best practices

## 5. Known Limitations and Biases

### 5.1 What Git-audit Cannot Measure

- ❌ **Code correctness**: Actual functionality, performance, security
- ❌ **Non-code contributions**: Design, mentoring, project management, meetings
- ❌ **Developer satisfaction**: Morale, burnout, job satisfaction
- ❌ **Business value**: Impact on users, revenue, strategic importance
- ❌ **Role context**: Junior vs. senior expectations

### 5.2 Data Availability Constraints

- Requires Git repository access (doesn't work with SVN, proprietary VCS)
- No deployment/incident data (unlike DORA metrics)
- Limited to committed work (misses work-in-progress, abandoned branches)
- Requires commit message discipline for bug fix/review detection

### 5.3 Potential Biases and Mitigations

**Commit Granularity Bias**:
- **Issue**: Frequent small commits vs. batched large commits
- **Mitigation**: Commit size metrics detect extremes; quality rewards appropriate sizing

**Role Bias**:
- **Issue**: Juniors write more new code; seniors refactor and review
- **Mitigation**: Quality rewards refactoring (lower churn); collaboration rewards reviews

**Repository Age Bias**:
- **Issue**: Early contributors accumulate more metrics
- **Mitigation**: Frequency/span metrics focus on consistency; dynamic thresholds adapt to current team

**Language/Domain Bias**:
- **Issue**: Some languages are more verbose (Java vs. Python)
- **Mitigation**: Within-team comparison (relative normalization) controls for project factors

**Documentation Contributor Bias**:
- **Previous Issue**: Documentation writers appeared highly productive via LOC
- **Mitigation**: File type categorization weights documentation at 50% of code

## 6. Ethical Considerations

### 6.1 Intended Use

**✅ Appropriate Applications**:
- Team retrospectives and improvement planning
- Identifying mentoring opportunities
- Recognizing diverse contributions (code, review, collaboration)
- Spotting process issues (e.g., siloed knowledge)
- Celebrating balanced team members

**❌ Inappropriate Applications**:
- Performance reviews as sole evaluation factor
- Compensation decisions based purely on metrics
- Hiring/firing decisions without human judgment
- Comparing developers across different teams/projects
- Automated judgments without context

### 6.2 Gaming and Goodhart's Law

> "When a measure becomes a target, it ceases to be a good measure." — Goodhart (1975)

**Potential Gaming**:
- Artificially splitting commits to inflate count
- Adding unnecessary lines/files
- Excessive refactoring to manipulate churn ratio
- Spamming review credits in commit messages

**Recommendations**:
1. Use metrics as conversation starters, not automated judgments
2. Combine with qualitative assessment and peer feedback
3. Rotate metrics periodically to prevent optimization
4. Make gaming behaviors visible to team (transparency)
5. Focus on team improvement, not individual competition

### 6.3 Transparency and Team Ownership

**Principles**:
- All metrics and formulas are open-source and documented
- Developers should understand how they're evaluated
- Team should collectively decide metric weights and thresholds
- Regular review and adjustment of evaluation criteria
- Open discussion of limitations and biases

## 7. Validation and Accuracy

### 7.1 What Git-audit Gets Right

✅ **Multi-dimensional assessment**: No single metric dominates
✅ **Context-aware**: Dynamic thresholds adapt to team size and norms
✅ **Bias reduction**: Multiple normalization methods reduce individual biases
✅ **Modern practices**: Recognizes code review and pair programming
✅ **Fair weighting**: File type categorization prevents documentation inflation
✅ **Research-backed**: Built on highly-cited academic findings

### 7.2 Areas for Continued Research

⚠️ **Optimal weights**: Current weights (40/30/20/10) are heuristic; team-specific tuning may improve accuracy
⚠️ **Temporal dynamics**: Activity trends and velocity changes not yet captured
⚠️ **Role differentiation**: Explicit architect/reviewer/implementer roles not distinguished
⚠️ **Cross-project contributions**: Developers working on multiple repositories not fully captured
⚠️ **Context detection**: Cannot automatically detect project phase (e.g., initial development vs. maintenance)

---

**For academic foundations, framework comparisons, and complete bibliography, see [ACADEMIC_RESEARCH.md](ACADEMIC_RESEARCH.md)**

**For detailed metric documentation, see [METRICS.md](METRICS.md)**

**Last Updated**: October 2025
**Git-audit Version**: Enhanced with file categorization, bug fix detection, code review tracking, and dynamic thresholds
