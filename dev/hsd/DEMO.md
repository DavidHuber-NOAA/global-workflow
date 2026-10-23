# HSD demonstration: a GCAFS Tier 1 repository and a round-trip pull request

This walks through the whole HSD life cycle with one small feature,
[NOAA-EMC/global-workflow#4393](https://github.com/NOAA-EMC/global-workflow/issues/4393)
("Run product jobs on the WCOSS2 prepost nodes"). Every command was run end to end on a copy of this repository
(single-commit history); the outputs shown are from that run.

| Step | What | Where | Cadence | Who |
|------|------|-------| ------- | -----|
| 0 | Prerequisite installations | On your machine | One-time | EPIC |
| 1 | Create the Tier 1 GCAFS filter | full (Tier 0) clone | One-time | EPIC/Core Developer |
| 2 | Create the Tier 1 GCAFS repository | new directory | One-time | EPIC/OMD |
| 3 | Make the change (issue 4393) | Tier 1 repository | As needed | Developer |
| 4 | Round-trip the change into a Tier 0 pull request | full (Tier 0) clone | Once per PR | EPIC/Developer |

```
 +-----------------+       josh-filter (step 1-2)       +-------------------+
 |  Tier 0 (full)  | ---------------------------------> | Tier 1 GCAFS repo |
 +-----------------+                                    +-------------------+
      ^                                                           |
      | pull request                                              | branch out
      |                                                           v
 +-----------------+                                    +-------------------+
 | hsd/... branch  |                                    |  feature branch   |
 +-----------------+                                    |     (step 3)      |
      ^                                                 +-------------------+
      |             dev/hsd/sync_tiers.sh (step 4)                |
      +-----------------------------------------------------------+
```

## Step 0: prerequisite installations

```bash
# Assumes Python 3.8+ and git 2.30+ are already installed.
# Install Rust (https://www.rust-lang.org/tools/install) and add it to your PATH.
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
export PATH="${HOME}/.cargo/bin:${PATH}"
# Add the cargo bin directory to your PATH in .bashrc or .zshrc for future sessions.
# josh-filter (Rust). Use --locked; without it the build fails on a yanked dependency.
cargo install josh-cli --locked
josh-filter --version

# A FULL (not shallow) clone of the Tier 0 repository. JOSH cannot filter shallow clones.
git clone --recurse-submodules=no https://github.com/NOAA-EMC/global-workflow.git global-workflow
cd global-workflow
git checkout develop
```

## Step 1: create the Tier 1 GCAFS filter

```bash
# Sanity check the exclude lists against the tracked files (Tier 0 only)
python3 dev/hsd/check_lists.py
#   tier 1: 1493 files excluded, 765 kept; 2 submodules excluded, 8 kept
#   tier 1.5: 1578 files excluded, 680 kept; 2 submodules excluded, 8 kept
#   tier 2: 1676 files excluded, 582 kept; 4 submodules excluded, 6 kept

# Print the JOSH filter (an ":exclude[...]" string built from dev/hsd/gcafs.tier1.list)
FILTER="$(dev/hsd/make_filter.sh gcafs 1)"
echo "${FILTER}"

# Project develop through the filter into a local branch
josh-filter --update refs/heads/gcafs-tier1 "${FILTER}" HEAD
git ls-tree -r --name-only gcafs-tier1 | wc -l     # 765
```

Other tiers: `make_filter.sh gcafs 1.5` (no production code) and `make_filter.sh gcafs 2` (forecast-only).

## Step 2: create the Tier 1 repository

```bash
### Go to GitHub and create a new repository named `global-workflow-gcafs` (no README, no license, no gitignore).
git remote add gw-gcafs git@github.com:<ORG>/global-workflow-gcafs.git
# Push the filtered branch to the new repository as `develop`
git push origin gcafs-tier1:develop
cd ..
git clone git@github.com:<ORG>/global-workflow-gcafs.git gcafs-tier1
cd gcafs-tier1

# Tier 1 only builds what it contains
sorc/build_all.sh -h | head          # lists only: gcafs
```

Notes:

* `.gitmodules` is a file and cannot be edited by a filter, so it still lists every submodule. Git ignores entries
  with no matching gitlink. Do **not** prune it on a branch you plan to round-trip (the removal would be sent
  back to Tier 0).
* Build systems and workflow generators are discovered dynamically (`sorc/build_systems/*.yaml`, the factory
  registration in `dev/workflow`), so no other file needs editing in the filtered repository.

## Step 3: make the change (issue 4393)

The issue asks that product jobs on WCOSS2 request `prepost=true` in the PBS select string
(`-l select=1:mpiprocs=24:ompthreads=1:ncpus=24:mem=6GB:prepost=true`), for PBS on WCOSS2 only, with Slurm
unchanged. `dev/workflow/rocoto/tasks.py` already appends `:prepost=true` to the memory request when a task has
`prepost` set, so the change for GCAFS is in the resource configuration: `atmos_products` sets
`prepost=True`, a non-exclusive allocation and an explicit memory request on WCOSS2.

```bash
git checkout -b feature/wcoss2-prepost-products
```

Edit `dev/parm/config/gcafs/config.resources`. In the `atmos_products` case add:

```bash
    export is_exclusive=True
    # Run on the shared prepost nodes, which require an explicit memory request
    memory="6GB"
    prepost=True
```

Add a unit test to `dev/workflow/tests/test_tasks.py` (`test_prepost_resources`: PBS with `prepost` gives
`memory == '6GB:prepost=true'` and a shared allocation, PBS without it and Slurm are unchanged).
The complete diff is in this branch's history: `git log -p -- dev/parm/config/gcafs/config.resources`.

Test and commit:

```bash
(cd dev/workflow && python3 -m pytest tests/test_tasks.py -q)    # 3 passed

# Check the resources by hand (WCOSS2 vs another machine)
for m in WCOSS2 HERA; do
  (export machine=${m} EXPDIR=$(pwd)/dev/parm/config/gcafs CASE=C96 RUN=gcafs max_tasks_per_node=128
   bash -c 'source dev/parm/config/gcafs/config.resources atmos_products >/dev/null
            echo "'"${m}"': memory=${memory:-} exclusive=${is_exclusive} prepost=${prepost:-}"')
done
#   WCOSS2: memory=6GB exclusive=False prepost=True
#   HERA:   memory=    exclusive=True  prepost=

git add -A
git commit -m "Run GCAFS atmos_products on the WCOSS2 prepost nodes (#4393)"
```

The change only touches files kept at Tier 1, which is required for the round trip.

## Step 4: round trip into a Tier 0 pull request

Run `sync_tiers.sh` from the **Tier 0** clone (the repository that receives the change):

```bash
cd ../global-workflow
git checkout develop
git pull                                    # keep the target current

dev/hsd/sync_tiers.sh -n gcafs 1 0 ../gcafs-tier1 feature/wcoss2-prepost-products   # check only
dev/hsd/sync_tiers.sh    gcafs 1 0 ../gcafs-tier1 feature/wcoss2-prepost-products
#   Changes that would be applied to develop (tier 0):
#    dev/parm/config/gcafs/config.resources |  9 ++++++++-
#    dev/workflow/tests/test_tasks.py       | 35 ++++++++++++++++++++++++++++++++++
#   Created branch 'hsd/gcafs-tier1-<timestamp>' ...

git log --oneline -3 hsd/gcafs-tier1-*      # the same commit, now on the full history
git push origin hsd/gcafs-tier1-<timestamp>
gh pr create --base develop --head hsd/gcafs-tier1-<timestamp> \
  --title "Run GCAFS atmos_products on the WCOSS2 prepost nodes (#4393)" \
  --body "Created in the GCAFS Tier 1 repository and brought back with dev/hsd/sync_tiers.sh. Closes #4393 for GCAFS."
```

A "reference refs/hsd/base/... wasn't updated" warning from JOSH is harmless.

If the change touches a file that Tier 1 does not contain, the tree check fails with an explanation and no branch
is created. If `develop` moved on since the Tier 1 repository was created, the branch is started from the commit
the Tier 1 repository was created from, and the pull request merges it.

## Slide summary (Steps 1-4; the appendix keeps the tier repository current)

1. `make_filter.sh gcafs 1` prints a JOSH exclude filter (about 1500 of 2250 files removed).
2. `josh-filter` rewrites history through it; a new repository is a `git fetch` of that branch.
3. Developers work in the small repository with normal git/PR tools.
4. `sync_tiers.sh` reverse-applies the commits onto the full history, producing a normal branch and PR.

Limits to mention: shallow clones are not supported; `.gitmodules` is not filtered; round trip fails (by design)
for changes outside the tier; the tier job classification (`dev/hsd/*.list`) needs review by system owners.

## Appendix: update `global-workflow-gcafs` after `global-workflow` develop changes

Run this whenever Tier 0 `develop` has moved (for example after the pull request from Step 4 was merged, or any
other change in the full repository). The published Tier 1 `develop` is updated with a fast-forward push, so
developers and forks of `global-workflow-gcafs` can simply `git merge develop` / "Sync fork".
It uses `dev/hsd/publish_tier.sh`, which adds a bridge commit only when the filter lists changed.

```bash
# 1. Update the Tier 0 clone (the full repository)
cd global-workflow
git checkout develop
git pull

# 2. Check that the filter lists still match the repository (new or removed files)
python3 dev/hsd/check_lists.py

# 3. Bring any pending Tier 1 changes back to Tier 0 first (otherwise they are overwritten by the update)
#    Skip if there are none; see Step 4. Check only:
dev/hsd/sync_tiers.sh -n gcafs 1 0 git@github.com:<ORG>/global-workflow-gcafs.git develop

# 4. Preview the update against the published Tier 1 develop (nothing is created)
dev/hsd/publish_tier.sh -n -p git@github.com:<ORG>/global-workflow-gcafs.git gcafs 1
#   Filtering develop to tier 1 ...
#   Fetching develop from git@github.com:<ORG>/global-workflow-gcafs.git ...
#   The filter did not change history: fast-forward, no bridge needed.       (list unchanged)
#   -- or --
#   The filtered history no longer contains the published develop (the filter changed): creating a bridge.

# 5. Create the branch to publish
dev/hsd/publish_tier.sh -p git@github.com:<ORG>/global-workflow-gcafs.git gcafs 1
#   Created branch 'hsd/publish/gcafs-tier1-<timestamp>' ...

# 6. Publish it (always a fast-forward; never use --force)
git push git@github.com:<ORG>/global-workflow-gcafs.git hsd/publish/gcafs-tier1-<timestamp>:develop

# 7. Update local clones as normal (fast-forward, with or without a bridge)
cd ../global-workflow-gcafs
git checkout develop
git pull
```

What happens in step 5:

| Situation | Result |
|-----------|--------|
| Only Tier 0 commits were added, lists unchanged | The published `develop` is an ancestor of the filtered history: the new commits are fast-forwarded |
| Lists changed (for example a new script must go to Tier 1), or an earlier PR was squash-merged in Tier 0 | A bridge commit (first parent: published `develop`, second parent: new filtered `develop`, tree: the filtered tree) is created |
| Nothing changed | "Nothing to do" |

For developers of `global-workflow-gcafs` afterwards:

```bash
git checkout develop && git pull                 # fast-forward, with or without a bridge
git checkout my-feature && git merge develop     # works as usual
```

Only a branch that was never merged with a published `develop` and is based on a repository rewritten *without* a
bridge needs `dev/hsd/update_branch.sh`.

If the filter lists changed, change them in a Tier 0 pull request first and run steps 1-6 once it is merged;
mention the change in the pull request so Tier 1 developers know to pull.
