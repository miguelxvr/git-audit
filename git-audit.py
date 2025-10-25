#!/usr/bin/env python3
"""
Enhanced developer evaluation tool with SPACE framework and AGES-specific features.
Generates 86 metrics per developer (79 Git metrics + 6 SPACE scores + AGES level).

Usage:
  python3 git-audit.py > output.csv
  python3 git-audit.py --repo https://github.com/user/repo.git > output.csv
  python3 git-audit.py --print --output team_analysis.csv

See docs/METHODOLOGY.md for SPACE framework implementation details.
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
from datetime import datetime
from typing import Dict, List, Optional, Set

# Configuration
GIT_LOG_FORMAT = "%H%x09%an%x09%ae%x09%ad%n%B%n--END-COMMIT--"
SPACE_WEIGHTS = {
    "satisfaction": 0.15,
    "performance": 0.20,
    "activity": 0.25,
    "communication": 0.25,
    "efficiency": 0.15,
}

FILE_CATEGORIES = {
    "test": {
        "ext": {".test.js", ".test.ts", ".spec.js", ".spec.py"},
        "pat": {"test-plan", "test-report"},
        "wgt": 0.7,
    },
    "database": {
        "ext": {".sql", ".mwb", ".erd", ".dbml"},
        "pat": {"schema", "migrations", "database"},
        "wgt": 0.8,
    },
    "architecture": {
        "ext": {".puml", ".drawio", ".uml"},
        "pat": {"architecture", "component-diagram", "class-diagram"},
        "wgt": 0.9,
    },
    "management": {
        "ext": set(),
        "pat": {"backlog", "wbs", "sprint-plan", "user-stories"},
        "wgt": 0.6,
    },
    "code": {
        "ext": {
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".java",
            ".c",
            ".cpp",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".swift",
            ".kt",
            ".html",
            ".css",
            ".vue",
        },
        "pat": set(),
        "wgt": 1.0,
    },
    "docs": {
        "ext": {".md", ".txt", ".rst", ".adoc", ".pdf"},
        "pat": {"readme", "license", "changelog"},
        "wgt": 0.5,
    },
    "config": {
        "ext": {".json", ".yaml", ".yml", ".xml", ".toml", ".ini", ".env"},
        "pat": {"makefile", "dockerfile", "package.json"},
        "wgt": 0.3,
    },
}

OUTPUT_FIELDS = [
    "author_name",
    "author_email",
    "ages_level",
    "commits_non_merge",
    "commits_merge",
    "commits_bugfix",
    "commits_feature",
    "commits_total",
    "commits_bugfix_ratio",
    "commits_coauthored",
    "lines_added",
    "lines_deleted",
    "lines_total",
    *[f"lines_{c}_{o}" for c in FILE_CATEGORIES for o in ["added", "deleted", "total"]],
    "files_added",
    "files_deleted",
    "files_modified",
    "files_binary",
    "files_total",
    "files_touched",
    *[
        f"files_{c}_{o}"
        for c in FILE_CATEGORIES
        for o in ["added", "deleted", "modified", "total"]
    ],
    "lines_per_commit_avg",
    "files_per_commit_avg",
    "commits_freq",
    "lines_churn_ratio",
    "days_active",
    "days_span",
    "commits_first_date",
    "commits_last_date",
    "reviews_given",
    "commits_team_pct",
    "lines_team_pct",
    "files_team_pct",
    "space_satisfaction",
    "space_performance",
    "space_activity",
    "space_communication",
    "space_efficiency",
    "space_overall",
]


def categorize_file(filename: str) -> str:
    fl, bn = filename.lower(), filename.lower().split("/")[-1]
    bn_no_ext = bn.rsplit(".", 1)[0] if "." in bn else bn
    for cat, cfg in FILE_CATEGORIES.items():
        if any(fl.endswith(e) for e in cfg["ext"]) or any(
            p in bn_no_ext for p in cfg["pat"]
        ):
            return cat
    return "other"


@dataclass
class AuthorStats:
    """Aggregate statistics for a single author."""

    author_name: str = ""
    commits_non_merge: int = 0
    commits_merge: int = 0
    commits_bugfix: int = 0
    commits_coauthored: int = 0
    reviews_given: int = 0
    lines_by_category: Dict = field(
        default_factory=lambda: {c: {"added": 0, "deleted": 0} for c in FILE_CATEGORIES}
    )
    files_by_category: Dict = field(
        default_factory=lambda: {
            c: {"added": 0, "deleted": 0, "modified": 0} for c in FILE_CATEGORIES
        }
    )
    files_binary: int = 0
    total_files_changed: int = 0
    days_active: Set[str] = field(default_factory=set)
    files: Set[str] = field(default_factory=set)
    commits_first_date: str = ""
    commits_last_date: str = ""

    # Properties
    lines_added = property(
        lambda s: sum(c["added"] for c in s.lines_by_category.values())
    )
    lines_deleted = property(
        lambda s: sum(c["deleted"] for c in s.lines_by_category.values())
    )
    lines_total = property(lambda s: s.lines_added + s.lines_deleted)
    files_added = property(
        lambda s: sum(c["added"] for c in s.files_by_category.values())
    )
    files_deleted = property(
        lambda s: sum(c["deleted"] for c in s.files_by_category.values())
    )
    files_modified = property(
        lambda s: sum(c["modified"] for c in s.files_by_category.values())
    )
    commits_total = property(lambda s: s.commits_non_merge + s.commits_merge)
    commits_feature = property(lambda s: max(0, s.commits_non_merge - s.commits_bugfix))
    commits_bugfix_ratio = property(
        lambda s: round((s.commits_bugfix / s.commits_non_merge) * 100, 2)
        if s.commits_non_merge
        else 0.0
    )
    lines_per_commit_avg = property(
        lambda s: round(s.lines_total / s.commits_non_merge, 2)
        if s.commits_non_merge
        else 0.0
    )
    files_per_commit_avg = property(
        lambda s: round(s.total_files_changed / s.commits_non_merge, 2)
        if s.commits_non_merge
        else 0.0
    )
    commits_freq = property(
        lambda s: round(s.commits_non_merge / len(s.days_active), 2)
        if s.days_active
        else 0.0
    )
    lines_churn_ratio = property(
        lambda s: round(s.lines_deleted / s.lines_added, 2) if s.lines_added else 0.0
    )

    @property
    def days_span(self) -> int:
        if not self.commits_first_date or not self.commits_last_date:
            return 0
        try:
            return (
                datetime.strptime(self.commits_last_date, "%Y-%m-%d")
                - datetime.strptime(self.commits_first_date, "%Y-%m-%d")
            ).days
        except:
            return 0

    def to_dict(self, email: str, metrics: Optional[Dict] = None) -> Dict:
        result = {
            k: getattr(self, k)
            for k in [
                "author_name",
                "commits_non_merge",
                "commits_merge",
                "commits_bugfix",
                "commits_feature",
                "commits_total",
                "commits_bugfix_ratio",
                "commits_coauthored",
                "lines_added",
                "lines_deleted",
                "lines_total",
                "files_added",
                "files_deleted",
                "files_modified",
                "files_binary",
                "lines_per_commit_avg",
                "files_per_commit_avg",
                "commits_freq",
                "lines_churn_ratio",
                "reviews_given",
            ]
        }
        result.update(
            {
                "author_email": email,
                "files_total": self.total_files_changed,
                "files_touched": len(self.files),
                "days_active": len(self.days_active),
                "days_span": self.days_span,
                "commits_first_date": self.commits_first_date,
                "commits_last_date": self.commits_last_date,
            }
        )
        for cat in FILE_CATEGORIES:
            result.update(
                {
                    f"lines_{cat}_added": self.lines_by_category[cat]["added"],
                    f"lines_{cat}_deleted": self.lines_by_category[cat]["deleted"],
                    f"lines_{cat}_total": sum(self.lines_by_category[cat].values()),
                    f"files_{cat}_added": self.files_by_category[cat]["added"],
                    f"files_{cat}_deleted": self.files_by_category[cat]["deleted"],
                    f"files_{cat}_modified": self.files_by_category[cat]["modified"],
                    f"files_{cat}_total": sum(self.files_by_category[cat].values()),
                }
            )
        result.update(
            metrics
            or {
                "ages_level": "",
                "commits_team_pct": 0.0,
                "lines_team_pct": 0.0,
                "files_team_pct": 0.0,
                "space_satisfaction": 0.0,
                "space_performance": 0.0,
                "space_activity": 0.0,
                "space_communication": 0.0,
                "space_efficiency": 0.0,
                "space_overall": 0.0,
            }
        )
        return result


def run_git(args: List[str], cwd: str = None) -> str:
    try:
        return subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, check=True
        ).stdout
    except subprocess.CalledProcessError as e:
        sys.stderr.write(e.stderr or "")
        raise


normalize_author = lambda email: email.strip().lower()
is_bugfix = lambda msg: any(
    p in msg.lower()
    for p in [
        "fix",
        "bug",
        "issue #",
        "hotfix",
        "patch",
        "resolve",
        "closes #",
        "repair",
    ]
)


def extract_reviews(msg: str, author: str, stats: Dict[str, AuthorStats]) -> None:
    for p in [
        r"Reviewed-by:\s*(?:[^<]*<)?([^>@\s]+@[^>\s]+)",
        r"Co-authored-by:\s*(?:[^<]*<)?([^>@\s]+@[^>\s]+)",
        r"Acked-by:\s*(?:[^<]*<)?([^>@\s]+@[^>\s]+)",
    ]:
        for email in re.findall(p, msg, re.IGNORECASE | re.MULTILINE):
            reviewer = normalize_author(email.strip())
            if reviewer != author:
                stats.setdefault(reviewer, AuthorStats())
                if "co-authored" in p.lower():
                    stats[author].commits_coauthored += 1
                    stats[reviewer].commits_coauthored += 1
                else:
                    stats[reviewer].reviews_given += 1


def update_stats(
    stats: AuthorStats,
    cat: str,
    added: int,
    deleted: int,
    op: str = None,
    is_file: bool = False,
) -> None:
    if cat != "other":
        if is_file and op:
            stats.files_by_category[cat][op] += 1
        elif not is_file:
            stats.lines_by_category[cat]["added"] += added
            stats.lines_by_category[cat]["deleted"] += deleted


def parse_log(output: str, stats: Dict[str, AuthorStats]) -> None:
    current, msg, in_msg = None, [], False
    for line in output.splitlines():
        if line == "--END-COMMIT--":
            if current and msg:
                full_msg, author = "\n".join(msg), current[2]
                if is_bugfix(full_msg):
                    stats[author].commits_bugfix += 1
                extract_reviews(full_msg, author, stats)
            msg, in_msg = [], False
        elif line.count("\t") == 3:
            sha, name, email, date = line.split("\t")
            email = normalize_author(email)
            current, in_msg = (sha, name, email, date), True
            s = stats.setdefault(email, AuthorStats())
            if not s.author_name:
                s.author_name = name
            s.commits_non_merge += 1
            s.days_active.add(date)
            if not s.commits_first_date:
                s.commits_first_date = date
            s.commits_last_date = date
        elif line and current and line.count("\t") == 2 and not in_msg:
            adds, dels, path = line.split("\t")
            s = stats[current[2]]
            if adds == "-" and dels == "-":
                s.files_binary += 1
            else:
                update_stats(
                    s,
                    categorize_file(path),
                    int(adds) if adds != "-" else 0,
                    int(dels) if dels != "-" else 0,
                )
            s.total_files_changed += 1
        elif in_msg:
            msg.append(line)


def calc_file_ops(
    args: List[str], stats: Dict[str, AuthorStats], cwd: str = None
) -> None:
    output, curr = (
        run_git(["log"] + args + ["--name-status", "--no-merges", "--format=%ae"], cwd),
        None,
    )
    for line in output.splitlines():
        if "@" in line and "." in line and " " not in line and "/" not in line:
            curr = normalize_author(line.strip())
            stats.setdefault(curr, AuthorStats())
        elif line and curr and "\t" in line:
            status, path = (
                line.split("\t")[0].strip(),
                line.split("\t")[1] if len(line.split("\t")) > 1 else "",
            )
            op = (
                "modified"
                if status[0] in "MR"
                else "deleted"
                if status[0] == "D"
                else "added"
                if status[0] in "AC"
                else None
            )
            if op:
                update_stats(
                    stats[curr], categorize_file(path), 0, 0, op=op, is_file=True
                )


def gather_stats(
    args: List[str], no_merges: bool, cwd: str = None
) -> Dict[str, AuthorStats]:
    stats = {}
    log_args = (
        ["log"]
        + args
        + ["--numstat", "--date=short", f"--format={GIT_LOG_FORMAT}"]
        + (["--no-merges"] if no_merges else [])
    )
    parse_log(run_git(log_args, cwd), stats)

    for line in run_git(
        ["log"] + args + ["--merges", "--format=%ae"], cwd
    ).splitlines():
        stats.setdefault(
            normalize_author(line.strip()), AuthorStats()
        ).commits_merge += 1

    calc_file_ops(args, stats, cwd)

    log_args = (
        ["log"]
        + args
        + ["--name-only", "--format=%ae"]
        + (["--no-merges"] if no_merges else [])
    )
    output, curr = run_git(log_args, cwd), None
    for line in output.splitlines():
        if "@" in line and "." in line and " " not in line and "/" not in line:
            curr = normalize_author(line.strip())
            stats.setdefault(curr, AuthorStats())
        elif line.strip() and curr and ("/" in line or "." in line):
            stats[curr].files.add(line.strip())

    return stats


score_range = (
    lambda v, mn, mx, b=0.6, a=0.6: 1.0
    if mn <= v <= mx
    else (b + (v / mn) * (1.0 - b) if v > 0 else b)
    if v < mn
    else max(0.3, 1.0 - ((v - mx) / mx) * 0.5)
)


def calc_performance(s: AuthorStats) -> float:
    churn = (
        1.0 if s.lines_churn_ratio < 0.3 else max(0.2, 1.0 - s.lines_churn_ratio * 0.8)
    )
    return round(
        0.30 * churn
        + 0.20 * score_range(s.lines_per_commit_avg, 50, 200)
        + 0.20 * score_range(s.files_per_commit_avg, 1, 3)
        + 0.15 * score_range(s.commits_bugfix_ratio, 15, 35, 0.6, 0.5)
        + 0.15
        * score_range(
            (s.commits_merge / s.commits_total if s.commits_total else 0) * 100,
            5,
            15,
            0.7,
            0.6,
        ),
        3,
    )


def calc_activity(s: AuthorStats, c_n: float, l_n: float, f_n: float) -> float:
    cons = 0.0
    if s.days_span > 0:
        cons = 0.60 * (len(s.days_active) / s.days_span) + 0.40 * min(
            s.commits_freq / 2.0, 1.0
        )
    return round(0.40 * c_n + 0.30 * l_n + 0.20 * f_n + 0.10 * cons, 3)


def calc_communication(
    s: AuthorStats, shared: float, integ: float, proj_days: int
) -> float:
    review = 0.70 * min(s.reviews_given / 10.0, 1.0) + 0.30 * min(
        s.commits_coauthored / 5.0, 1.0
    )
    own = (
        1.0
        if 0.30 <= shared <= 0.70
        else (
            0.4 + (shared / 0.30) * 0.6
            if shared < 0.30
            else max(0.9, 1.0 - (shared - 0.70) * 0.33)
        )
    )
    engage = min(s.days_span / proj_days, 1.0) if proj_days else 0.0
    return round(0.30 * review + 0.30 * own + 0.25 * integ + 0.15 * engage, 3)


def calc_efficiency(s: AuthorStats) -> float:
    rework = max(0.2, 1.0 - s.lines_churn_ratio) if s.lines_churn_ratio <= 1.0 else 0.2
    return round(
        0.35 * score_range(s.lines_per_commit_avg, 50, 200)
        + 0.30 * score_range(s.files_per_commit_avg, 1, 3)
        + 0.20 * score_range(s.commits_freq, 1.0, 2.0, 0.4, 0.7)
        + 0.15 * rework,
        3,
    )


def normalize_tri(v: float, vals: List[float]) -> float:
    if not vals:
        return 0.0
    mn, mx = min(vals), max(vals)
    rel = (v - mn) / (mx - mn) if mx > mn else 0.5
    s = sorted(vals)
    p25, p90 = (
        max(s[max(0, int(len(s) * 0.25) - 1)], 1),
        max(s[min(len(s) - 1, int(len(s) * 0.90))], 10),
    )
    abs_n = max(0.0, min(1.0, (v - p25) / (p90 - p25))) if p90 > p25 else 0.5
    stat = (sum(1 for x in vals if x < v) + 0.5 * sum(1 for x in vals if x == v)) / len(
        vals
    )
    return round((rel + abs_n + stat) / 3, 3)


def calc_shared_pct(
    files: Set[str], all_stats: Dict[str, AuthorStats], author: str
) -> float:
    if not files:
        return 0.0
    other = set()
    for email, s in all_stats.items():
        if email != author:
            other.update(s.files)
    return round((len(files & other) / len(files)) * 100, 2)


def calc_space_scores(
    stats: Dict[str, AuthorStats], sat: Dict[str, float] = None
) -> Dict[str, Dict]:
    dates = [
        d
        for s in stats.values()
        for d in [s.commits_first_date, s.commits_last_date]
        if d
    ]
    proj_days = (
        (
            max([datetime.strptime(d, "%Y-%m-%d") for d in dates])
            - min([datetime.strptime(d, "%Y-%m-%d") for d in dates])
        ).days
        if dates
        else 1
    )

    w_lines = {
        e: sum(
            (s.lines_by_category[c]["added"] + s.lines_by_category[c]["deleted"])
            * FILE_CATEGORIES[c]["wgt"]
            for c in FILE_CATEGORIES
        )
        for e, s in stats.items()
    }
    w_files = {
        e: sum(
            sum(s.files_by_category[c].values()) * FILE_CATEGORIES[c]["wgt"]
            for c in FILE_CATEGORIES
        )
        for e, s in stats.items()
    }
    merges = {e: s.commits_merge for e, s in stats.items()}

    commits_v, lines_v, files_v, merge_v = (
        [s.commits_non_merge for s in stats.values()],
        list(w_lines.values()),
        list(w_files.values()),
        list(merges.values()),
    )

    result = {}
    for email, s in stats.items():
        satisfaction = sat.get(email, 0.0) if sat else 0.0
        perf = calc_performance(s)
        act = calc_activity(
            s,
            normalize_tri(s.commits_non_merge, commits_v),
            normalize_tri(w_lines[email], lines_v),
            normalize_tri(w_files[email], files_v),
        )
        comm = calc_communication(
            s,
            calc_shared_pct(s.files, stats, email) / 100,
            normalize_tri(merges[email], merge_v),
            proj_days,
        )
        eff = calc_efficiency(s)
        overall = sum(
            SPACE_WEIGHTS[k] * v
            for k, v in zip(
                [
                    "satisfaction",
                    "performance",
                    "activity",
                    "communication",
                    "efficiency",
                ],
                [satisfaction, perf, act, comm, eff],
            )
        )
        result[email] = {
            "space_satisfaction": round(satisfaction, 3),
            "space_performance": perf,
            "space_activity": act,
            "space_communication": comm,
            "space_efficiency": eff,
            "space_overall": round(overall, 3),
        }
    return result


def calc_relative(stats: Dict[str, AuthorStats]) -> Dict[str, Dict]:
    tot_c, tot_l = (
        sum(s.commits_total for s in stats.values()),
        sum(s.lines_total for s in stats.values()),
    )
    all_f = set()
    for s in stats.values():
        all_f.update(s.files)
    tot_f = len(all_f)
    return {
        e: {
            "commits_team_pct": round((s.commits_total / tot_c) * 100, 2)
            if tot_c
            else 0.0,
            "lines_team_pct": round((s.lines_total / tot_l) * 100, 2) if tot_l else 0.0,
            "files_team_pct": round((len(s.files) / tot_f) * 100, 2) if tot_f else 0.0,
        }
        for e, s in stats.items()
    }


def build_rows(
    stats: Dict[str, AuthorStats], sat: Dict = None, ages: Dict = None
) -> List[Dict]:
    rel, space = calc_relative(stats), calc_space_scores(stats, sat)
    rows = []
    for email in sorted(stats.keys()):
        combined = {**rel.get(email, {}), **space.get(email, {})}
        if ages and email in ages:
            combined["ages_level"] = ages[email]
        rows.append(stats[email].to_dict(email, combined))
    return rows


def write_csv(rows: List[Dict], f) -> None:
    w = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
    w.writeheader()
    w.writerows(rows)


def print_report(data: List[Dict]) -> None:
    if not data:
        return print("No data to analyze")

    print("=" * 120 + "\nSPACE FRAMEWORK EVALUATION SUMMARY\n" + "=" * 120)
    print(f"Total Developers: {len(data)}\n\nOVERALL RANKINGS:\n" + "-" * 120)
    print(
        f"{'Rank':<6} {'Developer':<45} {'Overall':<8} {'S':<6} {'P':<6} {'A':<6} {'C':<6} {'E':<6} {'Level':<6}\n"
        + "-" * 120
    )

    for i, d in enumerate(
        sorted(data, key=lambda x: float(x["space_overall"]), reverse=True), 1
    ):
        name = (
            d["author_email"][:43] if len(d["author_email"]) > 43 else d["author_email"]
        )
        print(
            f"{i:<6} {name:<45} {float(d['space_overall']):<8.3f} {float(d['space_satisfaction']):<6.2f} "
            f"{float(d['space_performance']):<6.2f} {float(d['space_activity']):<6.2f} "
            f"{float(d['space_communication']):<6.2f} {float(d['space_efficiency']):<6.2f} {d.get('ages_level', ''):<6}"
        )

    dims = {
        "satisfaction": "Satisfaction",
        "performance": "Performance",
        "activity": "Activity",
        "communication": "Communication",
        "efficiency": "Efficiency",
    }

    for dim in dims:
        field = f"space_{dim}"
        vals = [float(r[field]) for r in data]
        avg, top = sum(vals) / len(vals), max(data, key=lambda x: float(x[field]))
        top_name = (
            top["author_email"][:40]
            if len(top["author_email"]) > 40
            else top["author_email"]
        )
        exc, good, dev = (
            len([v for v in vals if v >= 0.7]),
            len([v for v in vals if 0.5 <= v < 0.7]),
            len([v for v in vals if v < 0.5]),
        )
        print(f"\n{dims[dim].upper()} ANALYSIS:\n" + "=" * 100)
        print(
            f"Avg: {avg:.3f}  |  Range: [{min(vals):.3f},{max(vals):.3f}]  |  Top: {top_name} ({float(top[field]):.3f})"
        )
        print(
            f"Excellent (≥0.7): {exc} ({exc / len(data) * 100:.0f}%)  |  Good (0.5-0.7): {good} ({good / len(data) * 100:.0f}%)  |  Dev (<0.5): {dev} ({dev / len(data) * 100:.0f}%)"
        )

    print(
        "\n"
        + "=" * 100
        + "\nSPACE LEADERS\n"
        + "=" * 100
        + f"\n{'Dimension':<18} {'Leader':<50} {'Score':<8}\n"
        + "-" * 100
    )
    for name, key in [
        ("Satisfaction", "space_satisfaction"),
        ("Performance", "space_performance"),
        ("Activity", "space_activity"),
        ("Communication", "space_communication"),
        ("Efficiency", "space_efficiency"),
        ("Overall", "space_overall"),
    ]:
        top = max(data, key=lambda x: float(x[key]))
        leader = (
            top["author_email"][:48]
            if len(top["author_email"]) > 48
            else top["author_email"]
        )
        print(f"{name:<18} {leader:<50} {float(top[key]):<8.3f}")

    avg_s = {
        f"space_{d}": sum(float(r[f"space_{d}"]) for r in data) / len(data)
        for d in [
            "satisfaction",
            "performance",
            "activity",
            "communication",
            "efficiency",
            "overall",
        ]
    }
    print(
        "\n"
        + "=" * 100
        + "\nTEAM HEALTH\n"
        + "=" * 100
        + f"\nOverall: {avg_s['space_overall']:.3f}"
    )
    print(
        f"Satisfaction: {avg_s['space_satisfaction']:.3f} {'⚠️ (No survey)' if avg_s['space_satisfaction'] == 0 else ''}  |  "
        f"Performance: {avg_s['space_performance']:.3f}  |  Activity: {avg_s['space_activity']:.3f}  |  "
        f"Comm: {avg_s['space_communication']:.3f}  |  Efficiency: {avg_s['space_efficiency']:.3f}"
    )
    print("\n" + "=" * 100 + "\n✅ Analysis complete!\n" + "=" * 100)


def load_csv(file: str, process_fn) -> Dict:
    try:
        with open(file, "r", encoding="utf-8") as f:
            return process_fn(csv.DictReader(f))
    except FileNotFoundError:
        sys.stderr.write(f"Warning: File not found: {file}\n")
        return {}
    except Exception as e:
        sys.stderr.write(f"Error loading {file}: {e}\n")
        return {}


def load_survey(file: str) -> Dict[str, float]:
    def process(r):
        scores = {}
        for row in r:
            email = normalize_author(row.get("author_email", "").strip())
            if not email or "@" not in email:
                continue
            try:
                resp = [float(row[f"q{i}"]) for i in range(1, 15)]
                if not all(1 <= x <= 5 for x in resp):
                    continue
                resp = [6 - resp[i] if i in [3, 4] else resp[i] for i in range(14)]
                scores[email] = round(
                    sum(resp[0:3]) / 15 * 0.30
                    + sum(resp[3:7]) / 20 * 0.25
                    + sum(resp[7:11]) / 20 * 0.25
                    + sum(resp[11:14]) / 15 * 0.20,
                    3,
                )
            except:
                pass
        if scores:
            sys.stderr.write(
                f"Loaded {len(scores)} surveys (avg: {sum(scores.values()) / len(scores):.3f})\n"
            )
        return scores

    return load_csv(file, process)


def load_roster(file: str) -> Dict[str, str]:
    def process(r):
        levels = {}
        for row in r:
            name, level = (
                row.get("student_name", "").strip(),
                row.get("ages_level", "").strip().upper(),
            )
            if name and level in ["I", "II", "III", "IV"]:
                levels[name] = level
        sys.stderr.write(f"Loaded {len(levels)} students\n")
        return levels

    return load_csv(file, process)


def load_mapping(file: str) -> Dict[str, str]:
    def process(r):
        mapping = {}
        for row in r:
            name, email = (
                row.get("student_name", "").strip(),
                normalize_author(row.get("author_email", "").strip()),
            )
            if name and email and "@" in email:
                mapping[email] = name
        sys.stderr.write(f"Loaded {len(mapping)} mappings\n")
        return mapping

    return load_csv(file, process)


def aggregate(
    stats: Dict[str, AuthorStats], mapping: Dict[str, str]
) -> Dict[str, AuthorStats]:
    agg = {}
    for email, s in stats.items():
        name = mapping.get(email, email)
        if name not in agg:
            agg[name] = AuthorStats()
            agg[name].author_name = name
        a = agg[name]
        for f in [
            "commits_non_merge",
            "commits_merge",
            "commits_bugfix",
            "commits_coauthored",
            "reviews_given",
            "files_binary",
            "total_files_changed",
        ]:
            setattr(a, f, getattr(a, f) + getattr(s, f))
        for cat in FILE_CATEGORIES:
            for op in ["added", "deleted"]:
                a.lines_by_category[cat][op] += s.lines_by_category[cat][op]
            for op in ["added", "deleted", "modified"]:
                a.files_by_category[cat][op] += s.files_by_category[cat][op]
        a.days_active.update(s.days_active)
        a.files.update(s.files)
        if s.commits_first_date and (
            not a.commits_first_date or s.commits_first_date < a.commits_first_date
        ):
            a.commits_first_date = s.commits_first_date
        if s.commits_last_date and (
            not a.commits_last_date or s.commits_last_date > a.commits_last_date
        ):
            a.commits_last_date = s.commits_last_date
    sys.stderr.write(f"Aggregated {len(stats)} accounts into {len(agg)} records\n")
    return agg


is_valid_url = lambda u: any(
    re.match(p, u.strip(), re.IGNORECASE)
    for p in [
        r"^https?://github\.com/[\w\-]+/[\w\-\.]+(?:\.git)?$",
        r"^git@github\.com:[\w\-]+/[\w\-\.]+(?:\.git)?$",
        r"^https?://gitlab\.com/[\w\-]+/[\w\-\.]+(?:\.git)?$",
        r"^git@gitlab\.com:[\w\-]+/[\w\-\.]+(?:\.git)?$",
        r"^https?://[^\s]+\.git$",
        r"^git@[^\s]+\.git$",
    ]
)


def clone_repo(url: str, dir: str) -> None:
    sys.stderr.write(f"Cloning: {url}\n")
    try:
        subprocess.run(
            ["git", "clone", "--quiet", url, dir],
            check=True,
            capture_output=True,
            text=True,
        )
        sys.stderr.write(f"Cloned to: {dir}\n")
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Failed: {e.stderr}\n")
        raise


def main() -> None:
    p = argparse.ArgumentParser(
        description="Extract per-developer evaluation indicators from Git repository"
    )
    p.add_argument("--repo", help="GitHub/GitLab repository URL")
    p.add_argument(
        "--print", action="store_true", help="Save output and generate report"
    )
    p.add_argument("--output", default="output.csv", help="Output CSV filename")
    p.add_argument("--survey", help="Satisfaction survey CSV")
    p.add_argument("--roster", help="Student roster CSV")
    p.add_argument("--mapping", help="GitHub mapping CSV")
    args = p.parse_args()

    temp_dir, working_dir = None, None
    try:
        if args.repo:
            if not is_valid_url(args.repo):
                sys.stderr.write(f"Error: Invalid URL: {args.repo}\n")
                sys.exit(1)
            temp_dir = tempfile.mkdtemp(prefix="git-audit-")
            clone_repo(args.repo, temp_dir)
            working_dir = temp_dir

        stats = gather_stats(["--all"], False, working_dir)

        mapping = load_mapping(args.mapping) if args.mapping else {}
        roster = load_roster(args.roster) if args.roster else {}

        if mapping:
            stats = aggregate(stats, mapping)
            ages = roster if roster else None
        else:
            ages = None

        sat = None
        if args.survey:
            sat = load_survey(args.survey)
            if mapping:
                student_sat = {}
                for email, score in sat.items():
                    name = mapping.get(email, email)
                    student_sat[name] = (
                        (student_sat[name] + score) / 2
                        if name in student_sat
                        else score
                    )
                sat = student_sat

        rows = build_rows(stats, sat, ages)

        if args.print:
            sys.stderr.write(f"Writing: {args.output}\n")
            with open(args.output, "w", newline="") as f:
                write_csv(rows, f)
            sys.stderr.write(f"Saved: {args.output}\n\n")
            try:
                print_report(rows)
            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")
        else:
            write_csv(rows, sys.stdout)

    finally:
        if temp_dir and os.path.exists(temp_dir):
            sys.stderr.write(f"Cleanup: {temp_dir}\n")
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
