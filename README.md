# Mathematics by economic status: CAASPP grade 11 and NAEP grade 8

California students' mathematics results split into economically disadvantaged students and everyone
else: the state's CAASPP grade-11 test, 2015–2025 (statewide, across high schools grouped by LCFF+
status, and within any one high school or pooled set of schools), and the national NAEP grade-8
assessment, 2019–2024 (statewide sample). A small interactive chart, and the data files behind it.

Live page: `https://hart-hornor-jones.github.io/caaspp-economic-status/`

## What is here

| | |
|---|---|
| `index.html`, `data.js` | the chart (no dependencies; `data.js` is generated) |
| `data/` | the data files — statewide results for every CDE student group, grade-11 results by economic status for every California school, school UPP and LCFF+ status, CDE's scale-score percentile tables, same-students growth tables, and NAEP grade-8 mathematics estimates and significance tests by SES. Column definitions in `data/README.md`. |
| `build/` | the scripts that produced `data/` and `data.js` |

## Rebuilding

`data.js` and the two derived files in `data/` (`schools_lcff_classification.csv`,
`school_aggregates_by_lcff.csv`) are reproduced from the other files in `data/` by

    python build/make_site_data.py

(pandas required). `build/make_data.py` records how the remaining files in `data/` were assembled
from the California Department of Education's published research files; it reads local copies of
those files and is included for documentation.

## Source and license

All figures are from the California Department of Education (CAASPP research files, CALPADS
unduplicated pupil counts, CAASPP technical reports and scale-score percentile tables) and the NAEP Data
Service of the National Center for Education Statistics. Code is
released under the MIT License; the data files are derived from public records.
