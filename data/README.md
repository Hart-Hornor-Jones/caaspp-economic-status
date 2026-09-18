# Data files

All files are UTF-8 CSV with a header row. `year` is the calendar year of the spring test
(2019 = school year 2018–19). There was no test in 2020; 2021 rows exist but testing was optional
that year and under half of students took part. `subject` is `ela` or `math`. Scores are Smarter
Balanced scale scores. Percentages are of students with scores; CDE rounds 2015 and 2016 percentages
to whole numbers. Cells CDE suppresses (fewer than 11 students) are blank.

Economic status is CDE's student group 31, "socioeconomically disadvantaged" (labeled "economically
disadvantaged" on the CAASPP reporting site): students eligible for free or reduced-price meals, or
whose parents did not complete high school, or who are migrant, homeless, or foster youth. Group 111
is its complement. The definition changed in 2022–23, when the number of grade-11 students so counted
rose by about a tenth.

## statewide_all_groups.csv
Statewide results, every CDE student group, grades 3–8 and 11, both subjects, 2015–2025. From the
statewide rows of the CAASPP research files.

| column | |
|---|---|
| `year`, `subject`, `grade` | |
| `group_code`, `group_name`, `group_category` | CDE student group (1 = all students, 31 / 111 = economic status, 74–80 and 144 = ethnicity, 90–94 = parent education, 3 / 4 = gender, 160 / 180 / 6–8 = English-language status, 128 / 99 = disability, …) |
| `enrolled`, `tested` | students enrolled; students tested |
| `mean_scale_score` | |
| `pct_level4_exceeded`, `pct_level3_met`, `pct_met_or_exceeded`, `pct_level2_nearly_met`, `pct_level1_not_met` | achievement levels, % of tested students |

## statewide_economic_status.csv
CDE's economic-status crosstab workbooks, which add the standard deviation: economic status × ethnicity
× grade × subject × year. `ethnicity` = `All` for the two-group totals.

| column | |
|---|---|
| `year`, `subject`, `grade`, `economic_status`, `ethnicity` | |
| `tested`, `mean_scale_score`, `sd_scale_score`, `pct_met_or_exceeded` | |
| `source_workbook` | CDE file name |

## schools_by_economic_status.csv
Every California public school with grade-11 results, 2015–2025, both subjects, three rows per
school-year-subject: all students, economically disadvantaged, not economically disadvantaged.
From the school rows of the CAASPP research files. Names are as listed in that year's file.

| column | |
|---|---|
| `cds_code` | 14-digit County-District-School code |
| `school`, `district`, `county`, `zip`, `school_type` | `school_type`: `school`, `direct-funded charter`, or `locally funded charter` |
| `year`, `subject`, `grade` | grade is always 11 |
| `economic_status` | `All students`, `Economically disadvantaged`, `Not economically disadvantaged` |
| `enrolled`, `tested`, `mean_scale_score`, `pct_level4_exceeded`, `pct_level3_met`, `pct_met_or_exceeded`, `pct_level2_nearly_met`, `pct_level1_not_met` | as above |

## schools_upp_lcff.csv
Unduplicated pupil percentage by school and school year, 2016–17 to 2025–26 (CALPADS; grades 9–12
enrollment). `cde_lcff_plus_flag` is CDE's own LCFF+ flag for that year.

| column | |
|---|---|
| `cds_code`, `school_year` | |
| `enrollment_9_12`, `upp_pct` | |
| `cde_lcff_plus_flag` | Y / N |

## schools_lcff_classification.csv  (derived)
One row per school: mean UPP over 2016–17 to 2019–20 and the fixed label used by the chart
(`LCFF+` when that mean is above 75).

| column | |
|---|---|
| `cds_code`, `upp_pre2020_mean`, `years_of_upp_pre2020`, `lcff_plus_fixed` | |

## school_aggregates_by_lcff.csv  (derived)
LCFF+ vs. other high schools, by year and subject, from each school's all-students results.

| column | |
|---|---|
| `subject`, `grade`, `year`, `school_group` | `LCFF+` / `Not LCFF+` |
| `weighting` | `students` (each school weighted by students tested) or `schools` (equal weights) |
| `school_set` | `all_schools_reporting` or `same_schools_every_year` (schools with results in all nine non-2021 years) |
| `schools`, `tested` | number of schools; students tested |
| `mean_scale_score`, `pct_level4_exceeded`, `pct_level3_met`, `pct_met_or_exceeded`, `pct_level2_nearly_met`, `pct_level1_not_met` | weighted means of the school values |

## scale_score_percentiles.csv
CDE's published statewide percentile tables: the scale score at the 1st, 10th, 20th, …, 90th, and
99th percentile of all tested students, by year, subject, and grade (3–8 and 11).

| column | |
|---|---|
| `year`, `subject`, `grade`, `percentile`, `scale_score` | |

## same_students_growth.csv
The longitudinal tables of the CAASPP technical reports (appendix 10), which follow the same students
from one grade to the next, grades 3–8 only. Each table contributes two rows per group: the earlier
grade-year and the later one, for the students matched across both. Reports for 2016, 2017, 2019, and
2021–2025; the 2021 and 2022 reports carry ethnicity and gender only.

| column | |
|---|---|
| `report_year`, `table_title` | the technical report and table the rows come from |
| `subject`, `group`, `students` | students matched in that table |
| `year`, `grade` | the administration each row describes |
| `mean_scale_score`, `sd_scale_score`, `pct_level1_not_met`, `pct_level2_nearly_met`, `pct_level3_met`, `pct_level4_exceeded`, `pct_met_or_exceeded` | |
