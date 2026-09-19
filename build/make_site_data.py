"""
make_site_data.py -- derive the school-level classification and aggregates, and write data.js for the
page, from the files in ../data/. Anyone with the repository can run it (pandas only).

  data/schools_lcff_classification.csv   one row per school: pre-2020 mean UPP and the fixed LCFF+ label
  data/school_aggregates_by_lcff.csv     LCFF+ vs. other high schools, by year and subject, under two
                                         weightings (students / schools) and two school sets
                                         (all schools reporting that year / schools reporting every year)
  data.js                                grade-11 mathematics only, the payload behind index.html

Run from anywhere:  python build/make_site_data.py
"""
from pathlib import Path
import json
import datetime as dt
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = REPO / "data"

SUBJECT, GRADE = "math", 11
STANDARD = {"math": 2628, "ela": 2583}          # grade-11 "standard met" cut scores
VIZ_YEARS = [2015, 2016, 2017, 2018, 2019, 2022, 2023, 2024, 2025]   # 2020: no test; 2021: optional testing
PRE2020 = ["2016-2017", "2017-2018", "2018-2019", "2019-2020"]
LCFF_CUT = 75.0                                 # LCFF+ = more than 75% unduplicated pupils (Ed. Code 92680.4)
VAL = ["tested", "mean_scale_score", "pct_level4_exceeded", "pct_level3_met", "pct_met_or_exceeded",
       "pct_level2_nearly_met", "pct_level1_not_met"]
SHORT = ["tested", "mean", "L4", "L3", "met", "L2", "L1"]
ECON = {"All students": "ALL", "Economically disadvantaged": "SED", "Not economically disadvantaged": "NOT"}


def r(v, k=2):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), k)


def rows_by_year(g):
    """{year: [tested, mean, L4, L3, met, L2, L1]} for one school x group (or the state x group)."""
    out = {}
    for _, row in g.iterrows():
        vals = [row[c] for c in VAL]
        if pd.isna(vals[1]):
            continue                               # suppressed cell (scores blank)
        out[str(int(row["year"]))] = [int(vals[0])] + [r(v, 1) for v in vals[1:]]
    return out


def classify():
    u = pd.read_csv(DATA / "schools_upp_lcff.csv", dtype={"cds_code": str})
    pre = u[u["school_year"].isin(PRE2020)].groupby("cds_code")["upp_pct"].agg(["mean", "size"]).reset_index()
    pre.columns = ["cds_code", "upp_pre2020_mean", "years_of_upp_pre2020"]
    pre["upp_pre2020_mean"] = pre["upp_pre2020_mean"].round(2)
    pre["lcff_plus_fixed"] = np.where(pre["upp_pre2020_mean"] > LCFF_CUT, "LCFF+", "Not LCFF+")
    pre = pre.sort_values("cds_code")
    pre.to_csv(DATA / "schools_lcff_classification.csv", index=False, encoding="utf-8", lineterminator="\n")
    print(f"  schools_lcff_classification.csv: {len(pre):,} schools "
          f"({(pre.lcff_plus_fixed == 'LCFF+').sum():,} LCFF+)")
    return pre


def aggregates(d, cls):
    """School-level series: LCFF+ vs. other, all-students scores per school, two weightings, two panels."""
    a = d[d["economic_status"] == "All students"].merge(cls[["cds_code", "lcff_plus_fixed"]], on="cds_code")
    a = a.dropna(subset=["mean_scale_score"])
    out = []
    for subj, g in a.groupby("subject"):
        every = g[g["year"].isin(VIZ_YEARS)].groupby("cds_code")["year"].nunique()
        fixed_ids = set(every[every == len(VIZ_YEARS)].index)
        for panel, gg in (("all_schools_reporting", g), ("same_schools_every_year", g[g["cds_code"].isin(fixed_ids) & g["year"].isin(VIZ_YEARS)])):
            for (year, lab), h in gg.groupby(["year", "lcff_plus_fixed"]):
                w = h["tested"].astype(float)
                for weighting in ("students", "schools"):
                    rec = {"subject": subj, "grade": GRADE, "year": int(year), "school_group": lab,
                           "weighting": weighting, "school_set": panel, "schools": int(len(h)), "tested": int(w.sum())}
                    for c in VAL[1:]:
                        v = h[c].astype(float)
                        ok = v.notna()
                        rec[c] = round(float((v[ok] * w[ok]).sum() / w[ok].sum()), 2) if weighting == "students" else round(float(v[ok].mean()), 2)
                    out.append(rec)
    agg = pd.DataFrame(out).sort_values(["subject", "school_set", "weighting", "school_group", "year"])
    agg.to_csv(DATA / "school_aggregates_by_lcff.csv", index=False, encoding="utf-8", lineterminator="\n")
    print(f"  school_aggregates_by_lcff.csv: {len(agg):,} rows")
    return agg


def main():
    print("deriving ...")
    cls = classify()
    d = pd.read_csv(DATA / "schools_by_economic_status.csv", dtype={"cds_code": str})
    agg = aggregates(d, cls)

    # ---- data.js (grade-11 mathematics) ------------------------------------------------------
    s = pd.read_csv(DATA / "statewide_all_groups.csv")
    s = s[(s.subject == SUBJECT) & (s.grade == GRADE) & (s.group_code.isin([1, 31, 111]))]
    state = {{1: "ALL", 31: "SED", 111: "NOT"}[k]: rows_by_year(g) for k, g in s.groupby("group_code")}

    p = pd.read_csv(DATA / "scale_score_percentiles.csv")
    p = p[(p.subject == SUBJECT) & (p.grade == GRADE)].sort_values(["year", "percentile"])
    pct = {str(int(y)): {"p": g["percentile"].astype(int).tolist(), "s": g["scale_score"].astype(int).tolist()} for y, g in p.groupby("year")}

    ag = agg[agg.subject == SUBJECT]
    aggjs = {}
    for (panel, weighting), g in ag.groupby(["school_set", "weighting"]):
        key = f"{weighting}|{'fixed' if panel == 'same_schools_every_year' else 'all'}"
        aggjs[key] = {}
        for lab, h in g.groupby("school_group"):
            aggjs[key]["LCFF" if lab == "LCFF+" else "NON"] = {
                str(int(row.year)): [int(row.schools), int(row.tested)] + [r(row[c], 2) for c in VAL[1:]] for _, row in h.iterrows()}

    dm = d[(d.subject == SUBJECT) & (d.grade == GRADE) & (d.year != 2021)]
    both = dm[dm.economic_status != "All students"].dropna(subset=["mean_scale_score"])
    both = both.groupby(["cds_code", "year"])["economic_status"].nunique()
    keep = set(both[both == 2].reset_index()["cds_code"])
    info = dm.sort_values("year").groupby("cds_code").last()[["school", "district", "county"]]
    upp = cls.set_index("cds_code")
    schools = []
    for cds, g in dm[dm.cds_code.isin(keep)].groupby("cds_code"):
        rec = {"id": cds, "n": info.loc[cds, "school"], "d": info.loc[cds, "district"], "c": info.loc[cds, "county"],
               "u": r(upp.loc[cds, "upp_pre2020_mean"], 1) if cds in upp.index else None,
               "l": (1 if upp.loc[cds, "lcff_plus_fixed"] == "LCFF+" else 0) if cds in upp.index else None}
        for lab, h in g.groupby("economic_status"):
            k = ECON[lab]
            if k in ("SED", "NOT"):
                rec[k] = rows_by_year(h)
        schools.append(rec)
    schools.sort(key=lambda x: (x["n"].lower(), x["c"]))

    # ---- NAEP grade 8 mathematics (statewide only) --------------------------------------------
    nz = pd.read_csv(DATA / "naep_ca_grade8_math_by_ses.csv")
    nz = nz[(nz.ses_variable_code.isin(["TOTAL", "ECONDIS"])) & (nz.statistic_family != "score distribution") & (nz.is_displayable == 1)]
    NSTAT = {"MN:MN": "mean", "SD:SD": "sd", "PC:P1": "p10", "PC:P2": "p25", "PC:P5": "p50", "PC:P7": "p75", "PC:P9": "p90",
             "ALC:BB": "belowBasic", "ALC:AB": "basicUp", "ALC:AP": "proficientUp", "ALC:AD": "advanced",
             "ALD:BA": "basicOnly", "ALD:PR": "proficientOnly", "RP:RP": "share"}
    NGRP = {("TOTAL", 1): "ALL", ("ECONDIS", 1): "SED", ("ECONDIS", 2): "NOT"}
    naep = {"years": sorted(int(y) for y in nz.year.unique()), "groups": {}}
    for (var, lev, year), g in nz.groupby(["ses_variable_code", "ses_level_code", "year"]):
        key = NGRP.get((var, int(lev)))
        if not key:
            continue
        mn = g[g.statistic_code == "MN:MN"]
        row = {"n": int(mn.cell_n.iloc[0]) if len(mn) and pd.notna(mn.cell_n.iloc[0]) else None}   # unweighted sample size
        for _, x in g.iterrows():
            k = NSTAT.get(x.statistic_code)
            if k:
                row[k] = [r(x.estimate, 2), r(x.standard_error, 2)]
        naep["groups"].setdefault(key, {})[str(int(year))] = row
    cmp_ = pd.read_csv(DATA / "naep_ca_grade8_math_year_comparisons.csv")
    print("  naep: years", naep["years"], "| comparison columns:", list(cmp_.columns)[:12])

    # ---- odds by year (statewide CAASPP and NAEP, plus the LCFF+ school groups) -----------------
    # odds = p/(1-p) of being at (or above) a level; odds ratio = not-disadvantaged odds / disadvantaged odds
    orows = []
    LV = [("pct_level4_exceeded", "standard exceeded (level 4)"), ("pct_met_or_exceeded", "standard met or exceeded (levels 3-4)"),
          ("pct_level3_met", "standard met, not exceeded (level 3)"), ("pct_level2_nearly_met", "standard nearly met (level 2)"),
          ("pct_level1_not_met", "standard not met (level 1)")]
    def odds(v):
        return None if v is None or pd.isna(v) or v <= 0 or v >= 100 else round(float(v) / (100 - float(v)), 4)
    sw = pd.read_csv(DATA / "statewide_all_groups.csv")
    sw = sw[(sw.subject == SUBJECT) & (sw.grade == GRADE) & (sw.group_code.isin([31, 111]))]
    for year, g in sw.groupby("year"):
        a, b = g[g.group_code == 31], g[g.group_code == 111]
        for col, lab in LV:
            oa, ob = odds(a[col].iloc[0]) if len(a) else None, odds(b[col].iloc[0]) if len(b) else None
            orows.append({"test": "CAASPP grade 11 mathematics", "comparison": "all California students", "year": int(year), "level": lab,
                          "share_disadvantaged_pct": a[col].iloc[0] if len(a) else None, "share_not_disadvantaged_pct": b[col].iloc[0] if len(b) else None,
                          "odds_disadvantaged": oa, "odds_not_disadvantaged": ob, "odds_ratio_not_over_disadvantaged": round(ob / oa, 4) if oa and ob else None})
    la = agg[(agg.subject == SUBJECT) & (agg.weighting == "students") & (agg.school_set == "all_schools_reporting")]
    for year, g in la.groupby("year"):
        a, b = g[g.school_group == "LCFF+"], g[g.school_group == "Not LCFF+"]
        for col, lab in LV:
            oa, ob = odds(a[col].iloc[0]) if len(a) else None, odds(b[col].iloc[0]) if len(b) else None
            orows.append({"test": "CAASPP grade 11 mathematics", "comparison": "LCFF+ vs. other high schools (student-weighted, all reporting)", "year": int(year), "level": lab,
                          "share_disadvantaged_pct": a[col].iloc[0] if len(a) else None, "share_not_disadvantaged_pct": b[col].iloc[0] if len(b) else None,
                          "odds_disadvantaged": oa, "odds_not_disadvantaged": ob, "odds_ratio_not_over_disadvantaged": round(ob / oa, 4) if oa and ob else None})
    NLV = [("advanced", "at NAEP Advanced"), ("proficientUp", "at or above NAEP Proficient"), ("basicUp", "at or above NAEP Basic"),
           ("proficientOnly", "at NAEP Proficient, not Advanced"), ("basicOnly", "at NAEP Basic, not Proficient"), ("belowBasic", "below NAEP Basic")]
    for year in naep["years"]:
        a, b = naep["groups"]["SED"].get(str(year), {}), naep["groups"]["NOT"].get(str(year), {})
        for k, lab in NLV:
            pa, pb = (a.get(k) or [None])[0], (b.get(k) or [None])[0]
            oa, ob = odds(pa), odds(pb)
            orows.append({"test": "NAEP grade 8 mathematics", "comparison": "all California students (NAEP sample)", "year": int(year), "level": lab,
                          "share_disadvantaged_pct": pa, "share_not_disadvantaged_pct": pb,
                          "odds_disadvantaged": oa, "odds_not_disadvantaged": ob, "odds_ratio_not_over_disadvantaged": round(ob / oa, 4) if oa and ob else None})
    od = pd.DataFrame(orows)
    od.to_csv(DATA / "odds_by_year.csv", index=False, encoding="utf-8", lineterminator="\n")
    print(f"  odds_by_year.csv: {len(od):,} rows")

    payload = {"generated": dt.date.today().isoformat(), "subject": SUBJECT, "grade": GRADE,
               "standard": STANDARD[SUBJECT], "years": VIZ_YEARS, "cols": SHORT, "lcff_cut": LCFF_CUT,
               "pct": pct, "state": state, "agg": aggjs, "schools": schools, "naep": naep}
    js = "window.CAASPP_ECON=" + json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + ";\n"
    (REPO / "data.js").write_text(js, encoding="utf-8")
    print(f"  data.js: {len(js)/1e6:.2f} MB, {len(schools):,} schools, years {VIZ_YEARS[0]}-{VIZ_YEARS[-1]}")
    print("done.")


if __name__ == "__main__":
    main()
