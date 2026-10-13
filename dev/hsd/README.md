# Hierarchical System Design (HSD) filters

This directory holds [JOSH](https://josh-project.github.io/josh/) (Just One Single History) filter
lists used to produce reduced views of the global workflow for a single forecasting system at a given
tier. The tier definitions and the documentation layout that supports them are described in
`docs/source/hsd.rst`.

| Tier | View | Lists applied (cumulative) |
|------|------|----------------------------|
| 0    | Full global workflow | none (`:/`) |
| 1    | One forecasting system | `<system>.tier1.list` |
| 1.5  | System without production code, still cycled (GFS and GCAFS only) | + `<system>.tier1p5.list` |
| 2    | System forecast-only (no data assimilation, no production code) | + `<system>.tier2.list` |

Only the GCAFS lists exist so far (prototype).

## Usage

`make_filter.sh` joins the lists for a tier into one JOSH `:exclude[...]` filter:

```bash
cd dev/hsd
./make_filter.sh gcafs 1      # Tier 1
./make_filter.sh gcafs 1.5    # Tier 1.5
./make_filter.sh gcafs 2      # Tier 2

# Produce a filtered history
josh-filter "$(./make_filter.sh gcafs 2)" HEAD
```

The lists are plain text: one repository-relative path per line, `#` starts a comment. Directories
are written without a trailing slash; `make_filter.sh` adds it. Trailing-`*` globs (e.g.
`dev/jobs/JGLOBAL_MARINE_*`) are used where a pattern matches only files that belong in the same
list. When editing, keep globs narrow: a glob must never match a file that a lower tier still needs.

## Pending lists

`<system>.<tier>.pending.list` holds removals that are correct in principle but would currently break
the filtered tree because shared Python code imports every system unconditionally:

* `dev/workflow/applications/application_factory.py`, `dev/workflow/rocoto/{tasks_factory,rocoto_xml_factory}.py`
  and `dev/workflow/ecflow/ecflow_suite_factory.py` import the classes of all systems.
* `ush/python/pygfs/__init__.py` imports all task modules.

Make those imports lazy (or registered per system), then pass `-p` to `make_filter.sh` to apply the pending
lists too.

## Files that are created by `sorc/link_workflow.sh`

Several directories GCAFS needs are not tracked in this repository; `sorc/link_workflow.sh` creates
them as (git-ignored) symlinks into submodules, so they are available as long as the submodule is kept:

* `parm/gdas/{aero,atm,io,ioda,anlstat,analcalc,jcb-gdas,jcb-algorithms,spoc}` and `ush/python/jcb`
  come from `sorc/gdas.cd`, which is therefore kept at Tiers 1 and 1.5 (the tracked `parm/gdas/staging`
  only holds snow analysis templates and is the only part of `parm/gdas` removed).
* `parm/post/*`, `parm/ufs/*` templates and CCPP suites come from `sorc/upp.fd` and `sorc/ufs_model.fd`.
* `parm/chem/nexus` comes from `sorc/nexus.fd`.

At Tier 2 `sorc/gdas.cd` is removed, but `link_workflow.sh` links `jcb` from it unconditionally; guard that
link with a directory check before using a Tier 2 tree.

Files that looked removable but are required by kept code were retained: `dev/workflow/aux`,
`ush/cpfsd.sh` and `ush/getdump.sh` (Tier 2 only), `ush/parse-storm-type.pl` (Tier 2 only),
`ush/wave_domain_grid.sh`, `ush/wave_extractvars.sh`, `ush/ocnice_extractvars.sh` (used by the
`extractvars` and archive jobs), and `dev/parm/config/gcafs/config.nsst` and `config.efcs`
(sourced by `config.fcst.j2`).

## Known limitations

* JOSH filters whole files and directories; it does not edit file contents. References to removed
  submodules in `.gitmodules`, system lists in `sorc/build_all.sh`/`sorc/build_opts.yaml`, and
  mentions of other systems in shared documentation remain until the content is refactored.
* The lists were derived from the GCAFS applications (`dev/workflow/applications/gcafs_*.py`), the
  job cards, and the job-to-script chain. Optional features that GCAFS does not enable by default
  (waves, ocean and ice components) are treated as unused. Validate each tier by building
  the workflow and running the GCAFS CI cases (`dev/ci/cases/pr/C96_gcafs_cycled*.yaml`) on the
  filtered tree.
* The filter syntax was written against the documented JOSH `:exclude[::path,...]` form and has not
  been run with `josh-filter` in this environment.
