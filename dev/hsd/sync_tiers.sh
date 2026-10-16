#!/usr/bin/env bash
# Bring changes made in a higher (more filtered) tier back into a lower tier using the JOSH round trip.
#
# Run this from a checkout of the TARGET (lower tier) repository:
#
#   sync_tiers.sh [-b TARGET_BRANCH] [-o NEW_BRANCH] [-n] SYSTEM FROM_TIER TO_TIER SOURCE [SOURCE_BRANCH]
#
#   SYSTEM         forecasting system the tiers belong to (e.g., gcafs)
#   FROM_TIER      tier the changes were made in: 1, 1.5 or 2
#   TO_TIER        tier of this repository, lower than FROM_TIER (0, 1 or 1.5)
#   SOURCE         path or URL of the FROM_TIER repository
#   SOURCE_BRANCH  branch of SOURCE holding the changes (default: develop)
#   -b             branch of this repository the changes are based on (default: develop)
#   -o             name of the branch to create with the changes (default: hsd/SYSTEM-tierFROM-TIMESTAMP)
#   -n             only check; do not create the branch
#
# The FROM_TIER view of -b is compared with SOURCE_BRANCH, and the commits SOURCE_BRANCH has on top of
# it are re-applied (reverse filter) onto -b as a new branch. -b itself is never modified; review the new
# branch and merge it (or open a pull request). To go up several tiers run the script once per step,
# or go straight to the lower tier: the FROM_TIER filter works on any lower tier (e.g., tier 2 -> tier 0).
#
# Requires josh-filter (cargo install josh-cli --locked).

set -eu

usage() {
  sed -n '2,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 1
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

target_branch="develop"
new_branch=""
check_only="NO"
while getopts ":b:o:nh" opt; do
  case "${opt}" in
    b) target_branch="${OPTARG}" ;;
    o) new_branch="${OPTARG}" ;;
    n) check_only="YES" ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -ge 4 && $# -le 5 ]] || usage

system="$1"
from_tier="$2"
to_tier="$3"
source_repo="$4"
source_branch="${5:-develop}"

hsd_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
top_dir="$(git -C "${hsd_dir}" rev-parse --show-toplevel)"
cd "${top_dir}"

command -v josh-filter > /dev/null || die "josh-filter not found (cargo install josh-cli --locked)"

# Sets "rank" to the position of tier $1 in the hierarchy
set_rank() {
  case "$1" in
    0) rank=0 ;;
    1) rank=1 ;;
    1.5) rank=2 ;;
    2) rank=3 ;;
    *) die "Unknown tier '$1' (use 0, 1, 1.5 or 2)" ;;
  esac
}
set_rank "${from_tier}"
from_rank="${rank}"
set_rank "${to_tier}"
to_rank="${rank}"
[[ "${from_rank}" -gt "${to_rank}" ]] || die "FROM_TIER (${from_tier}) must be a higher tier than TO_TIER (${to_tier})"
[[ "${from_rank}" -gt 0 ]] || die "Tier 0 has no filter to reverse"

git rev-parse --verify --quiet "refs/heads/${target_branch}" > /dev/null || die "Branch '${target_branch}' does not exist here"
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || die "Working tree has uncommitted changes"

if [[ -z "${new_branch}" ]]; then
  new_branch="hsd/${system}-tier${from_tier}-$(date +%Y%m%d%H%M%S)"
fi
if [[ "${check_only}" == "NO" ]]; then
  git rev-parse --verify --quiet "refs/heads/${new_branch}" > /dev/null && die "Branch '${new_branch}' already exists"
fi

# The FROM_TIER filter is valid on every lower tier: paths a lower tier already lacks are simply absent
filter="$("${hsd_dir}/make_filter.sh" "${system}" "${from_tier}")"
incoming_ref="refs/hsd/incoming/${system}-tier${from_tier}"
base_ref="refs/hsd/base/${system}-tier${from_tier}"
check_ref="refs/hsd/check/${system}-tier${from_tier}"

echo "Fetching ${source_branch} from ${source_repo} ..."
git fetch --quiet --force "${source_repo}" "${source_branch}:${incoming_ref}"

echo "Projecting ${target_branch} to tier ${from_tier} ..."
josh-filter --update "${base_ref}" "${filter}" "refs/heads/${target_branch}" > /dev/null
base_tip="$(git rev-parse "${base_ref}")"
incoming_tip="$(git rev-parse "${incoming_ref}")"

if [[ "${base_tip}" == "${incoming_tip}" ]]; then
  echo "Nothing to do: ${source_branch} has no changes relative to ${target_branch}."
  exit 0
fi
merge_base="$(git merge-base "${base_ref}" "${incoming_ref}" || true)"
[[ -n "${merge_base}" ]] || die "${source_branch} shares no history with ${target_branch} as seen from tier ${from_tier}. \
Was the tier ${from_tier} repository created from this repository with the same filter?"
if [[ "${merge_base}" != "${base_tip}" ]]; then
  echo "NOTE: ${target_branch} has changes since ${source_repo} was created; the new branch is based on the older commit and needs a merge."
fi

echo "Reverse-applying the tier ${from_tier} commits ..."
work_branch="hsd-sync-work-$$"
trap 'git branch -q -D "${work_branch}" > /dev/null 2>&1 || true' EXIT
# Start from the commit of the target that the tier repository was created from, so that changes
# made on the target since then do not stop the reverse apply (they are merged by the user afterwards).
start_commit="${target_branch}"
if [[ "${merge_base}" != "${base_tip}" ]]; then
  start_commit=""
  while read -r commit; do
    josh-filter --update "${check_ref}" "${filter}" "${commit}" > /dev/null
    if [[ "$(git rev-parse "${check_ref}")" == "${merge_base}" ]]; then
      start_commit="${commit}"
      break
    fi
  done < <(git rev-list "refs/heads/${target_branch}")
  [[ -n "${start_commit}" ]] || die "Could not find the commit of ${target_branch} that ${source_repo} was created from"
fi
git branch -q "${work_branch}" "${start_commit}"
josh-filter --reverse --update "${incoming_ref}" "${filter}" "refs/heads/${work_branch}" > /dev/null \
  || die "josh-filter could not reverse-apply the changes"

# Round trip: projecting the result must give back exactly what the tier repository has
josh-filter --update "${check_ref}" "${filter}" "refs/heads/${work_branch}" > /dev/null
if [[ "$(git rev-parse "${check_ref}^{tree}")" != "$(git rev-parse "${incoming_ref}^{tree}")" ]]; then
  git diff --stat "${check_ref}" "${incoming_ref}" | tail -20 >&2 || true
  die "Round trip check failed: some changes in ${source_branch} fall outside the tier ${from_tier} view \
(for example, files added under a path that tier ${from_tier} excludes) and cannot be applied."
fi

echo
echo "Changes that would be applied to ${target_branch} (tier ${to_tier}):"
git diff --stat "${start_commit}" "${work_branch}" | tail -30

if [[ "${check_only}" == "YES" ]]; then
  echo "Check only: no branch created."
  exit 0
fi
git branch -q "${new_branch}" "${work_branch}"
echo
echo "Created branch '${new_branch}' in ${top_dir}. Review, then merge it into ${target_branch} or push it for a pull request."
