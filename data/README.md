# Data files

All files are UTF-8 CSV with a header row and LF line endings. `year` is the calendar year of the spring
test (2019 = school year 2018–19). There was no test in 2020; 2021 rows exist in the CAASPP files that
carry them (noted below) but testing was optional that year and under half of students took part. `subject`
is `ela` or `math`. CAASPP scores are Smarter Balanced scale scores; NAEP scores are on NAEP's 0–500
composite scale. Percentages are of students with scores; CDE rounds 2015 and 2016 percentages to whole
numbers. Cells CDE suppresses (fewer than 11 students) are blank. `cds_code` is a 14-digit string with a
leading zero for counties 01–09; read it as text.

Economic status is CDE's student group 31, "socioeconomically disadvantaged" (labeled "economically
disadvantaged" on the CAASPP reporting site): students eligible for free or reduced-price meals, or
whose parents did not complete high school, or who are migrant, homeless, or foster youth. Group 111
is its complement. The definition changed in 2022–23, when the number of grade-11 students so counted
rose by about a tenth.

Row counts below are checked by `tests/check_data.py`, which also checks the column lists.

## statewide_all_groups.csv
Statewide results, every CDE student group, grades 3–8 and 11, both subjects, 2015–2019 and 2021–2025
(10 years). From the statewide rows of the CAASPP research files. 7,155 rows; one row per year × subject ×
grade × group. Not every group is published in every year (58 group codes in all; groups 170 and 190 start in 2017,
50–53 in 2019, 29 and 243 in 2021, 240–241 in 2022, and 250–252 in 2023). Groups 1, 31 and 111 are present for every year × subject × grade.

| column | |
|---|---|
| `year`, `subject`, `grade` | |
| `group_code`, `group_name`, `group_category` | CDE student group. `group_category` and the codes in each: All Students (1); Gender (3 male, 4 female); Economic Status (31 socioeconomically disadvantaged, 111 not); Race and Ethnicity (74 Black or African American, 75 American Indian or Alaska Native, 76 Asian, 77 Filipino, 78 Hispanic or Latino, 79 Native Hawaiian or Pacific Islander, 80 White, 144 two or more races); Ethnicity for Socioeconomically Disadvantaged (200–207, same order as 74–80 and 144) and for Not Socioeconomically Disadvantaged (220–227); Parent Education (90 not a high school graduate, 91 high school graduate, 92 some college, 93 college graduate, 94 graduate school, 121 declined to state); English-Language Fluency (6 fluent English proficient and English only, 7 IFEP, 8 RFEP, 120 ELs enrolled less than 12 months, 142 ELs enrolled 12 months or more, 160 EL, 170 ever-EL, 180 English only, 190 to be determined, 243 adult English learner, 250 long-term EL, 251 at risk of becoming long-term EL, 252 never-EL); Disability Status (99 no reported disabilities, 128 reported disabilities); Migrant (28 migrant education, 29 not); Foster Status (240 foster youth, 241 not); Homeless Status (52 homeless, 53 not); Military Status (50 armed forces family member, 51 not) |
| `enrolled`, `tested` | students enrolled; students tested (always at least 11) |
| `mean_scale_score` | |
| `pct_level4_exceeded`, `pct_level3_met`, `pct_met_or_exceeded`, `pct_level2_nearly_met`, `pct_level1_not_met` | achievement levels, % of tested students; `pct_met_or_exceeded` = level 3 + level 4 |

## statewide_economic_status.csv
CDE's economic-status crosstab workbooks, which add the standard deviation: economic status × ethnicity
× grade × subject × year, grades 3–8 and 11, 2015–2019 and 2022–2025 (no 2021 workbooks). 2,408 rows.
`ethnicity` = `All` for the two-group totals (from the `...econdisall...` workbooks); the other
rows come from the `...econdiseth...` workbooks. Ethnicity labels are copied as the workbooks spell
them, so the same group can appear as `Two or More Races` (2015–2019) and `Two or more races`
(2022–2025), two 2019 labels contain a line break (`American Indian or Alaska\nNative`, `Native Hawaiian
or Pacific\nIslander`), and `Blank` (2015–2019 only) is students with no ethnicity reported.
Means and standard deviations are whole numbers from 2016 on (one decimal in 2015); `pct_met_or_exceeded`
is a whole number from 2016 on and has two decimals in 2015. The `All` totals count slightly fewer
students (up to 3.3%) than groups 31 and 111 of `statewide_all_groups.csv` and their means and percentages differ from
those rows by up to 0.5, within the workbooks' rounding.

| column | |
|---|---|
| `year`, `subject`, `grade`, `economic_status`, `ethnicity` | `economic_status`: `Economically disadvantaged` or `Not economically disadvantaged` |
| `tested`, `mean_scale_score`, `sd_scale_score`, `pct_met_or_exceeded` | |
| `source_workbook` | CDE file name |

## schools_by_economic_status.csv
Every California public school with grade-11 results, 2015–2019 and 2021–2025, both subjects, up to three
rows per school-year-subject: all students, economically disadvantaged, not economically disadvantaged.
A row exists only when CDE published that group for that school (34,238 school-year-subjects have all three
rows, 9,552 have two, 1,369 have one). 123,187 rows, 3,653 schools. From the school rows of the CAASPP
research files. Names, district, ZIP code and school type are as listed in that year's entity file, so
they can change from year to year for the same `cds_code`; `zip` is blank for 48 rows and is whatever CDE
listed (a few schools carry out-of-state or placeholder ZIP codes).
Suppressed cells have blank scores and shares but keep `enrolled` and `tested`; every published cell has at
least 11 students tested, and a few cells with 11–23 tested are also suppressed (46 rows, 2019–2023).

| column | |
|---|---|
| `cds_code` | 14-digit County-District-School code |
| `school`, `district`, `county`, `zip`, `school_type` | `school_type`: `school`, `direct-funded charter`, or `locally funded charter` |
| `year`, `subject`, `grade` | grade is always 11 |
| `economic_status` | `All students`, `Economically disadvantaged`, `Not economically disadvantaged` |
| `enrolled`, `tested`, `mean_scale_score`, `pct_level4_exceeded`, `pct_level3_met`, `pct_met_or_exceeded`, `pct_level2_nearly_met`, `pct_level1_not_met` | as above |

## schools_upp_lcff.csv
Unduplicated pupil percentage by school and school year, 2016–17 to 2025–26 (CALPADS; grades 9–12
enrollment). 29,122 rows, 3,509 schools; `school_year` is written `2016-2017` … `2025-2026`.
`cde_lcff_plus_flag` is CDE's own LCFF+ flag for that year. It is `Y` in 169 rows where `upp_pct` is
exactly 75.00 and in one row at 74.99, so it is not simply `upp_pct > 75`; the chart's classification
(next file) applies the "more than 75%" rule to the pre-2020 mean instead. Twelve rows have zero
grade 9–12 enrollment.

| column | |
|---|---|
| `cds_code`, `school_year` | |
| `enrollment_9_12`, `upp_pct` | |
| `cde_lcff_plus_flag` | Y / N |

## schools_lcff_classification.csv  (derived)
One row per school with at least one UPP value for 2016–17 to 2019–20: the mean of those values, rounded
to two decimals, and the fixed label used by the chart (`LCFF+` when that rounded mean is above 75).
3,210 rows (1,299 LCFF+). Schools in `schools_by_economic_status.csv` without a pre-2020 UPP value (about
a quarter of them) have no row here and no LCFF+ status on the page.

| column | |
|---|---|
| `cds_code`, `upp_pre2020_mean`, `years_of_upp_pre2020`, `lcff_plus_fixed` | `years_of_upp_pre2020` is 1–4 |

## school_aggregates_by_lcff.csv  (derived)
LCFF+ vs. other high schools, by year and subject, from each school's all-students results (schools with a
published all-students cell and a row in `schools_lcff_classification.csv`). 152 rows: 2 subjects × 2 groups
× 2 weightings × (10 years for `all_schools_reporting`, including 2021, plus 9 for `same_schools_every_year`,
which omits 2021).

| column | |
|---|---|
| `subject`, `grade`, `year`, `school_group` | `LCFF+` / `Not LCFF+` |
| `weighting` | `students` (each school weighted by students tested) or `schools` (equal weights) |
| `school_set` | `all_schools_reporting` or `same_schools_every_year` (schools with results in all nine non-2021 years) |
| `schools`, `tested` | number of schools; students tested |
| `mean_scale_score`, `pct_level4_exceeded`, `pct_level3_met`, `pct_met_or_exceeded`, `pct_level2_nearly_met`, `pct_level1_not_met` | weighted means of the school values, rounded to two decimals |

## odds_by_year.csv  (derived)
The achievement-level shares of the two groups re-expressed as odds, p/(1−p), with the between-group odds
ratio, by year: statewide CAASPP grade 11 mathematics (2015–2019 and 2021–2025, from groups 31 and 111 of
`statewide_all_groups.csv`), LCFF+ vs. other high schools (student-weighted, all reporting schools, same years,
from `school_aggregates_by_lcff.csv`), and NAEP grade 8 (2015–2024, shares rounded to two decimals). 130 rows:
5 CAASPP levels × 10 years × 2 comparisons + 6 NAEP levels × 5 years. Odds are rounded to four decimals and
would be blank if a share were 0% or 100% (none is).

| column | |
|---|---|
| `test`, `comparison`, `year`, `level` | |
| `share_disadvantaged_pct`, `share_not_disadvantaged_pct` | the published shares (for the LCFF+ rows, the two sets of schools) |
| `odds_disadvantaged`, `odds_not_disadvantaged`, `odds_ratio_not_over_disadvantaged` | |

## scale_score_percentiles.csv
CDE's published statewide percentile tables: the scale score at the 1st, 10th, 20th, …, 90th, and
99th percentile of all tested students, by year (2015–2019 and 2022–2025; CDE published no 2021 table),
subject, and grade (3–8 and 11). 1,386 rows, a complete 9 × 2 × 7 × 11 grid.

| column | |
|---|---|
| `year`, `subject`, `grade`, `percentile`, `scale_score` | |

## same_students_growth.csv
The longitudinal tables of the CAASPP technical reports (appendix 10), which follow the same students
from one grade to the next, grades 3–8 only. 10,330 rows. Reports for 2016, 2017, 2019, and 2021–2025; the
2021 and 2022 reports carry ethnicity and gender only. Each table contributes one row per group per
administration it covers: two rows for a two-administration table, three for the tables that follow
students across three administrations (2019, 2021 and 2022 reports; the 2021 and 2022 three-year tables
reach back across the 2020 gap to 2017–18 and 2018–19). A table continued on a new page appears under
its title with ` (Continued)` added, so a group's rows can be split across the two titles. The 2019
report also contributes claim-level tables ("… on Claim 1" to "… on Claim 4"; 3,850 rows) that carry
only the mean and standard deviation. Achievement-level shares are given for two-administration tables
only; the three-administration tables carry the mean, standard deviation, and `pct_met_or_exceeded`.
Statistics are blank where a group has fewer than 11 matched students (2025 report; `students` is 0 for
98 of those rows). Table titles are copied from the reports, including their punctuation.

| column | |
|---|---|
| `report_year`, `table_title` | the technical report and table the rows come from |
| `subject`, `group`, `students` | students matched in that table |
| `year`, `grade` | the administration each row describes |
| `mean_scale_score`, `sd_scale_score`, `pct_level1_not_met`, `pct_level2_nearly_met`, `pct_level3_met`, `pct_level4_exceeded`, `pct_met_or_exceeded` | |

## naep_ca_grade8_math_by_ses.csv
NAEP Data Service estimates for California public-school students, grade 8 mathematics (composite scale,
0–500), assessment years 2015, 2017, 2019, 2022 and 2024, one row per year × student group × statistic:
5,850 rows = 5 years × 18 groups × 65 statistics. Groups: all students (`TOTAL`); economically
disadvantaged / not / information not available (`ECONDIS`, levels 1–3; before 2024 this was eligibility
for the National School Lunch Program, which NAEP carries forward as one series); highest parent education
(`PARED`, levels 1–5: did not finish high school, graduated high school, some education after high school,
graduated college, unknown); and the school-reported share of students eligible for free or reduced-price
lunch (`SCHOOL_FRPL_PCT`, levels 1–9: 0%, 1–5%, 6–10%, 11–25%, 26–34%, 35–50%, 51–75%, 76–99%, 100%;
NAEP's own code is `C051601` for 2015–2017 and `C051651` from 2019, kept in `api_variable_code`; many
California cells fail NAEP reporting standards).
Statistics (`statistic_code`): average score (`MN:MN`), standard deviation (`SD:SD`), 10th/25th/50th/75th/90th
percentile scores (`PC:P1`, `PC:P2`, `PC:P5`, `PC:P7`, `PC:P9`), percentages at each NAEP achievement level
(`ALD:BA`, `ALD:PR`, `ALD:AD`) and below Basic / at or above each level (`ALC:BB`, `ALC:AB`, `ALC:AP`, `ALC:AD`;
`ALC:AD` repeats `ALD:AD`), share of students in the group (`RP:RP`, summing to 100 across the levels of a
variable), and the score distribution in ten-point bins (`DP:D1` … `DP:D50`, summing to 100). Retrieved
from the NAEP API on 2026-09-19; the exact request is in `source_url`.

| column | |
|---|---|
| `subject`, `grade`, `scale`, `jurisdiction`, `year` | |
| `ses_variable_code`, `ses_variable`, `api_variable_code`, `api_variable`, `ses_level_code`, `ses_level` | the student group |
| `statistic_code`, `statistic_family`, `statistic`, `unit`, `percentile`, `achievement_level`, `score_interval_low`, `score_interval_high` | what the row measures; `unit` is `scale score` or `percent` |
| `estimate`, `standard_error` | blank when NAEP marks the statistic not displayable (`is_displayable` = 0; 1,485 rows). `standard_error` is −1 in 27 rows where NAEP reports no standard error for an extreme percentage (see `error_labels`) |
| `cell_n` | unweighted number of sampled students in the group (not a population count); for `RP:RP` it is the number of sampled students with a known value of the variable, the share's denominator |
| `stat_cv`, `is_displayable`, `error_labels` | NAEP's quality flags |
| `source_url` | the API request that returned the row |

## naep_ca_grade8_math_year_comparisons.csv
NAEP's own significance tests between assessment years, for the means, percentile scores and
achievement-level percentages in the file above (13 statistics; not the standard deviation, group share
or score distribution). 1,638 rows. Every pair of years is tested within one variable code: all ten pairs of
2015–2024 for `TOTAL`, `ECONDIS` and `PARED`; for the school lunch-share variable only 2015 vs. 2017
(`C051601`) and the three pairs among 2019, 2022 and 2024 (`C051651`), because NAEP does not compare across
the change of variable. `baseline_estimate` and `followup_estimate` repeat the estimates of the file above.
`change_followup_minus_baseline` is positive when the later year is higher; `official_significance` is
NAEP's verdict at the .05 level (`follow-up higher`, `follow-up lower`, `no statistically significant
difference`) and is blank when `is_comparison_displayable` is 0 (463 rows). `api_significance_focal_vs_target`
is the same verdict from the baseline year's side (`HIGHER` = baseline higher = follow-up lower).

| column | |
|---|---|
| `retrieved_at_utc`, `program`, `subject_code`, `subject`, `grade`, `scale_code`, `scale`, `jurisdiction_code`, `jurisdiction` | constant: retrieved 2026-09-19, NAEP (`NDE`), mathematics (`MAT`), grade 8, composite scale (`MRPCM`), California (`CA`) |
| `ses_variable_code`, `ses_variable`, `api_variable_code`, `api_variable`, `ses_level_code`, `ses_level` | the student group, as above |
| `statistic_code`, `statistic_family`, `statistic`, `unit`, `percentile`, `achievement_level` | what is compared, as above |
| `baseline_year`, `followup_year` | the earlier and later assessment year |
| `baseline_estimate`, `followup_estimate`, `change_followup_minus_baseline` | |
| `official_significance`, `api_significance_focal_vs_target`, `is_comparison_displayable` | NAEP's verdict and its displayability flag |
| `baseline_error_flag`, `baseline_error_labels`, `followup_error_flag`, `followup_error_labels` | NAEP's error bit-flag and its decoded labels for each year's cell |
| `data_keys` | NAEP's keys for the two cells compared |
| `source_url` | the API request that returned the row |

## data.js
The payload behind `index.html`, written by `build/make_site_data.py` from the files above (grade-11
mathematics and the NAEP statewide series only): a single statement `window.CAASPP_ECON={...};` whose JSON
has `generated` (build date), `subject`, `grade`, `standard` (2628, the grade-11 mathematics standard-met
cut score), `years` (the nine years the page plots; 2021 is carried in `state` and the `all` panels of
`agg` but never plotted), `cols` (the order of the seven numbers in every row: tested, mean, L4, L3, met,
L2, L1), `lcff_cut`, `pct` (the mathematics grade-11 percentile tables), `state` (groups `ALL`, `SED`,
`NOT`, rows by year), `agg` (keys `students|all`, `students|fixed`, `schools|all`, `schools|fixed`, each with
`LCFF` and `NON` rows by year prefixed by the number of schools), `schools` (the 1,922 schools with both
groups published in at least one plotted year: `id`, name `n`, district `d`, county `c`, pre-2020 UPP mean `u`,
LCFF+ flag `l`, and `SED` / `NOT` rows by year), and `naep` (years and, for `ALL`, `SED`, `NOT`, each
statistic as [estimate, standard error] with the unweighted sample size `n`). `tests/check_data.py` checks
that every value equals the CSVs.
