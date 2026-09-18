# build

- `make_site_data.py` — from `data/`, writes `data/schools_lcff_classification.csv`,
  `data/school_aggregates_by_lcff.csv`, and `data.js`. Needs pandas. Run from any folder:
  `python build/make_site_data.py`.
- `make_data.py` — how the other files in `data/` were assembled from the California Department of
  Education's research files, entity lists, UPP files, percentile tables, and technical-report
  tables. It reads local copies of those sources (paths at the top of the script), so it is
  documentation rather than something to run.
