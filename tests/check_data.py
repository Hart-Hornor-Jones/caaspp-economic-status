"""
check_data.py -- internal-consistency checks for the data files and the page payload.

Standard library + pandas only. Run from anywhere:

    python tests/check_data.py

Exits 0 when every check passes, 1 otherwise, printing one line per failed assertion.
Every file is opened with encoding="utf-8"; nothing here depends on the platform's line endings.

What is checked
  * data/README.md describes every CSV in data/ (one "## name.csv" section each, no extra sections),
    its column table names exactly the columns in the file, and its stated row count is right
  * no duplicate keys in any file; years, grades, subjects and category labels are the documented ones
  * percentages lie in 0-100; achievement-level shares sum to 100 and "met or exceeded" equals
    level 3 + level 4, within the rounding CDE applied that year; tested <= enrolled; suppressed
    cells are blank as a block
  * the derived files (schools_lcff_classification.csv, school_aggregates_by_lcff.csv,
    odds_by_year.csv) are reproduced from their inputs and match exactly
  * the long NAEP file and NAEP's year-comparison file agree with each other (same estimates for
    the same cell), level shares, group shares and score-distribution bins sum to 100, percentiles
    are ordered, cumulative and discrete level codes agree
  * data.js (the payload behind index.html) equals the CSVs it was built from, value for value
"""
from __future__ import annotations

import json
import math
import re
import sys
import traceback
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

CAASPP_YEARS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]
NO_2021 = [y for y in CAASPP_YEARS if y != 2021]
NAEP_YEARS = [2015, 2017, 2019, 2022, 2024]
GRADES = [3, 4, 5, 6, 7, 8, 11]
SUBJECTS = ["ela", "math"]
LEVELS = ["pct_level4_exceeded", "pct_level3_met", "pct_level2_nearly_met", "pct_level1_not_met"]
PCT_COLS = LEVELS + ["pct_met_or_exceeded"]
ECON = ["All students", "Economically disadvantaged", "Not economically disadvantaged"]
WHOLE_YEARS = {2015, 2016}            # CDE published whole-number percentages in these years

FAILURES: list[str] = []


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)


def read(name, **kw):
    kw.setdefault("encoding", "utf-8")
    kw.setdefault("dtype", {"cds_code": str})
    return pd.read_csv(DATA / name, **kw)


def level_tolerance(years):
    """Max deviation of a sum of four rounded shares from 100: 4 x half-unit of the rounding."""
    return pd.Series([2.0 if y in WHOLE_YEARS else 0.05 for y in years], index=years.index)


def met_tolerance(years):
    return pd.Series([1.0 if y in WHOLE_YEARS else 0.03 for y in years], index=years.index)


def in_range(df, cols, lo=0, hi=100, label=""):
    for c in cols:
        v = df[c].dropna()
        check(((v >= lo) & (v <= hi)).all(), f"{label}: {c} outside {lo}-{hi}")


def level_arithmetic(df, label, require_all=False):
    """Level shares sum to 100 and met = L3 + L4 where the shares are published."""
    have = df.dropna(subset=LEVELS)
    if require_all:
        check(len(have) == len(df), f"{label}: level shares missing in {len(df) - len(have)} rows")
    dev = (have[LEVELS].sum(axis=1) - 100).abs()
    check((dev <= level_tolerance(have["year"])).all(), f"{label}: level shares do not sum to 100 within rounding "
          f"(max deviation {dev.max():.2f})")
    met = (have["pct_level4_exceeded"] + have["pct_level3_met"] - have["pct_met_or_exceeded"]).abs()
    check((met <= met_tolerance(have["year"])).all(), f"{label}: met-or-exceeded != level 3 + level 4 within rounding "
          f"(max deviation {met.max():.2f})")


# ---------------------------------------------------------------------------------------------
# README as data dictionary
# ---------------------------------------------------------------------------------------------
def readme_sections():
    text = (DATA / "README.md").read_text(encoding="utf-8")
    parts = re.split(r"^## (\S+)\s*(?:\(derived\))?\s*$", text, flags=re.M)
    sections = {}
    for i in range(1, len(parts), 2):
        sections[parts[i]] = parts[i + 1]
    return sections


def check_readme():
    sections = readme_sections()
    csvs = sorted(p.name for p in DATA.glob("*.csv"))
    check(set(sections) >= set(csvs), f"README: no section for {sorted(set(csvs) - set(sections))}")
    check(set(sections) <= set(csvs) | {"data.js"}, f"README: sections for files that do not exist: {sorted(set(sections) - set(csvs) - {'data.js'})}")
    for name in csvs:
        body = sections.get(name)
        if body is None:
            continue
        cols = []
        for line in body.splitlines():
            if line.startswith("| `"):
                cols += re.findall(r"`([A-Za-z0-9_]+)`", line.split("|")[1])
        actual = list(read(name, nrows=5).columns)
        check(cols == actual, f"README section {name}: column table lists {cols} but the file has {actual}")
        m = re.search(r"\b([\d,]+) rows\b", body)
        check(m is not None, f"README section {name}: no row count stated")
        if m:
            stated = int(m.group(1).replace(",", ""))
            n = len(read(name, usecols=[0]))        # records, not lines: some quoted labels contain a newline
            check(stated == n, f"README section {name}: says {stated:,} rows, file has {n:,}")
    # the two README files and the build README name the same derived files
    top = (REPO / "README.md").read_text(encoding="utf-8")
    build = (REPO / "build" / "README.md").read_text(encoding="utf-8")
    for derived in ["schools_lcff_classification.csv", "school_aggregates_by_lcff.csv", "odds_by_year.csv"]:
        check(derived in top, f"README.md does not name derived file {derived}")
        check(derived in build, f"build/README.md does not name derived file {derived}")
        check("(derived)" in re.search(rf"^## {re.escape(derived)}.*$", (DATA / "README.md").read_text(encoding='utf-8'), flags=re.M).group(0),
              f"data/README.md: {derived} is not marked (derived)")


# ---------------------------------------------------------------------------------------------
# source files
# ---------------------------------------------------------------------------------------------
def check_statewide_all_groups():
    s = read("statewide_all_groups.csv")
    L = "statewide_all_groups"
    key = ["year", "subject", "grade", "group_code"]
    check(not s.duplicated(key).any(), f"{L}: duplicate keys")
    check(sorted(s.year.unique()) == CAASPP_YEARS, f"{L}: years {sorted(s.year.unique())}")
    check(sorted(s.grade.unique()) == GRADES, f"{L}: grades {sorted(s.grade.unique())}")
    check(sorted(s.subject.unique()) == SUBJECTS, f"{L}: subjects {sorted(s.subject.unique())}")
    check((s.groupby("group_code").group_name.nunique() == 1).all(), f"{L}: a group_code carries more than one group_name")
    check((s.groupby("group_code").group_category.nunique() == 1).all(), f"{L}: a group_code carries more than one group_category")
    check((s.tested <= s.enrolled).all(), f"{L}: tested > enrolled")
    check((s.tested >= 11).all(), f"{L}: tested < 11 (suppressed cells should be absent)")
    check(s[PCT_COLS + ["mean_scale_score", "enrolled", "tested"]].notna().all().all(), f"{L}: blank numeric cells")
    in_range(s, PCT_COLS, label=L)
    level_arithmetic(s, L, require_all=True)
    whole = s[s.year.isin(WHOLE_YEARS)][PCT_COLS]
    check((whole % 1 == 0).all().all(), f"{L}: 2015-2016 percentages are not whole numbers")
    # every year has the three groups the page uses, in every subject x grade
    core = s[s.group_code.isin([1, 31, 111])].groupby(["year", "subject", "grade"]).group_code.nunique()
    check(len(core) == len(CAASPP_YEARS) * 2 * 7 and (core == 3).all(), f"{L}: groups 1/31/111 missing for some year x subject x grade")
    return s


def check_statewide_economic_status(s):
    e = read("statewide_economic_status.csv")
    L = "statewide_economic_status"
    key = ["year", "subject", "grade", "economic_status", "ethnicity"]
    check(not e.duplicated(key).any(), f"{L}: duplicate keys")
    check(sorted(e.year.unique()) == NO_2021, f"{L}: years {sorted(e.year.unique())}")
    check(sorted(e.grade.unique()) == GRADES, f"{L}: grades")
    check(set(e.economic_status) == set(ECON[1:]), f"{L}: economic_status values {set(e.economic_status)}")
    check(e.notna().all().all(), f"{L}: blank cells")
    in_range(e, ["pct_met_or_exceeded"], label=L)
    check((e.sd_scale_score > 0).all(), f"{L}: non-positive standard deviation")
    check(e.source_workbook.str.match(r"^(ela|math)econdis(all|eth)\d{4}\.xlsx$").all(), f"{L}: unexpected source_workbook name")
    check((e.source_workbook.str[:3].str.rstrip("h") == e.subject.str[:3].str.rstrip("h")).all() and
          (e.source_workbook.str.extract(r"(\d{4})")[0].astype(int) == e.year).all(), f"{L}: source_workbook disagrees with subject/year")
    check(((e.ethnicity == "All") == e.source_workbook.str.contains("all")).all(), f"{L}: ethnicity 'All' rows do not come from the 'all' workbooks")
    # the two-group totals agree with groups 31 / 111 of the research files within the workbooks' rounding
    m = s[s.group_code.isin([31, 111])].copy()
    m["economic_status"] = m.group_code.map({31: ECON[1], 111: ECON[2]})
    j = e[e.ethnicity == "All"].merge(m, on=["year", "subject", "grade", "economic_status"], suffixes=("_wb", "_rf"))
    check(len(j) == len(e[e.ethnicity == "All"]), f"{L}: 'All' rows without a matching statewide_all_groups row")
    check(((j.mean_scale_score_wb - j.mean_scale_score_rf).abs() <= 0.5).all(), f"{L}: 'All' means differ from statewide_all_groups by more than 0.5")
    check(((j.pct_met_or_exceeded_wb - j.pct_met_or_exceeded_rf).abs() <= 0.5).all(), f"{L}: 'All' pct_met differs from statewide_all_groups by more than 0.5")
    check((j.tested_wb <= j.tested_rf).all() and (j.tested_wb >= 0.95 * j.tested_rf).all(), f"{L}: 'All' tested counts are not within 5% below the research-file counts")


def check_schools():
    d = read("schools_by_economic_status.csv")
    L = "schools_by_economic_status"
    key = ["cds_code", "year", "subject", "economic_status"]
    check(not d.duplicated(key).any(), f"{L}: duplicate keys")
    check(d.cds_code.str.fullmatch(r"\d{14}").all(), f"{L}: cds_code is not 14 digits")
    check((d.grade == 11).all(), f"{L}: grade != 11")
    check(sorted(d.year.unique()) == CAASPP_YEARS, f"{L}: years")
    check(sorted(d.subject.unique()) == SUBJECTS, f"{L}: subjects")
    check(set(d.economic_status) == set(ECON), f"{L}: economic_status values")
    check(set(d.school_type) == {"school", "direct-funded charter", "locally funded charter"}, f"{L}: school_type values")
    check(d[["school", "district", "county", "enrolled", "tested"]].notna().all().all(), f"{L}: blank name or count")
    check((d.tested <= d.enrolled).all(), f"{L}: tested > enrolled")
    scored = d.mean_scale_score.notna()
    for c in PCT_COLS:
        check((d[c].notna() == scored).all(), f"{L}: {c} blank/present does not match mean_scale_score (suppression should blank the whole cell)")
    check((d.loc[scored, "tested"] >= 11).all(), f"{L}: published cell with fewer than 11 tested")
    in_range(d, PCT_COLS, label=L)
    level_arithmetic(d, L)
    whole = d[d.year.isin(WHOLE_YEARS)][PCT_COLS].dropna()
    check((whole % 1 == 0).all().all(), f"{L}: 2015-2016 percentages are not whole numbers")
    return d


def check_upp():
    u = read("schools_upp_lcff.csv")
    L = "schools_upp_lcff"
    check(not u.duplicated(["cds_code", "school_year"]).any(), f"{L}: duplicate keys")
    check(u.cds_code.str.fullmatch(r"\d{14}").all(), f"{L}: cds_code is not 14 digits")
    yrs = [f"{y}-{y + 1}" for y in range(2016, 2026)]
    check(sorted(u.school_year.unique()) == yrs, f"{L}: school_year values {sorted(u.school_year.unique())}")
    check(u.notna().all().all(), f"{L}: blank cells")
    in_range(u, ["upp_pct"], label=L)
    check((u.enrollment_9_12 >= 0).all(), f"{L}: negative enrollment")
    check(set(u.cde_lcff_plus_flag) == {"Y", "N"}, f"{L}: flag values")
    return u


def check_classification(u):
    c = read("schools_lcff_classification.csv")
    L = "schools_lcff_classification"
    check(not c.duplicated("cds_code").any(), f"{L}: duplicate cds_code")
    check(set(c.lcff_plus_fixed) == {"LCFF+", "Not LCFF+"}, f"{L}: label values")
    pre = u[u.school_year.isin(["2016-2017", "2017-2018", "2018-2019", "2019-2020"])]
    r = pre.groupby("cds_code")["upp_pct"].agg(["mean", "size"]).reset_index()
    r.columns = ["cds_code", "upp_pre2020_mean", "years_of_upp_pre2020"]
    r["upp_pre2020_mean"] = r["upp_pre2020_mean"].round(2)
    r["lcff_plus_fixed"] = (r["upp_pre2020_mean"] > 75.0).map({True: "LCFF+", False: "Not LCFF+"})
    r = r.sort_values("cds_code").reset_index(drop=True)
    same = len(r) == len(c) and (r.cds_code.values == c.cds_code.values).all() and \
        (r.upp_pre2020_mean.values == c.upp_pre2020_mean.values).all() and \
        (r.years_of_upp_pre2020.values == c.years_of_upp_pre2020.values).all() and \
        (r.lcff_plus_fixed.values == c.lcff_plus_fixed.values).all()
    check(same, f"{L}: does not match a recomputation from schools_upp_lcff.csv")
    return c


def recompute_aggregates(d, c):
    out = []
    a = d[d.economic_status == "All students"].merge(c[["cds_code", "lcff_plus_fixed"]], on="cds_code")
    a = a.dropna(subset=["mean_scale_score"])
    vals = ["mean_scale_score", "pct_level4_exceeded", "pct_level3_met", "pct_met_or_exceeded", "pct_level2_nearly_met", "pct_level1_not_met"]
    for subj, g in a.groupby("subject"):
        every = g[g.year.isin(NO_2021)].groupby("cds_code").year.nunique()
        fixed = set(every[every == len(NO_2021)].index)
        panels = (("all_schools_reporting", g), ("same_schools_every_year", g[g.cds_code.isin(fixed) & g.year.isin(NO_2021)]))
        for panel, gg in panels:
            for (year, lab), h in gg.groupby(["year", "lcff_plus_fixed"]):
                w = h.tested.astype(float)
                for weighting in ("students", "schools"):
                    rec = {"subject": subj, "grade": 11, "year": int(year), "school_group": lab, "weighting": weighting,
                           "school_set": panel, "schools": int(len(h)), "tested": int(w.sum())}
                    for col in vals:
                        v = h[col].astype(float)
                        rec[col] = round(float((v * w).sum() / w.sum()), 2) if weighting == "students" else round(float(v.mean()), 2)
                    out.append(rec)
    return pd.DataFrame(out)


def check_aggregates(d, c):
    a = read("school_aggregates_by_lcff.csv")
    L = "school_aggregates_by_lcff"
    key = ["subject", "year", "school_group", "weighting", "school_set"]
    check(not a.duplicated(key).any(), f"{L}: duplicate keys")
    check(a.notna().all().all(), f"{L}: blank cells")
    check((a.grade == 11).all(), f"{L}: grade != 11")
    check(sorted(a[a.school_set == "all_schools_reporting"].year.unique()) == CAASPP_YEARS, f"{L}: all_schools_reporting years")
    check(sorted(a[a.school_set == "same_schools_every_year"].year.unique()) == NO_2021, f"{L}: same_schools_every_year years")
    check(set(a.school_group) == {"LCFF+", "Not LCFF+"} and set(a.weighting) == {"students", "schools"}, f"{L}: labels")
    check(len(a) == 2 * 2 * 2 * (len(CAASPP_YEARS) + len(NO_2021)), f"{L}: expected {2*2*2*(len(CAASPP_YEARS)+len(NO_2021))} rows, found {len(a)}")
    in_range(a, PCT_COLS, label=L)
    dev = (a[LEVELS].sum(axis=1) - 100).abs()
    check((dev <= 0.5).all(), f"{L}: level shares do not sum to 100 within rounding (max {dev.max():.2f})")
    fixed_n = a[a.school_set == "same_schools_every_year"].groupby(["subject", "school_group", "weighting"]).schools.nunique()
    check((fixed_n == 1).all(), f"{L}: the same-schools panel does not hold a constant number of schools")
    r = recompute_aggregates(d, c)
    m = a.merge(r, on=key, suffixes=("", "_r"))
    check(len(m) == len(a) == len(r), f"{L}: recomputation yields a different set of rows")
    for col in ["schools", "tested", "mean_scale_score"] + PCT_COLS:
        check(((m[col] - m[col + "_r"]).abs() < 1e-9).all(), f"{L}: {col} differs from a recomputation from the school file")
    return a


def check_percentiles():
    p = read("scale_score_percentiles.csv")
    L = "scale_score_percentiles"
    key = ["year", "subject", "grade", "percentile"]
    check(not p.duplicated(key).any(), f"{L}: duplicate keys")
    pcts = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]
    check(sorted(p.percentile.unique()) == pcts, f"{L}: percentiles {sorted(p.percentile.unique())}")
    check(sorted(p.year.unique()) == NO_2021, f"{L}: years")
    check(sorted(p.grade.unique()) == GRADES and sorted(p.subject.unique()) == SUBJECTS, f"{L}: grades/subjects")
    check(len(p) == len(NO_2021) * 2 * 7 * len(pcts), f"{L}: incomplete grid ({len(p)} rows)")
    mono = p.sort_values(key).groupby(["year", "subject", "grade"]).scale_score.apply(lambda x: (x.diff().dropna() >= 0).all())
    check(mono.all(), f"{L}: scale score not non-decreasing in percentile")
    check(p.scale_score.between(2000, 3000).all(), f"{L}: scale score outside the Smarter Balanced range")
    return p


def check_growth():
    t = read("same_students_growth.csv")
    L = "same_students_growth"
    key = ["report_year", "table_title", "subject", "group", "year", "grade"]
    check(not t.duplicated(key).any(), f"{L}: duplicate keys")
    check(sorted(t.report_year.unique()) == [2016, 2017, 2019, 2021, 2022, 2023, 2024, 2025], f"{L}: report years")
    check(sorted(t.grade.unique()) == [3, 4, 5, 6, 7, 8], f"{L}: grades")
    check(sorted(t.subject.unique()) == SUBJECTS, f"{L}: subjects")
    check(set(t.year.unique()) <= set(CAASPP_YEARS), f"{L}: years")
    check((t.year <= t.report_year).all() and (t.year >= t.report_year - 3).all(), f"{L}: row year more than three years before its report")
    check(t.table_title.str.startswith("Table 10.").all(), f"{L}: table_title not an appendix-10 table")
    check((t.students >= 0).all(), f"{L}: negative student count")
    in_range(t, PCT_COLS, label=L)
    present = t.dropna(subset=LEVELS)
    dev = (present[LEVELS].sum(axis=1) - 100).abs()
    check((dev <= 2.0).all(), f"{L}: level shares do not sum to 100 within whole-number rounding (max {dev.max():.2f})")
    met = (present.pct_level4_exceeded + present.pct_level3_met - present.pct_met_or_exceeded).abs()
    check((met <= 1.0).all(), f"{L}: met-or-exceeded != level 3 + level 4 within rounding")
    # blank statistics only where the table has no students or where the table carries no such column
    nostud = t[t.students == 0]
    check(nostud[["mean_scale_score", "sd_scale_score"] + PCT_COLS].isna().all().all(), f"{L}: statistics given for a group of 0 students")
    check(t[t.students >= 11].mean_scale_score.notna().all(), f"{L}: blank mean for a group of 11 or more students")
    check(t[t.mean_scale_score.isna()].students.lt(11).all(), f"{L}: blank mean outside groups of fewer than 11 students")
    claims = t[t.table_title.str.contains("Claim")]
    check((claims.report_year == 2019).all() and claims[PCT_COLS].isna().all().all(), f"{L}: claim tables outside the 2019 report or with achievement-level shares")
    check(set(t[t.report_year.isin([2021, 2022])].group) <= {"All Students", "Male", "Female", "American Indian or Alaska Native", "Asian",
          "Native Hawaiian or Other Pacific Islander", "Filipino", "Hispanic or Latino", "Black or African American", "White", "Two or more races"},
          f"{L}: 2021/2022 reports should carry ethnicity and gender only")
    return t


def check_naep():
    n = read("naep_ca_grade8_math_by_ses.csv")
    L = "naep_ca_grade8_math_by_ses"
    key = ["year", "ses_variable_code", "ses_level_code", "statistic_code"]
    check(not n.duplicated(key).any(), f"{L}: duplicate keys")
    check(sorted(n.year.unique()) == NAEP_YEARS, f"{L}: years")
    check((n.subject == "Mathematics").all() and (n.grade == 8).all() and (n.jurisdiction == "California").all(), f"{L}: subject/grade/jurisdiction")
    groups = n.groupby(["ses_variable_code", "ses_level_code"]).ses_level.nunique()
    check((groups == 1).all(), f"{L}: a level code carries more than one label")
    expected = {"TOTAL": 1, "ECONDIS": 3, "PARED": 5, "SCHOOL_FRPL_PCT": 9}
    found = n.groupby("ses_variable_code").ses_level_code.nunique().to_dict()
    check(found == expected, f"{L}: groups per variable {found}, expected {expected}")
    per = n.groupby(["year", "ses_variable_code", "ses_level_code"]).statistic_code.nunique()
    check(len(per) == len(NAEP_YEARS) * 18 and (per == 65).all(), f"{L}: not 65 statistics for each of the 90 year x group cells")
    check(((n.estimate.isna()) == (n.is_displayable == 0)).all(), f"{L}: estimate blank does not coincide with is_displayable = 0")
    check(((n.estimate.isna()) == (n.standard_error.isna())).all() and ((n.estimate.isna()) == (n.cell_n.isna())).all(), f"{L}: blanks not aligned across estimate / standard_error / cell_n")
    check(n[n.standard_error.notna()].standard_error.isin([-1.0]).sum() + (n.standard_error >= 0).sum() == n.standard_error.notna().sum(),
          f"{L}: standard_error other than >= 0 or the -1 'not applicable' marker")
    check((n[(n.standard_error == -1)].error_labels.fillna("").str.contains("standard error not applicable")).all(), f"{L}: standard_error = -1 without the 'not applicable' label")
    check((n[n.statistic_code != "RP:RP"].groupby(["year", "ses_variable_code", "ses_level_code"]).cell_n.nunique() <= 1).all(), f"{L}: cell_n varies within a year x group")
    tot = n[(n.ses_variable_code == "TOTAL") & (n.statistic_code == "MN:MN")].set_index("year").cell_n
    rp = n[(n.statistic_code == "RP:RP") & n.cell_n.notna()]
    check((rp.groupby(["year", "ses_variable_code"]).cell_n.nunique() == 1).all() and (rp.cell_n <= tot.reindex(rp.year).values).all(),
          f"{L}: cell_n of the group-share statistic is not one denominator per year x variable, within the whole sample")
    pct = n[n.unit == "percent"].estimate.dropna()
    check(((pct >= 0) & (pct <= 100)).all(), f"{L}: percent outside 0-100")
    sc = n[n.unit == "scale score"].estimate.dropna()
    check(((sc >= 0) & (sc <= 500)).all(), f"{L}: scale score outside 0-500")
    cols = ["year", "ses_variable_code", "ses_level_code"]
    pv = n.pivot_table(index=cols, columns="statistic_code", values="estimate")
    disc = pv[["ALC:BB", "ALD:BA", "ALD:PR", "ALD:AD"]].dropna()
    check(((disc.sum(axis=1) - 100).abs() < 1e-6).all(), f"{L}: discrete achievement-level shares do not sum to 100")
    cum = pv[["ALC:BB", "ALC:AB"]].dropna()
    check(((cum.sum(axis=1) - 100).abs() < 1e-6).all(), f"{L}: below Basic + at or above Basic != 100")
    ab = pv[["ALC:AB", "ALC:AP", "ALC:AD"]].dropna()
    check(((ab["ALC:AB"] >= ab["ALC:AP"]) & (ab["ALC:AP"] >= ab["ALC:AD"])).all(), f"{L}: cumulative levels not nested")
    ad = pv[["ALC:AD", "ALD:AD"]]
    check(((ad["ALC:AD"] - ad["ALD:AD"]).abs().fillna(0) < 1e-9).all() and (ad["ALC:AD"].isna() == ad["ALD:AD"].isna()).all(), f"{L}: ALC:AD and ALD:AD differ")
    pc = pv[["PC:P1", "PC:P2", "PC:P5", "PC:P7", "PC:P9"]].dropna()
    check(((pc["PC:P1"] <= pc["PC:P2"]) & (pc["PC:P2"] <= pc["PC:P5"]) & (pc["PC:P5"] <= pc["PC:P7"]) & (pc["PC:P7"] <= pc["PC:P9"])).all(), f"{L}: percentiles not ordered")
    dist = n[n.statistic_family == "score distribution"].groupby(cols).estimate.agg(["sum", "count"])
    full = dist[dist["count"] == 50]
    check(((full["sum"] - 100).abs() < 1e-6).all() and (dist["count"].isin([0, 50])).all(), f"{L}: score-distribution bins do not sum to 100")
    lo = n[n.statistic_family == "score distribution"]
    check(((lo.score_interval_high - lo.score_interval_low) == 9).all() and lo.score_interval_low.between(0, 490).all(), f"{L}: score bins are not ten points wide")
    share = n[n.statistic_code == "RP:RP"].groupby(["year", "ses_variable_code"]).estimate.sum()
    check(((share - 100).abs() <= 0.25).all(), f"{L}: group shares within a variable do not sum to 100 (max off by {(share - 100).abs().max():.2f})")
    frpl = n[n.ses_variable_code == "SCHOOL_FRPL_PCT"].groupby("api_variable_code").year.apply(lambda y: sorted(set(y))).to_dict()
    check(frpl == {"C051601": [2015, 2017], "C051651": [2019, 2022, 2024]}, f"{L}: school-lunch variable codes by year {frpl}")
    check(n.source_url.str.startswith("https://www.nationsreportcard.gov/DataService/GetAdhocData.aspx?type=data").all(), f"{L}: source_url is not a data request")
    return n


def check_naep_comparisons(n):
    c = read("naep_ca_grade8_math_year_comparisons.csv")
    L = "naep_ca_grade8_math_year_comparisons"
    key = ["ses_variable_code", "ses_level_code", "statistic_code", "baseline_year", "followup_year"]
    check(not c.duplicated(key).any(), f"{L}: duplicate keys")
    check((c.baseline_year < c.followup_year).all(), f"{L}: baseline not before follow-up")
    check(set(c.baseline_year) | set(c.followup_year) <= set(NAEP_YEARS), f"{L}: years outside the assessment years")
    stats = sorted(c.statistic_code.unique())
    check(stats == ["ALC:AB", "ALC:AD", "ALC:AP", "ALC:BB", "ALD:AD", "ALD:BA", "ALD:PR", "MN:MN", "PC:P1", "PC:P2", "PC:P5", "PC:P7", "PC:P9"], f"{L}: statistics {stats}")
    # every pair of years available for a variable code, and no others
    import itertools
    yrs = n.groupby(["ses_variable_code", "api_variable_code"]).year.apply(lambda y: sorted(set(y))).to_dict()
    for (var, api), ys in yrs.items():
        sub = c[(c.ses_variable_code == var) & (c.api_variable_code == api)]
        have = set(zip(sub.baseline_year, sub.followup_year))
        check(have == set(itertools.combinations(ys, 2)), f"{L}: year pairs for {var}/{api} are {sorted(have)}")
        per = sub.groupby(["ses_level_code", "statistic_code"]).size()
        check((per == len(list(itertools.combinations(ys, 2)))).all(), f"{L}: a {var} group x statistic lacks some year pair")
    ch = c.followup_estimate - c.baseline_estimate - c.change_followup_minus_baseline
    check((ch.abs().fillna(0) < 1e-9).all(), f"{L}: change != follow-up minus baseline")
    check((c.change_followup_minus_baseline.isna() == (c.baseline_estimate.isna() | c.followup_estimate.isna())).all(), f"{L}: change blank pattern")
    est = n.set_index(["year", "ses_variable_code", "ses_level_code", "statistic_code"]).estimate.to_dict()
    b = c.apply(lambda r: est.get((r.baseline_year, r.ses_variable_code, r.ses_level_code, r.statistic_code), math.nan), axis=1)
    f = c.apply(lambda r: est.get((r.followup_year, r.ses_variable_code, r.ses_level_code, r.statistic_code), math.nan), axis=1)
    check(((b - c.baseline_estimate).abs().fillna(0) < 1e-9).all() and (b.isna() == c.baseline_estimate.isna()).all(), f"{L}: baseline estimates differ from naep_ca_grade8_math_by_ses.csv")
    check(((f - c.followup_estimate).abs().fillna(0) < 1e-9).all() and (f.isna() == c.followup_estimate.isna()).all(), f"{L}: follow-up estimates differ from naep_ca_grade8_math_by_ses.csv")
    check((c.official_significance.isna() == (c.is_comparison_displayable == 0)).all(), f"{L}: official_significance blank does not coincide with is_comparison_displayable = 0")
    check(set(c.official_significance.dropna()) == {"follow-up higher", "follow-up lower", "no statistically significant difference"}, f"{L}: significance labels")
    sign = c.change_followup_minus_baseline
    check(((c.official_significance == "follow-up higher") <= (sign > 0)).all() and ((c.official_significance == "follow-up lower") <= (sign < 0)).all(), f"{L}: significance verdict contradicts the sign of the change")
    api = {"follow-up higher": "LOWER", "follow-up lower": "HIGHER", "no statistically significant difference": "EQUAL"}
    ok = c.official_significance.map(api).fillna("NA") == c.api_significance_focal_vs_target.fillna("NA")
    check(ok.all(), f"{L}: api_significance_focal_vs_target is not the baseline-vs-follow-up mirror of official_significance")
    check(c.source_url.str.contains("type=sigacrossyear").all(), f"{L}: source_url is not a significance request")
    return c


def check_odds(s, a, n):
    o = read("odds_by_year.csv")
    L = "odds_by_year"
    key = ["test", "comparison", "year", "level"]
    check(not o.duplicated(key).any(), f"{L}: duplicate keys")
    in_range(o, ["share_disadvantaged_pct", "share_not_disadvantaged_pct"], label=L)
    for share, odds in [("share_disadvantaged_pct", "odds_disadvantaged"), ("share_not_disadvantaged_pct", "odds_not_disadvantaged")]:
        exp = (o[share] / (100 - o[share])).round(4)
        check(((exp - o[odds]).abs().fillna(0) < 1e-9).all() and (o[odds].isna() == ~o[share].between(0, 100, inclusive="neither")).all(), f"{L}: {odds} != p/(1-p)")
    ratio = (o.odds_not_disadvantaged / o.odds_disadvantaged).round(4)
    check(((ratio - o.odds_ratio_not_over_disadvantaged).abs().fillna(0) < 1e-9).all(), f"{L}: odds ratio != not / disadvantaged")

    def odds(v):
        return None if v is None or pd.isna(v) or v <= 0 or v >= 100 else round(float(v) / (100 - float(v)), 4)

    rows = []
    LV = [("pct_level4_exceeded", "standard exceeded (level 4)"), ("pct_met_or_exceeded", "standard met or exceeded (levels 3-4)"),
          ("pct_level3_met", "standard met, not exceeded (level 3)"), ("pct_level2_nearly_met", "standard nearly met (level 2)"),
          ("pct_level1_not_met", "standard not met (level 1)")]
    sw = s[(s.subject == "math") & (s.grade == 11) & s.group_code.isin([31, 111])]
    for year, g in sw.groupby("year"):
        x, y = g[g.group_code == 31].iloc[0], g[g.group_code == 111].iloc[0]
        for col, lab in LV:
            rows.append(("CAASPP grade 11 mathematics", "all California students", int(year), lab, x[col], y[col]))
    la = a[(a.subject == "math") & (a.weighting == "students") & (a.school_set == "all_schools_reporting")]
    for year, g in la.groupby("year"):
        x, y = g[g.school_group == "LCFF+"].iloc[0], g[g.school_group == "Not LCFF+"].iloc[0]
        for col, lab in LV:
            rows.append(("CAASPP grade 11 mathematics", "LCFF+ vs. other high schools (student-weighted, all reporting)", int(year), lab, x[col], y[col]))
    NLV = [("ALC:AD", "at NAEP Advanced"), ("ALC:AP", "at or above NAEP Proficient"), ("ALC:AB", "at or above NAEP Basic"),
           ("ALD:PR", "at NAEP Proficient, not Advanced"), ("ALD:BA", "at NAEP Basic, not Proficient"), ("ALC:BB", "below NAEP Basic")]
    ne = n[(n.ses_variable_code == "ECONDIS") & (n.is_displayable == 1)].set_index(["year", "ses_level_code", "statistic_code"]).estimate
    for year in NAEP_YEARS:
        for code, lab in NLV:
            pa, pb = ne.get((year, 1, code), math.nan), ne.get((year, 2, code), math.nan)
            rows.append(("NAEP grade 8 mathematics", "all California students (NAEP sample)", year, lab, round(pa, 2), round(pb, 2)))
    r = pd.DataFrame(rows, columns=key + ["share_disadvantaged_pct", "share_not_disadvantaged_pct"])
    r["odds_disadvantaged"] = r.share_disadvantaged_pct.map(odds)
    r["odds_not_disadvantaged"] = r.share_not_disadvantaged_pct.map(odds)
    r["odds_ratio_not_over_disadvantaged"] = [round(b / x, 4) if x and b else None for x, b in zip(r.odds_disadvantaged, r.odds_not_disadvantaged)]
    m = o.merge(r, on=key, suffixes=("", "_r"))
    check(len(m) == len(o) == len(r), f"{L}: recomputation yields a different set of rows ({len(o)} vs {len(r)})")
    for col in ["share_disadvantaged_pct", "share_not_disadvantaged_pct", "odds_disadvantaged", "odds_not_disadvantaged", "odds_ratio_not_over_disadvantaged"]:
        check(((m[col] - m[col + "_r"]).abs().fillna(0) < 1e-9).all() and (m[col].isna() == m[col + "_r"].isna()).all(), f"{L}: {col} differs from a recomputation")
    return o


# ---------------------------------------------------------------------------------------------
# data.js (the payload behind index.html) against the CSVs
# ---------------------------------------------------------------------------------------------
def load_payload():
    js = (REPO / "data.js").read_text(encoding="utf-8")
    prefix = "window.CAASPP_ECON="
    check(js.startswith(prefix) and js.rstrip().endswith(";"), "data.js: not of the form window.CAASPP_ECON=...;")
    return json.loads(js[len(prefix):].rstrip().rstrip(";"))


def r1(v):
    return None if pd.isna(v) else round(float(v), 1)


def rows_by_year(g, vals):
    out = {}
    for _, row in g.iterrows():
        if pd.isna(row["mean_scale_score"]):
            continue
        out[str(int(row["year"]))] = [int(row["tested"])] + [r1(row[c]) for c in vals[1:]]
    return out


def check_payload(s, d, c, a, p, n):
    D = load_payload()
    L = "data.js"
    VAL = ["tested", "mean_scale_score", "pct_level4_exceeded", "pct_level3_met", "pct_met_or_exceeded", "pct_level2_nearly_met", "pct_level1_not_met"]
    check(set(D) == {"generated", "subject", "grade", "standard", "years", "cols", "lcff_cut", "pct", "state", "agg", "schools", "naep"}, f"{L}: top-level keys {sorted(D)}")
    check(D["subject"] == "math" and D["grade"] == 11 and D["standard"] == 2628 and D["lcff_cut"] == 75.0, f"{L}: subject/grade/standard/lcff_cut")
    check(D["years"] == NO_2021, f"{L}: years {D['years']}")
    check(D["cols"] == ["tested", "mean", "L4", "L3", "met", "L2", "L1"], f"{L}: cols")
    check(re.fullmatch(r"\d{4}-\d{2}-\d{2}", D["generated"]) is not None, f"{L}: generated is not a date")
    # percentile tables
    pm = p[(p.subject == "math") & (p.grade == 11)].sort_values(["year", "percentile"])
    exp = {str(y): {"p": g.percentile.tolist(), "s": g.scale_score.tolist()} for y, g in pm.groupby("year")}
    check(D["pct"] == exp, f"{L}: pct differs from scale_score_percentiles.csv")
    # statewide
    sm = s[(s.subject == "math") & (s.grade == 11)]
    exp = {k: rows_by_year(sm[sm.group_code == code], VAL) for code, k in [(1, "ALL"), (31, "SED"), (111, "NOT")]}
    check(D["state"] == exp, f"{L}: state differs from statewide_all_groups.csv")
    # LCFF+ aggregates
    am = a[a.subject == "math"]
    exp = {}
    for (panel, weighting), g in am.groupby(["school_set", "weighting"]):
        k = f"{weighting}|{'fixed' if panel == 'same_schools_every_year' else 'all'}"
        exp[k] = {}
        for lab, h in g.groupby("school_group"):
            exp[k]["LCFF" if lab == "LCFF+" else "NON"] = {str(int(r.year)): [int(r.schools), int(r.tested)] + [round(float(r[col]), 2) for col in VAL[1:]] for _, r in h.iterrows()}
    check(D["agg"] == exp, f"{L}: agg differs from school_aggregates_by_lcff.csv")
    # schools
    dm = d[(d.subject == "math") & (d.year != 2021)]
    both = dm[dm.economic_status != "All students"].dropna(subset=["mean_scale_score"]).groupby(["cds_code", "year"]).economic_status.nunique()
    keep = set(both[both == 2].reset_index().cds_code)
    check(set(x["id"] for x in D["schools"]) == keep, f"{L}: school set differs (schools with both groups published in some non-2021 year)")
    check([x["id"] for x in D["schools"]] == [x["id"] for x in sorted(D["schools"], key=lambda x: (x["n"].lower(), x["c"]))], f"{L}: schools not sorted by name")
    check(len(set(x["id"] for x in D["schools"])) == len(D["schools"]), f"{L}: duplicate school ids")
    info = dm.sort_values("year").groupby("cds_code").last()[["school", "district", "county"]]
    cls = c.set_index("cds_code")
    bad = []
    for x in D["schools"]:
        cds = x["id"]
        exp = {"id": cds, "n": info.loc[cds, "school"], "d": info.loc[cds, "district"], "c": info.loc[cds, "county"],
               "u": round(float(cls.loc[cds, "upp_pre2020_mean"]), 1) if cds in cls.index else None,
               "l": (1 if cls.loc[cds, "lcff_plus_fixed"] == "LCFF+" else 0) if cds in cls.index else None}
        g = dm[dm.cds_code == cds]
        for lab, k in [("Economically disadvantaged", "SED"), ("Not economically disadvantaged", "NOT")]:
            exp[k] = rows_by_year(g[g.economic_status == lab], VAL)
        if x != exp:
            bad.append(cds)
    check(not bad, f"{L}: {len(bad)} school records differ from schools_by_economic_status.csv (first: {bad[:3]})")
    # NAEP
    NSTAT = {"MN:MN": "mean", "SD:SD": "sd", "PC:P1": "p10", "PC:P2": "p25", "PC:P5": "p50", "PC:P7": "p75", "PC:P9": "p90",
             "ALC:BB": "belowBasic", "ALC:AB": "basicUp", "ALC:AP": "proficientUp", "ALC:AD": "advanced",
             "ALD:BA": "basicOnly", "ALD:PR": "proficientOnly", "RP:RP": "share"}
    nz = n[n.ses_variable_code.isin(["TOTAL", "ECONDIS"]) & (n.statistic_family != "score distribution") & (n.is_displayable == 1)]
    check(D["naep"]["years"] == NAEP_YEARS, f"{L}: naep years")
    exp = {}
    for (var, lev, year), g in nz.groupby(["ses_variable_code", "ses_level_code", "year"]):
        k = {("TOTAL", 1): "ALL", ("ECONDIS", 1): "SED", ("ECONDIS", 2): "NOT"}.get((var, int(lev)))
        if not k:
            continue
        mn = g[g.statistic_code == "MN:MN"]
        row = {"n": int(mn.cell_n.iloc[0])}
        for _, x in g.iterrows():
            if x.statistic_code in NSTAT:
                row[NSTAT[x.statistic_code]] = [round(float(x.estimate), 2), round(float(x.standard_error), 2)]
        exp.setdefault(k, {})[str(int(year))] = row
    check(D["naep"]["groups"] == exp, f"{L}: naep groups differ from naep_ca_grade8_math_by_ses.csv")
    # what the page says about the payload
    html = (REPO / "index.html").read_text(encoding="utf-8")
    check(str(D["standard"]) in html, f"index.html: does not mention the standard-met cut score {D['standard']}")
    check('"data.js"' in html and "CAASPP_ECON" in html, "index.html: does not load data.js / window.CAASPP_ECON")
    for k in NSTAT.values():
        if k != "share":
            check(f"'{k}'" in html, f"index.html: payload NAEP statistic {k} is not used by the page")


def main():
    steps = [
        ("README data dictionary", check_readme, ()),
    ]
    ctx = {}

    def run(name, fn, *args):
        before = len(FAILURES)
        try:
            out = fn(*args)
        except Exception:
            FAILURES.append(f"{name}: raised\n" + traceback.format_exc())
            out = None
        n = len(FAILURES) - before
        print(f"{'FAIL' if n else 'ok  '}  {name}" + (f"  ({n} problem{'s' if n > 1 else ''})" if n else ""))
        return out

    run("README data dictionary", check_readme)
    s = run("statewide_all_groups.csv", check_statewide_all_groups)
    run("statewide_economic_status.csv", check_statewide_economic_status, s)
    d = run("schools_by_economic_status.csv", check_schools)
    u = run("schools_upp_lcff.csv", check_upp)
    c = run("schools_lcff_classification.csv (derived)", check_classification, u)
    a = run("school_aggregates_by_lcff.csv (derived)", check_aggregates, d, c)
    p = run("scale_score_percentiles.csv", check_percentiles)
    run("same_students_growth.csv", check_growth)
    n = run("naep_ca_grade8_math_by_ses.csv", check_naep)
    run("naep_ca_grade8_math_year_comparisons.csv", check_naep_comparisons, n)
    run("odds_by_year.csv (derived)", check_odds, s, a, n)
    run("data.js against the CSVs", check_payload, s, d, c, a, p, n)

    if FAILURES:
        print(f"\n{len(FAILURES)} failed check(s):")
        for f in FAILURES:
            print(" -", f)
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
