# Git-audit Methodology for AGES Teams

## Introduction

This document adapts git-audit's developer evaluation methodology specifically for **AGES** (Agência Experimental de Engenharia de Software) teams at PUCRS. Unlike industry teams where developers have similar experience levels, AGES teams are educational environments with:

- **Four distinct skill levels** (AGES I through IV)
- **Progressive responsibility model** (juniors to project managers)
- **Mentoring relationships** (seniors supporting juniors)
- **Learning-focused goals** (portfolio building, skill development)
- **Diverse artifact types** (code, architecture, documentation, management)

### Why Standard Metrics Fall Short for AGES

Academic research (Meyer et al., 2014; Forsgren et al., 2021) warns against applying industry metrics to educational contexts:

**Problem 1: Unfair Level Comparisons**
- AGES I student (50 commits, learning basics) vs. AGES IV student (200 commits, full competence)
- Raw metrics penalize juniors who are meeting their learning objectives

**Problem 2: Invisible Contributions**
- AGES III code reviews don't generate commits
- AGES IV project management work isn't captured in Git
- AGES II database design produces fewer lines than AGES I implementation

**Problem 3: Role Mismatch**
- Quality metrics (churn ratio) penalize AGES I students who are learning through trial/error
- Productivity metrics miss AGES III/IV mentoring and oversight work

### Academic Foundation

This methodology is based on:

**SPACE Framework** (Forsgren et al., 2021):
- **Activity**: Measured via commits, code volume (all levels)
- **Communication**: Measured via code reviews, mentoring, collaboration (AGES II-IV)
- **Performance**: Code quality indicators (AGES III-IV expected to excel)

**Mockus & Herbsleb (2002)** - Expertise measurement:
- Recognizes that expertise develops over time
- Recent activity weighted higher than old activity
- Role-specific expertise expectations

**Bird et al. (2011)** - Shared ownership:
- Collaboration improves quality in student teams
- Mentoring relationships visible through shared file editing

**Bacchelli & Bird (2013)** - Code review value:
- Reviewers contribute significantly to quality
- Critical for AGES III students who lead reviews

---

## AGES-Specific Adaptations

### 1. Level-Adjusted Evaluation

#### Concept: Role-Relative Assessment

Each AGES level has different responsibilities and expected output patterns. Metrics should be interpreted **relative to role expectations**, not absolute values.

**Academic Justification**:
- Meyer et al. (2014): "Productivity should be evaluated relative to context"
- Gousios & Spinellis (2014): "Within-group comparisons more valid than absolute thresholds"

#### Implementation: Segmented Team Analysis

**Step 1: Segment developers by AGES level**
```
Team composition identified from:
- Project documentation
- Repository analysis (activity patterns)
- Manual classification if needed
```

**Step 2: Calculate metrics within each level**
```
AGES I group: Compare AGES I students to each other
AGES II group: Compare AGES II students to each other
AGES III group: Compare AGES III students to each other
AGES IV group: Compare AGES IV students to each other (often just 1-2 students)
```

**Step 3: Apply level-specific weights and thresholds**

| Dimension | AGES I Weight | AGES II Weight | AGES III Weight | AGES IV Weight |
|-----------|---------------|----------------|-----------------|----------------|
| **Productivity** | 50% | 45% | 35% | 30% |
| **Quality** | 20% | 25% | 35% | 30% |
| **Collaboration** | 30% | 30% | 30% | 40% |

**Rationale**:
- **AGES I**: Focus on output volume (learning by doing)
- **AGES II**: Balanced development and quality awareness
- **AGES III**: Quality and architecture focus (code reviews, patterns)
- **AGES IV**: Leadership and collaboration emphasis (project management)

---

### 2. Mentoring Recognition

#### Problem: Invisible Mentoring Work

AGES III and IV students spend significant time mentoring juniors, but this doesn't appear in traditional metrics.

**Research Support**:
- Bacchelli & Bird (2013): Reviewers contribute to quality without authoring
- Bird et al. (2011): Shared file ownership indicates collaboration and knowledge transfer

#### Solution: Mentoring Indicators

**Indicator 1: Code Review Participation**
- Already measured: `reviews_given` metric
- AGES III/IV students expected to have high review counts
- Weight increased in Collaboration dimension for senior levels

**Indicator 2: Shared File Editing Patterns**
```
Mentoring Signal = (files touched by both senior and junior) / (total files touched by senior)

High mentoring: >50% of senior's files also touched by juniors
Interpretation: Senior is working alongside juniors, not in isolation
```

**Indicator 3: Co-authorship Credits**
- Already measured: `commits_coauthored` metric
- Tracks pair programming and collaborative work
- Common in AGES teams during knowledge transfer

**Indicator 4: Review Response Ratio**
```
Review Response = (junior commits after senior review) / (senior reviews given)

Effective mentoring: >0.8 (juniors act on feedback)
Interpretation: Senior reviews leading to junior improvements
```

#### Adjusted Collaboration Score for AGES III/IV

For AGES III and IV students, collaboration score emphasizes mentoring:

```
Collaboration Score (AGES III/IV) =
  0.20 × merge_activity
  + 0.20 × shared_file_ownership
  + 0.35 × review_participation  (increased from 20%)
  + 0.15 × co_authorship
  + 0.10 × activity_span
```

---

### 3. Artifact Type Weighting Adjustment

#### Problem: AGES II Documentation vs. AGES I Code

AGES produces diverse artifact types with varying Git visibility:

| Level | Primary Artifacts | Git Visibility | Lines Generated |
|-------|------------------|----------------|-----------------|
| **AGES I** | Feature code, tests | High | 500-2000 LOC |
| **AGES II** | Database schemas, mockups, docs | Medium | 200-1000 LOC |
| **AGES III** | Architecture diagrams, API design | Low | 100-500 LOC |
| **AGES IV** | Project plans, backlog, risk plans | Very Low | 50-200 LOC |

**Research Context**:
- Jones (1986): LOC varies dramatically by activity type
- Boehm (1981): "More code ≠ more value"

#### Solution: Enhanced File Type Categorization for AGES

Extend standard file categorization with AGES-specific artifact types:

**Standard Categories** (from METHODOLOGY.md):
- Code: 100% weight
- Documentation: 50% weight
- Configuration: 30% weight

**AGES-Specific Extensions**:

```python
# Database artifacts (AGES II focus)
DATABASE_EXTENSIONS = {'.sql', '.mwb', '.erd', '.dbml'}
DATABASE_WEIGHT = 80%  # High technical value

# Architecture artifacts (AGES III focus)
ARCHITECTURE_EXTENSIONS = {'.puml', '.drawio', '.archimate'}
ARCHITECTURE_WEIGHT = 90%  # Very high technical value

# Project management artifacts (AGES IV focus)
MANAGEMENT_EXTENSIONS = {'.md', '.xlsx', '.mpp', '.gan'}
MANAGEMENT_FILES = {'BACKLOG', 'WBS', 'RISK', 'COMMUNICATION_PLAN'}
MANAGEMENT_WEIGHT = 60%  # Important but lower code intensity
```

**Rationale**:
- Database design is highly technical (80% weight)
- Architecture artifacts are critical (90% weight)
- Management artifacts are valuable but text-heavy (60% weight)
- Prevents AGES I students from appearing disproportionately productive

---

### 4. Learning Trajectory Analysis

#### Concept: Growth Over Time

AGES is educational - **growth matters more than absolute performance**.

**Research Support**:
- Fritz et al. (2010): Recent activity predicts current knowledge
- González-Barahona et al. (2009): Temporal patterns reveal developer trajectory

#### Implementation: Temporal Segmentation

**Step 1: Split project into phases**
```
Early phase: First 1/3 of project timeline
Mid phase: Middle 1/3 of project timeline
Late phase: Final 1/3 of project timeline
```

**Step 2: Calculate metrics per phase**
```
commits_early, commits_mid, commits_late
quality_early, quality_mid, quality_late
collab_early, collab_mid, collab_late
```

**Step 3: Calculate growth indicators**
```
Productivity Growth = (commits_late - commits_early) / commits_early
Quality Growth = (quality_late - quality_early) / quality_early
Collaboration Growth = (collab_late - collab_early) / collab_early
```

**Step 4: Reward positive growth**

For AGES I and II students (still learning):
```
Overall Score =
  0.60 × current_performance
  + 0.40 × growth_trajectory
```

For AGES III and IV students (expected competence):
```
Overall Score =
  0.80 × current_performance
  + 0.20 × growth_trajectory
```

**Interpretation**:
- **High current + high growth**: Excellent student, meeting expectations
- **Low current + high growth**: Struggling initially but improving (positive)
- **High current + low growth**: Strong from start, consistent
- **Low current + low growth**: May need additional support

#### Growth-Adjusted Ranking

Standard ranking: Sort by `overall_score` (final performance)

AGES ranking: Sort by `overall_score × (1 + 0.2 × growth_factor)`
- Rewards students who show significant improvement
- Aligns with educational goals (learning, not just output)

---

### 5. Team Formation Insights

#### Concept: Data-Driven Team Composition

Git-audit metrics can inform team formation and role assignment for future semesters.

**Research Context**:
- Bird et al. (2009): Team composition affects project outcomes
- Distributed teams need balanced skill distribution

#### Analysis: Developer Profiles

**Profile 1: High Productivity, Low Quality**
```
Characteristics:
- High commits, lines, files
- High churn ratio, large commits
- Low code review participation

AGES Fit: AGES I (expected pattern - learning through volume)
Risk if AGES III/IV: May need quality mentoring
```

**Profile 2: High Quality, Low Productivity**
```
Characteristics:
- Low commits, lines, files
- Low churn ratio, small focused commits
- High code review participation

AGES Fit: AGES III (expected pattern - oversight role)
Risk if AGES I: May be stuck, needs support
```

**Profile 3: High Collaboration**
```
Characteristics:
- High shared file percentage
- High reviews given
- High co-authored commits

AGES Fit: AGES III/IV (mentoring role)
Also good: AGES II supporting AGES I
```

**Profile 4: Balanced All-Rounder**
```
Characteristics:
- Above-average productivity
- Above-average quality
- Above-average collaboration

AGES Fit: AGES II/III/IV (versatile team member)
Ideal: Future AGES IV candidate
```

#### Team Composition Recommendations

Based on research (Bird et al., 2011; Bacchelli & Bird, 2013):

**Optimal AGES Team Balance**:

| Role | Ideal Profile | Team Ratio | Rationale |
|------|--------------|------------|-----------|
| **AGES IV** | Balanced + High Collaboration | 1-2 (10-15%) | Leadership, can cover any gap |
| **AGES III** | High Quality + High Collaboration | 2-3 (20-25%) | Architectural oversight, code review |
| **AGES II** | Balanced | 2-4 (25-30%) | Database design, mentoring AGES I |
| **AGES I** | High Productivity acceptable | 3-5 (35-45%) | Feature development, learning |

**Red Flags in Team Composition**:
- ❌ No AGES III with High Collaboration → Quality risk (no effective code review)
- ❌ All AGES I with High Productivity, Low Quality → Technical debt accumulation
- ❌ AGES IV with Low Collaboration → Leadership gap
- ❌ Team has no Balanced profiles → Specialization silos, knowledge bottlenecks

---

### 6. Stakeholder Communication Strategy

#### For Students: Individual Feedback

**What to Share**:
✅ Level-relative ranking (compare within AGES I, II, III, IV groups)
✅ Growth trajectory (improvement over time)
✅ Strength identification (productivity, quality, or collaboration focus)
✅ Comparison to expected role profile

**What NOT to Share**:
❌ Absolute rankings across all levels (unfair comparison)
❌ Raw metrics without context (commit count meaningless alone)
❌ Metrics as sole evaluation (qualitative assessment also needed)

**Sample Student Report**:
```
AGES II Student: Maria Silva

Level-Relative Performance:
- Rank: 2nd out of 4 AGES II students
- Overall Score: 0.75 (Above Average)

Dimension Breakdown:
- Productivity: 0.70 (Average) - On track for AGES II expectations
- Quality: 0.85 (Excellent) - Low churn ratio, focused commits
- Collaboration: 0.70 (Above Average) - Good shared file engagement

Growth Trajectory:
- Productivity growth: +45% (Good - consistent improvement)
- Quality growth: +20% (Stable - maintained good practices)
- Collaboration growth: +60% (Excellent - increasing team engagement)

Strengths:
- High quality practices (low churn, focused commits)
- Strong improvement in collaboration over semester
- Database design files show high technical contribution

Development Areas:
- Could increase commit frequency (currently below AGES II median)
- Opportunity to mentor AGES I students more actively

Profile: High Quality, Growing Collaboration → Strong AGES III candidate
```

#### For Professors: Team Analytics

**What to Analyze**:
✅ Team composition balance
✅ Mentoring effectiveness (AGES III/IV review impact on AGES I/II)
✅ Outlier identification (students needing support)
✅ Learning trajectory patterns
✅ Role fit assessment

**Sample Professor Dashboard**:
```
Project: Sistema de Gestão Acadêmica
Team: 12 students (AGES I: 4, AGES II: 4, AGES III: 3, AGES IV: 1)

Team Health Indicators:
✅ Collaboration Index: 0.72 (Good - above 0.60 threshold)
✅ Quality Distribution: Balanced (no outliers with churn > 1.0)
⚠️ Productivity Variance: High (CV = 0.65 - some students very low)

Mentoring Effectiveness:
- AGES III code reviews: 89 total
- AGES I/II commits after review: 76 (85% response rate - Excellent)
- Shared file engagement: 68% (Good knowledge transfer)

Concerns:
⚠️ Student João (AGES I): Productivity 0.25, Quality 0.30, Collab 0.20
   → Recommendation: Check for blockers, pair with mentor

⚠️ Student Ana (AGES II): High productivity (0.95) but low quality (0.35)
   → Recommendation: AGES III code review focus on Ana's commits

Strengths:
✅ Student Carlos (AGES III): Excellent collaboration (0.92), high review count
   → Strong mentor, consider for future AGES IV role

✅ Student Beatriz (AGES IV): Balanced performance, high collaboration
   → Effective project leadership evident in metrics
```

---

## Implementation Recommendations

### Phase 1: Baseline (Current Semester)

**Goal**: Establish baseline metrics without changing evaluation practices

**Actions**:
1. Run git-audit on all AGES project repositories
2. Manually classify students by AGES level
3. Generate level-segmented reports
4. Identify typical metric ranges per level
5. Validate patterns with professor observations

**Outcome**: Understand normal AGES metric distributions

---

### Phase 2: Pilot Integration (Next Semester)

**Goal**: Use metrics to supplement qualitative assessment

**Actions**:
1. Share git-audit reports with professors mid-semester
2. Use metrics to identify students needing support early
3. Compare git-audit profiles with professor assessments
4. Refine level-specific weights based on feedback
5. Test growth trajectory analysis

**Outcome**: Validated AGES-specific methodology

---

### Phase 3: Operational Use (Subsequent Semesters)

**Goal**: Integrate git-audit into AGES evaluation framework

**Actions**:
1. Generate automated reports at sprint boundaries
2. Provide students with level-relative feedback
3. Use metrics for team formation decisions
4. Track longitudinal patterns (student progression I→II→III→IV)
5. Continuously refine methodology based on outcomes

**Outcome**: Metrics-informed educational environment

---

## Ethical Considerations for Educational Use

### Student Rights and Transparency

**Principle 1: Students must understand how they're evaluated**
- Share git-audit methodology at semester start
- Explain level-specific expectations
- Clarify that metrics supplement, not replace, qualitative assessment

**Principle 2: Metrics should support learning, not punish it**
- Reward growth trajectory, not just absolute performance
- Recognize diverse contribution types (code, review, architecture, management)
- Use metrics to identify support needs, not for punishment

**Principle 3: Privacy and consent**
- Students should consent to metric collection
- Individual metrics should be private (only shared with student and professor)
- Team-level analytics can be shared more broadly

### Academic Integrity

**Metrics Can Detect**:
✅ Low commit frequency + high lines per commit → Possible batch copying
✅ Zero shared files + zero collaboration → Working in isolation
✅ Sudden activity spikes → Possible deadline cramming or external help

**Appropriate Response**:
- Investigate patterns that suggest issues
- Have conversations with students (metrics start discussions)
- Consider context (personal issues, blockers, learning style)
- Don't auto-penalize based on metrics alone

### Cultural Sensitivity

AGES teams often include:
- Students with varying programming backgrounds
- Part-time students balancing work/studies
- International students adapting to new environments

**Recommendation**: Use metrics to identify students needing **support**, not to create competitive pressure. Educational goal is collective success, not ranking.

---

## Research-Backed Modifications Summary

### Standard git-audit → AGES git-audit

| Aspect | Standard (Industry) | AGES (Educational) |
|--------|--------------------|--------------------|
| **Comparison Group** | All developers | Segmented by AGES level |
| **Productivity Weight** | 40% (all roles) | 50% (I) → 30% (IV) |
| **Quality Weight** | 30% (all roles) | 20% (I) → 35% (III) |
| **Collaboration Weight** | 30% (all roles) | 30% (I-III) → 40% (IV) |
| **File Type Weights** | Code/Docs/Config | + Database/Architecture/Management |
| **Primary Metric** | Absolute performance | Growth trajectory + performance |
| **Evaluation Goal** | Team contribution | Learning progress + contribution |
| **Use Case** | Performance review | Formative feedback + team formation |

---

## Validation Plan

### Quantitative Validation

**Step 1: Correlation Analysis**
- Compare git-audit scores with final grades (AGES I-IV courses)
- Expected: Moderate correlation (0.4-0.6) - metrics capture some but not all performance

**Step 2: Professor Agreement**
- Professors rank top/bottom students qualitatively
- Compare with git-audit rankings
- Calculate inter-rater reliability (Cohen's kappa)

**Step 3: Longitudinal Tracking**
- Track students across AGES I → II → III → IV
- Validate that metrics improve as students advance
- Expected: Clear progression in quality and collaboration scores

### Qualitative Validation

**Step 1: Student Interviews**
- Do students feel metrics accurately reflect their contribution?
- Do students find feedback actionable?
- Any gaming behaviors observed?

**Step 2: Professor Feedback**
- Do metrics reveal insights professors didn't notice?
- Any false positives/negatives?
- What adjustments would improve accuracy?

**Step 3: Stakeholder Review**
- Do clients' perceptions align with team metrics?
- Do high-collaboration teams deliver better products?
- Do high-quality metrics correlate with fewer bugs?

---

## References and Academic Support

This methodology is based on research detailed in [ACADEMIC_RESEARCH.md](ACADEMIC_RESEARCH.md), particularly:

**Multi-dimensional Assessment**:
- Forsgren et al. (2021): SPACE framework - educational adaptation
- Meyer et al. (2014): Context-dependent productivity measurement

**Role-Specific Evaluation**:
- Mockus & Herbsleb (2002): Expertise varies by experience level
- Fritz et al. (2010): Recent activity indicates current knowledge

**Collaboration and Mentoring**:
- Bacchelli & Bird (2013): Code review contribution recognition
- Bird et al. (2011): Shared ownership in educational teams

**Temporal Analysis**:
- González-Barahona et al. (2009): Developer progression patterns
- Fritz et al. (2010): Recency weighting for skill assessment

**Metrics Criticism**:
- Kalliamvakou et al. (2014): Within-group comparison validity
- Goodhart (1975): Gaming prevention through multiple metrics

---

## Summary

AGES teams require specialized evaluation methodology because:

1. **Mixed skill levels**: AGES I-IV have different expectations
2. **Educational goals**: Growth matters more than absolute performance
3. **Diverse artifacts**: Code, architecture, documentation, management
4. **Mentoring emphasis**: Senior students support juniors
5. **Learning environment**: Mistakes are part of the process

**Key Adaptations**:
- ✅ Level-segmented comparison groups
- ✅ Role-adjusted dimension weights
- ✅ Artifact type recognition (database, architecture, management)
- ✅ Growth trajectory analysis
- ✅ Mentoring contribution tracking
- ✅ Formative feedback focus

**Expected Outcomes**:
- Fair evaluation across skill levels
- Early identification of students needing support
- Recognition of diverse contributions (not just code volume)
- Improved team formation based on complementary profiles
- Data-driven mentoring effectiveness assessment

---

**For general git-audit methodology, see [METHODOLOGY.md](METHODOLOGY.md)**

**For academic research foundations, see [ACADEMIC_RESEARCH.md](ACADEMIC_RESEARCH.md)**

**For standard metrics documentation, see [METRICS.md](METRICS.md)**

**For AGES team structure details, see [TEAM_FORMATION.md](TEAM_FORMATION.md)**

**Last Updated**: October 2025
**Context**: AGES program at PUCRS - Educational software development agency
