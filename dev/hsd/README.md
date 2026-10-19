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

## Dynamic system registration

Python code no longer imports every system explicitly, so a system's modules can be removed by listing them:

* `dev/workflow/applications/application_factory.py`, `dev/workflow/rocoto/{rocoto_xml_factory,tasks_factory}.py`
  and `dev/workflow/ecflowgw/ecflow_suite_factory.py` discover the modules in their package and register the
  classes defined there (`<System>[Cycled|ForecastOnly]AppConfig`, `...RocotoXML`, `...Tasks`, `...EcFlowSuite`).
  Only classes defined in the scanned module are registered, so imported base classes are never registered.
* `ush/python/pygfs/__init__.py` imports task classes lazily on first access.
* `dev/workflow/setup_workflow.py` imports the ecFlow factory only when `ecflow` is requested, so
  `dev/workflow/ecflowgw` can be removed at Tier 1.5.
* `sorc/link_workflow.sh` only links `jcb` when `sorc/gdas.cd` exists, so Tier 2 trees link cleanly.

To add a system: add its `applications/<sys>*.py`, `rocoto/<sys>_tasks.py`, `rocoto/<sys>*_xml.py` (and optionally
`ecflowgw/<sys>*_ecflow.py`) following the naming convention above; no other Python file needs editing.
Module file names must end in `tasks` / contain `xml` / end in `ecflow` to be scanned.

`dev/workflow/setup_expt.py` still builds its sub-parsers for all systems explicitly; in a filtered tree the
parsers of removed systems remain but fail when used because their config directories are gone.
`dev/workflow/workflow_suite.py` is a shared base class of the Rocoto and ecFlow generators and is kept at every tier.

## Verified with josh-filter

The filters were run with `josh-filter` (`cargo install josh-cli --locked`; the plain `josh-cli` install fails on
a yanked dependency). `josh-filter --single --update refs/josh/t2 "$(dev/hsd/make_filter.sh gcafs 2)" HEAD`
gives 758 / 673 / 577 files at Tiers 1 / 1.5 / 2 (`--single` is needed in shallow clones).
Submodules are gitlinks: JOSH only excludes them when the path has no trailing slash, which `make_filter.sh` handles.

## Pushing changes to a lower tier (round trip)

Work done in a filtered repository can be brought back with `sync_tiers.sh`, which uses `josh-filter --reverse`.
Run it from a checkout of the *lower tier* repository (for example the full repository for Tier 0):

```bash
cd gw-work                                   # the lower-tier repository, develop checked out
dev/hsd/sync_tiers.sh gcafs 2 0 ../gcafs-tier2 develop            # tier 2 -> tier 0
dev/hsd/sync_tiers.sh -o hsd/from-t2 gcafs 2 1.5 ../gcafs-tier2   # tier 2 -> tier 1.5, named branch
dev/hsd/sync_tiers.sh -n gcafs 2 0 ../gcafs-tier2                 # check only
```

Arguments are `SYSTEM FROM_TIER TO_TIER SOURCE [SOURCE_BRANCH]`. The tool fetches the branch, projects the local
`develop` (`-b` selects another) to the FROM tier, re-applies the commits the source has on top of it, and creates
a new branch (`-o`, default `hsd/<system>-tier<N>-<timestamp>`). The existing branch is never changed: review the
new branch, merge it or open a pull request. To go up one tier at a time, run it again from the next repository.

* The tier repository must have been created from the target with the same filter (`josh-filter` history), so that
  the histories share commits. Otherwise the tool stops with a "shares no history" error.
* If the target moved on since the tier repository was created, the new branch starts at the commit the tier
  repository was based on and you merge it into the target.
* A round-trip check projects the result again and requires it to equal the tier repository. It fails when a change
  falls outside the tier view, for example a file added under a path that the tier excludes; move such files first.
* Changes to `.gitmodules` and other files that only exist in the lower tier are not touched, because the filter
  removes whole paths only.

## Build systems

`sorc/build_all.sh` and `dev/workflow/setup_buildxml.py` discover systems from `sorc/build_systems/<system>.yaml`
(file name = system name). Each file has a `components` list and the `build` entries only that system uses; entries
shared by several systems (`gsi_utils`, `nexus`, ...) live in `sorc/build_opts.yaml` together with `host_override`,
`default_system` and the always-built `common` list. A tier removes a system by listing its file; the usage text,
the accepted system names and the `all` target follow automatically. A build entry may carry `requires:`, a list
of paths under `sorc/` (for example a submodule); an entry whose build script or required paths are missing is
skipped with a notice for `all` and is an error when its system is requested explicitly.

To add a system, add `sorc/build_systems/<system>.yaml`.

See [DEMO.md](DEMO.md) for an end-to-end walk-through (Tier 1 repository, a feature, round-trip PR).

## Checking the lists

```bash
dev/hsd/check_lists.py gcafs
```

reports list entries that match no tracked file, entries repeated across tiers, and kept Python files that
import an excluded module at module level. Run it whenever files are added, renamed or removed.

## Files that are created by `sorc/link_workflow.sh`

Several directories GCAFS needs are not tracked in this repository; `sorc/link_workflow.sh` creates
them as (git-ignored) symlinks into submodules, so they are available as long as the submodule is kept:

* `parm/gdas/{aero,atm,io,ioda,anlstat,analcalc,jcb-gdas,jcb-algorithms,spoc}` and `ush/python/jcb`
  come from `sorc/gdas.cd`, which is therefore kept at Tiers 1 and 1.5 (the tracked `parm/gdas/staging`
  only holds snow analysis templates and is the only part of `parm/gdas` removed).
* `parm/post/*`, `parm/ufs/*` templates and CCPP suites come from `sorc/upp.fd` and `sorc/ufs_model.fd`.
* `parm/chem/nexus` comes from `sorc/nexus.fd`.

At Tier 2 `sorc/gdas.cd` is removed; `link_workflow.sh` skips the links that need it.

Files that looked removable but are required by kept code were retained: `dev/workflow/aux`,
`ush/cpfsd.sh` and `ush/getdump.sh` (Tier 2 only), `ush/parse-storm-type.pl` (Tier 2 only),
`ush/wave_domain_grid.sh`, `ush/wave_extractvars.sh`, `ush/ocnice_extractvars.sh` (used by the
`extractvars` and archive jobs), and `dev/parm/config/gcafs/config.nsst` and `config.efcs`
(sourced by `config.fcst.j2`).

## Known limitations

* JOSH filters whole files and directories; it does not edit file contents. References to removed
  submodules in `.gitmodules` and
  mentions of other systems in shared documentation remain until the content is refactored.
* The lists were derived from the GCAFS applications (`dev/workflow/applications/gcafs_*.py`), the
  job cards, and the job-to-script chain. Optional features that GCAFS does not enable by default
  (waves, ocean and ice components) are treated as unused. Validate each tier by building
  the workflow and running the GCAFS CI cases (`dev/ci/cases/pr/C96_gcafs_cycled*.yaml`) on the
  filtered tree.
* The filter syntax was written against the documented JOSH `:exclude[::path,...]` form and has not
  been run with `josh-filter` in this environment.
