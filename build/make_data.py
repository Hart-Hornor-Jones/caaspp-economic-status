"""
make_data.py -- assemble the curated data files in ../data/ from the project's local extracts.

This script documents where every file in data/ came from. It reads files that live outside the
repository (the project's working folders), so visitors cannot run it; they do not need to.
Everything a visitor might want to recompute starts from data/ and make_site_data.py.

Sources (all California Department of Education, CAASPP / Smarter Balanced, public research files):
  statewide_all_groups.csv        the statewide rows of the CAASPP research files, every student group
  statewide_economic_status.csv   CDE's economic-status crosstab workbooks (add the standard deviation)
  schools_by_economic_status.csv  school rows of the research files, grade 11, all / disadvantaged / not
  schools_upp_lcff.csv            CALPADS unduplicated pupil percentage (UPP) by school and year
  scale_score_percentiles.csv     CDE's published scale-score percentile tables (one per test year)
  same_students_growth.csv        CAASPP technical-report appendix tables following the same students
                                  from one grade to the next (grades 3-8 only; grade 11 is never followed)
  naep_ca_grade8_math_by_ses.csv  NAEP Data Service estimates, California grade 8 mathematics, 2015-2024,
                                  by economic-disadvantage status, parent education and school lunch share
  naep_ca_grade8_math_year_comparisons.csv   NAEP's official across-year significance tests for the same

Run from anywhere:  python build/make_data.py
"""
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = REPO / "data"
SVET = REPO.parent                                   # ...\svetlana\Svetlana
SES = SVET / "SBAC by SES 2026-09-17"
UPP = SVET / "Panel Build 2026-06-07" / "components" / "upp_lcff.csv"
PCT = SVET / "CAASPP Percentiles 2026-08-19" / "caaspp_scale_score_percentiles_tidy.csv"
NAEP = Path.home() / "Documents" / "Codex" / "2026-09-18" / "our-x20" / "outputs"   # NAEP API pull (ChatGPT-assisted, 2026-09-19)
ENT = SVET.parent / "hs data"                        # sb_caYYYYentities_ascii.txt (CDE research-file entity lists)
YEARS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]
TYPES = {"07": "school", "09": "direct-funded charter", "10": "locally funded charter"}


def entities():
    """School names from CDE's fixed-width entity files, one row per school x year (type 07 = school).
    2015-2023: cds(14) 4sp year(4) type(2) county(50) district(50) school(50) zip(5)
    2024-2025: cds(14) type(2) 4sp year(4) county(25) district(40) school(60) zip(5)"""
    rows = []
    for y in YEARS:
        for line in (ENT / f"sb_ca{y}entities_ascii.txt").read_text(encoding="latin-1").splitlines():
            if len(line) < 150:
                continue
            if y >= 2024:
                cds, typ, county, district, school, zc = line[0:14], line[14:16], line[24:49], line[49:89], line[89:149], line[149:154]
            else:
                cds, typ, county, district, school, zc = line[0:14], line[22:24], line[24:74], line[74:124], line[124:174], line[174:179]
            if typ not in TYPES:                     # 04 state, 05 county, 06 district: not schools
                continue
            rows.append((cds, y, county.strip(), district.strip(), school.strip(), zc.strip(), TYPES[typ]))
    e = pd.DataFrame(rows, columns=["cds_code", "year", "county", "district", "school", "zip", "school_type"])
    assert not e.duplicated(["cds_code", "year"]).any()
    return e

LEVELS = {"L4": "pct_level4_exceeded", "L3": "pct_level3_met", "met": "pct_met_or_exceeded",
          "L2": "pct_level2_nearly_met", "L1": "pct_level1_not_met"}
ECON = {"All": "All students", "SED": "Economically disadvantaged", "Not SED": "Not economically disadvantaged",
        "Disadvantaged": "Economically disadvantaged", "Not disadvantaged": "Not economically disadvantaged"}


def write(df, name):
    DATA.mkdir(exist_ok=True)
    df.to_csv(DATA / name, index=False, encoding="utf-8", lineterminator="\n")
    print(f"  {name}: {len(df):,} rows")


def main():
    print("building data/ ...")

    # 1. statewide rows, every student group -------------------------------------------------
    s = pd.read_csv(SES / "state_rows_all_groups_tidy.csv")
    s = s.rename(columns={"group": "group_code", "group_cat": "group_category", "mean": "mean_scale_score", **LEVELS})
    s = s[["year", "subject", "grade", "group_code", "group_name", "group_category", "enrolled", "tested",
           "mean_scale_score", "pct_level4_exceeded", "pct_level3_met", "pct_met_or_exceeded",
           "pct_level2_nearly_met", "pct_level1_not_met"]]
    s = s.sort_values(["subject", "grade", "year", "group_code"])
    write(s, "statewide_all_groups.csv")

    # 2. economic-status crosstab workbooks (n, mean, SD, % met; by ethnicity too) ------------
    x = pd.read_csv(SES / "econ_status_crosstabs_tidy.csv")
    x = x.rename(columns={"econ": "economic_status", "n": "tested", "mean": "mean_scale_score",
                          "sd": "sd_scale_score", "pct_met": "pct_met_or_exceeded", "file": "source_workbook"})
    x["economic_status"] = x["economic_status"].map(ECON).fillna(x["economic_status"])
    x = x[["year", "subject", "grade", "economic_status", "ethnicity", "tested", "mean_scale_score",
           "sd_scale_score", "pct_met_or_exceeded", "source_workbook"]]
    write(x.sort_values(["subject", "grade", "year", "ethnicity", "economic_status"]), "statewide_economic_status.csv")

    # 3. school x year x subject x economic status (grade 11) ---------------------------------
    d = pd.read_csv(SES / "school_by_econ_tidy.csv", dtype={"cds": str})
    d = d.rename(columns={"cds": "cds_code", "econ": "economic_status", "mean": "mean_scale_score", **LEVELS})
    d["economic_status"] = d["economic_status"].map(ECON)
    e = entities()                                   # names re-read from the entity files (year-specific)
    d = d.drop(columns=["school", "district", "county"]).merge(e, on=["cds_code", "year"], how="left")
    missing = d["school"].isna()
    print(f"  rows dropped because the entity is a district or county, not a school: {int(missing.sum())} "
          f"({d[missing].cds_code.nunique()} entities)")
    d = d[~missing]
    d = d[["cds_code", "school", "district", "county", "zip", "school_type", "year", "subject", "grade", "economic_status",
           "enrolled", "tested", "mean_scale_score", "pct_level4_exceeded", "pct_level3_met",
           "pct_met_or_exceeded", "pct_level2_nearly_met", "pct_level1_not_met"]]
    d = d.sort_values(["cds_code", "subject", "year", "economic_status"])
    write(d, "schools_by_economic_status.csv")

    # 4. UPP by school and year ----------------------------------------------------------------
    u = pd.read_csv(UPP, dtype={"cds14": str})
    u = u.rename(columns={"cds14": "cds_code", "cupc_year": "school_year", "enroll_9_12": "enrollment_9_12",
                          "upp_pct": "upp_pct", "lcff_plus_flag": "cde_lcff_plus_flag"})
    write(u.sort_values(["cds_code", "school_year"]), "schools_upp_lcff.csv")

    # 5. scale-score percentiles ---------------------------------------------------------------
    p = pd.read_csv(PCT)
    p["subject"] = p["subject"].str.lower()
    p = p[p["subject"].isin(["ela", "math"])]           # the science tables are on another scale
    p["grade"] = p["grade"].str.replace("G", "", regex=False).astype(int)
    p = p[["year", "subject", "grade", "percentile", "scale_score"]].sort_values(["subject", "grade", "year", "percentile"])
    write(p, "scale_score_percentiles.csv")

    # 6. same-students growth tables -----------------------------------------------------------
    t = pd.read_csv(SES / "techreport_longitudinal_tidy.csv")
    t = t.rename(columns={"report": "report_year", "table": "table_title", "n_valid": "students",
                          "mean": "mean_scale_score", "sd": "sd_scale_score", **LEVELS})
    t = t[["report_year", "table_title", "subject", "group", "students", "year", "grade", "mean_scale_score",
           "sd_scale_score", "pct_level1_not_met", "pct_level2_nearly_met", "pct_level3_met",
           "pct_level4_exceeded", "pct_met_or_exceeded"]]
    write(t, "same_students_growth.csv")

    # 7. NAEP grade 8 mathematics, California, by SES ---------------------------------------------
    n = pd.read_csv(NAEP / "naep_ca_grade8_math_ses_estimates_2015_2024.csv")
    n = n.drop(columns=["retrieved_at_utc", "program", "subject_code", "scale_code", "jurisdiction_code", "sample",
                        "data_key", "value_raw", "standard_error_raw", "error_flag"])
    write(n, "naep_ca_grade8_math_by_ses.csv")
    c = pd.read_csv(NAEP / "naep_ca_grade8_math_ses_year_comparisons_2015_2024.csv")
    write(c, "naep_ca_grade8_math_year_comparisons.csv")
    print("done.")


if __name__ == "__main__":
    main()
