# Git-audit Methodology

## 1. Introduction

Git-audit is a developer evaluation tool based on Git repository mining that employs the **SPACE Framework** (Forsgren et al., 2021) for multi-dimensional assessment. Unlike simplistic metrics (e.g., lines of code), git-audit evaluates developers across five complementary dimensions using normalized scores and context-aware insights.

### Core Philosophy

1. **Multi-dimensional assessment**: The SPACE framework captures diverse aspects of developer productivity
2. **Context-aware evaluation**: Metrics interpreted relative to team and project norms
3. **Bias reduction**: Tri-method normalization (relative, absolute, statistical) averaged to minimize biases
4. **Actionable insights**: Metrics designed to identify strengths and improvement areas
5. **Research-backed**: Built on the SPACE framework (Forsgren et al., 2021), a well-validated productivity measurement system

## 2. SPACE Framework Implementation

Git-audit implements the **SPACE Framework** (Satisfaction, Performance, Activity, Communication, Efficiency), a comprehensive productivity measurement system developed by GitHub, Microsoft, and University of Victoria researchers.

### 2.1 Satisfaction Dimension (15% of Overall Score)

**Purpose**: Measures developer well-being and fulfillment

**Source**: External quarterly survey (14 questions, 1-5 Likert scale)

**Components**:
- Job Satisfaction (questions 1-3): 30% weight
- Wellbeing (questions 4-7): 25% weight (questions 4-5 reverse-scored)
- Growth Opportunities (questions 8-11): 25% weight
- Team Culture (questions 12-14): 20% weight

**Rationale**: Developer satisfaction correlates with retention, quality, and sustained productivity. However, it cannot be inferred from Git data and requires external survey collection.

**Implementation**: If survey data is provided via `--survey` option, satisfaction scores are calculated. Otherwise, defaults to 0.0 (not measured).

### 2.2 Performance Dimension (20% of Overall Score)

**Purpose**: Assesses code quality and workflow effectiveness from Git data

**Components**:
- **Code churn quality (30%)**: Lower churn ratio indicates new development over rework
  - Score 1.0 if churn < 0.3 (mostly new code)
  - Degrades linearly for higher churn
- **Commit size quality (20%)**: 50-200 lines per commit optimal for reviewability
  - Score 1.0 for 50-200 lines
  - Lower score for too small (<50) or too large (>200)
- **Commit focus (20%)**: 1-3 files per commit optimal
  - Score 1.0 for ≤3 files
  - Degrades for unfocused commits
- **Bugfix balance (15%)**: 15-35% bugfix ratio optimal
  - Shows responsiveness without being purely reactive
- **Merge quality (15%)**: 5-15% merge ratio optimal
  - Indicates integration work without excessive branching

**Rationale**: Performance captures code quality outcomes observable in Git. Unlike subjective code reviews, these metrics are automatically measurable and correlate with code maintainability.

### 2.3 Activity Dimension (25% of Overall Score)

**Purpose**: Measures contribution volume and consistency

**Components**:
- **Commits (40%)**: Primary activity indicator, tri-method normalized
- **Lines changed (30%)**: Weighted by file type, tri-method normalized
- **Files changed (20%)**: Weighted by file type, tri-method normalized
- **Temporal consistency (10%)**: Active days/span + commit frequency

**File Type Weighting**:
- Code: 100% (full value)
- Test: 70% (important but derivative)
- Database: 80% (schema work)
- Architecture: 90% (high-level design)
- Management: 60% (project artifacts)
- Documentation: 50% (valuable but less technical)
- Configuration: 30% (necessary but often mechanical)

**Rationale**: Activity captures contribution volume while accounting for technical complexity. File type weighting prevents documentation-heavy contributors from appearing disproportionately productive.

### 2.4 Communication Dimension (25% of Overall Score)

**Purpose**: Evaluates collaboration and knowledge sharing

**Components**:
- **Code review participation (30%)**: Reviews given + co-authorship
  - Reviews score: min(reviews_given / 10.0, 1.0) weighted 70%
  - Co-authorship score: min(coauthored / 5.0, 1.0) weighted 30%
- **Shared ownership (30%)**: 30-70% file overlap with team optimal
  - Score 1.0 if 30-70% of files also touched by others
  - Prevents silos (too low) and lack of focus (too high)
- **Integration activity (25%)**: Merge commits, tri-method normalized
  - Indicates active participation in code integration
- **Sustained engagement (15%)**: Developer's span / project duration
  - Shows long-term commitment to the project

**Rationale**: Modern development is collaborative. Communication metrics recognize contributions beyond individual coding (reviews, pair programming, shared ownership).

### 2.5 Efficiency Dimension (15% of Overall Score)

**Purpose**: Measures workflow effectiveness and minimal waste

**Components**:
- **Workflow smoothness (35%)**: Consistent commit sizing
  - Uses same scoring as Performance commit size
- **Focused work (30%)**: 1-3 files per commit
  - Uses same scoring as Performance commit focus
- **Response time proxy (20%)**: Commit frequency 1-2 per active day optimal
  - Lower suggests slow feedback cycles
  - Higher suggests reactive/interrupt-driven work
- **Rework minimization (15%)**: Inverse of churn ratio
  - Score = max(0.2, 1.0 - churn) if churn ≤ 1.0

**Rationale**: Efficiency is the weakest SPACE dimension for Git-only measurement (cycle time and workflow delays require external data). We approximate with commit patterns and code churn.

**Note**: True efficiency measurement requires CI/CD metrics, issue tracker integration, and developer surveys. Git-only measurement provides rough proxies.

### 2.6 Overall SPACE Score

**Formula**:
```
overall = 0.15×Satisfaction + 0.20×Performance + 0.25×Activity +
          0.25×Communication + 0.15×Efficiency
```

**Weights Rationale**:
- Activity and Communication receive highest weights (25% each) as they're best measured from Git
- Performance receives 20% as a critical quality indicator
- Satisfaction and Efficiency receive 15% each due to measurement limitations (external survey / Git proxy data)

**Interpretation**:
- 0.7-1.0: Excellent across all dimensions
- 0.5-0.7: Solid contributor with balanced performance
- 0.3-0.5: Developing contributor or specialized role
- 0.0-0.3: May need support or role adjustment

## 3. Enhanced File Categorization

Git-audit uses 7 file categories tailored for AGES educational environment and modern software projects.

### 3.1 Standard Categories (3)

**Code Files** (100% weight):
- Extensions: `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.java`, `.c`, `.cpp`, `.h`, `.hpp`, `.cs`, `.go`, `.rs`, `.rb`, `.php`, `.swift`, `.kt`, `.scala`, `.m`, `.dart`, `.lua`, `.sh`, `.bash`, `.html`, `.css`, `.scss`, `.vue`
- Full technical weight in activity calculation

**Documentation Files** (50% weight):
- Extensions: `.md`, `.txt`, `.rst`, `.adoc`, `.tex`, `.pdf`, `.doc`, `.docx`
- Special files: `readme`, `license`, `contributing`, `changelog`, `authors`
- Half weight recognizes value while preventing inflation

**Configuration Files** (30% weight):
- Extensions: `.json`, `.yaml`, `.yml`, `.xml`, `.toml`, `.ini`, `.cfg`, `.conf`, `.env`, `.gitignore`, `.dockerignore`
- Special files: `makefile`, `dockerfile`, `package.json`, `cargo.toml`
- Lower weight reflects mechanical nature

### 3.2 AGES-Specific Categories (4)

Git-audit includes four additional categories for educational team projects:

**Test Files** (70% weight):
- Extensions: `.test.js`, `.test.ts`, `.spec.js`, `.spec.py`, etc.
- Patterns: `test-plan`, `test-report`, `test-cases`, `test-strategy`
- Weighted at 70% as tests are derivative but important for quality

**Database Files** (80% weight):
- Extensions: `.sql`, `.mwb`, `.erd`, `.dbml`, `.ddl`, `.dml`
- Patterns: `schema`, `migrations`, `db-diagram`, `database`, `entities`
- Weighted at 80% as database design is technical but often template-driven

**Architecture Files** (90% weight):
- Extensions: `.puml`, `.drawio`, `.archimate`, `.uml`, `.dia`
- Patterns: `architecture`, `component-diagram`, `deployment-diagram`, `class-diagram`
- Weighted at 90% as architecture artifacts represent high-level design work

**Management Files** (60% weight):
- Patterns: `backlog`, `wbs`, `release-plan`, `sprint-plan`, `communication-plan`, `risk-plan`, `product-backlog`, `user-stories`, `use-cases`
- Weighted at 60% as project management artifacts are valuable but less technical

**Rationale**: AGES (Agência Experimental de Engenharia de Software) teams produce diverse artifacts beyond code. Explicit categorization allows fair comparison between roles (e.g., architects vs. developers vs. project managers).

## 4. Implementation Details

### 4.1 Work Type Detection (Bug Fix vs. Feature)

**Motivation**: Bug fixes indicate maintenance/quality work; features indicate development velocity.

**Detection Method**: Parse commit messages for patterns

**Bug Fix Patterns**:
- Keywords: `fix`, `bug`, `hotfix`, `patch`, `repair`, `correct`, `defect`
- Issue references: `issue #`, `closes #`, `fixes #`, `resolves #`

**Metrics Generated**:
- `commits_bugfix`: Count of bug fix commits
- `commits_feature`: Non-merge, non-bugfix commits
- `commits_bugfix_ratio`: Percentage maintenance work

**Performance Integration**: Bugfix ratio contributes 15% to Performance score. Optimal range is 15-35%.

### 4.2 Code Review Participation

**Motivation**: Reviewers contribute to quality without authoring commits.

**Detection Method**: Parse commit message trailers

**Recognized Trailers**:
- `Reviewed-by: Name <email>`: Explicit review credit
- `Co-authored-by: Name <email>`: Pair programming or joint work
- `Acked-by: Name <email>`: Acknowledgment of review

**Metrics Generated**:
- `reviews_given`: Times author reviewed others' code
- `commits_coauthored`: Pair programming contributions

**Communication Integration**: Review participation contributes 30% to Communication score.

### 4.3 Tri-Method Normalization

Git-audit uses three complementary normalization methods, averaging them to reduce bias.

#### Method 1: Relative Normalization (Min-Max)

**Formula**: `(value - min) / (max - min)`

**Advantages**: Fair within-team comparison, intuitive interpretation

**Disadvantages**: Sensitive to outliers, compressed ranges for small teams

#### Method 2: Absolute Normalization (Dynamic Thresholds)

**Formula**: `max(0, min(1, (value - poor) / (excellent - poor)))`

**Thresholds**:
- Poor = 25th percentile of team (minimum 1)
- Excellent = 90th percentile of team (minimum 10)

**Advantages**: Interpretable reference points, adapts to team context

**Disadvantages**: Can plateau at extremes

#### Method 3: Statistical Normalization (Percentile Rank)

**Formula**: `(count_below + 0.5 × count_equal) / team_size`

**Advantages**: Robust to outliers, captures relative standing

**Disadvantages**: Non-linear scale, less intuitive

#### Why Average All Three?

Each method has biases. Averaging:
1. Reduces individual method biases
2. Provides more stable evaluation
3. Captures multiple perspectives
4. Aligns with multi-criteria decision analysis best practices

**Implementation**: All Activity and Communication volume metrics use tri-method normalization before dimension calculation.

## 5. AGES-Specific Features

### 5.1 Student Roster Integration

**Purpose**: Map AGES level (I, II, III, IV) to students for cohort analysis

**Usage**: `--roster students.csv`

**Format**: `student_name,ages_level`

**Output**: `ages_level` column in CSV output

### 5.2 GitHub Account Aggregation

**Purpose**: Combine multiple GitHub accounts into single student record

**Usage**: `--mapping github_mapping.csv`

**Format**: `student_name,author_email`

**Behavior**: All commits from mapped emails are aggregated under student name

**Rationale**: Students often use multiple emails (personal, university). Aggregation ensures fair comparison.

### 5.3 Satisfaction Survey Integration

**Purpose**: Add Satisfaction dimension to SPACE framework

**Usage**: `--survey satisfaction.csv`

**Format**: `author_email,q1,q2,...,q14` (1-5 Likert scale)

**Scoring**:
- Questions 4 and 5 are reverse-scored (burnout items)
- Weighted average: 30% job satisfaction + 25% wellbeing + 25% growth + 20% team culture

**Output**: `space_satisfaction` score (0.0-1.0)

## 6. Known Limitations and Biases

### 6.1 What Git-audit Cannot Measure

- ❌ **Code correctness**: Actual functionality, performance, security
- ❌ **Non-code contributions**: Meetings, mentoring, design discussions
- ❌ **Developer experience**: Cycle time, flow state, interruptions (requires external data)
- ❌ **Business value**: Impact on users, revenue, strategic importance
- ❌ **Role context**: Junior vs. senior expectations

### 6.2 SPACE Dimension Measurement Quality

| Dimension | Git Measurement Quality | Notes |
|-----------|------------------------|-------|
| **Satisfaction** | ❌ Not measurable | Requires external survey |
| **Performance** | ✅ Good | Churn, commit size, focus measurable from Git |
| **Activity** | ✅ Excellent | Commits, lines, files directly available |
| **Communication** | ✅ Good | Reviews, merges, shared ownership from Git |
| **Efficiency** | ⚠️ Poor | True efficiency needs CI/CD + issue tracker data |

**Recommendation**: For full SPACE implementation, supplement git-audit with:
- Quarterly satisfaction surveys (14 questions)
- CI/CD metrics (build time, deployment frequency)
- Issue tracker integration (cycle time, lead time)

### 6.3 Potential Biases and Mitigations

**Commit Granularity Bias**:
- **Issue**: Frequent small commits vs. batched large commits
- **Mitigation**: Performance dimension rewards appropriate commit sizing (50-200 lines)

**Role Bias**:
- **Issue**: Juniors write more new code; seniors refactor and review
- **Mitigation**: Communication dimension rewards review participation; Performance rewards refactoring (lower churn)

**File Type Bias**:
- **Issue**: Documentation/config contributors appear inflated
- **Mitigation**: Differential weighting (code 100%, docs 50%, config 30%)

**Repository Age Bias**:
- **Issue**: Early contributors accumulate more metrics
- **Mitigation**: Frequency and consistency metrics (commits_freq, days_span ratio) focus on patterns

## 7. Ethical Considerations

### 7.1 Intended Use

**✅ Appropriate Applications**:
- Team retrospectives and improvement planning
- Identifying mentoring opportunities
- Recognizing diverse contributions (code, review, architecture, management)
- Spotting process issues (e.g., siloed knowledge, lack of reviews)
- Celebrating balanced team members

**❌ Inappropriate Applications**:
- Performance reviews as sole evaluation factor
- Compensation decisions based purely on metrics
- Hiring/firing decisions without human judgment
- Comparing developers across different teams/projects
- Automated judgments without context

### 7.2 Gaming and Goodhart's Law

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

### 7.3 Transparency and Team Ownership

**Principles**:
- All metrics and formulas are open-source and documented
- Developers should understand how they're evaluated
- Team should collectively decide metric weights and thresholds
- Regular review and adjustment of evaluation criteria
- Open discussion of limitations and biases

## 8. Validation and Accuracy

### 8.1 What Git-audit Gets Right

✅ **SPACE Framework**: Validated multi-dimensional model from industry research
✅ **Context-aware**: Dynamic thresholds and tri-method normalization adapt to team
✅ **Modern practices**: Recognizes code review, pair programming, diverse artifacts
✅ **Fair weighting**: File type categorization prevents metric gaming
✅ **Research-backed**: Built on highly-cited academic findings

### 8.2 Areas for Continued Research

⚠️ **Satisfaction measurement**: Requires external survey infrastructure
⚠️ **Efficiency proxies**: Git patterns are weak proxies; need CI/CD integration
⚠️ **Temporal dynamics**: Activity trends and velocity changes not yet captured
⚠️ **Role differentiation**: Explicit architect/reviewer/implementer roles not distinguished
⚠️ **Cross-project contributions**: Developers working on multiple repositories not fully captured

---

## References

**SPACE Framework**:
- Forsgren, N., Storey, M. A., Maddila, C., Zimmermann, T., Houck, B., & Butler, J. (2021). The SPACE of Developer Productivity. *ACM Queue*, 19(1), 20-48.

**For complete bibliography (50+ citations), see [ACADEMIC_RESEARCH.md](ACADEMIC_RESEARCH.md)**

**For detailed metric documentation, see [METRICS.md](METRICS.md)**

---

**Last Updated**: October 2025
**Git-audit Version**: SPACE Framework implementation with 7 file categories, tri-method normalization, and AGES integration
