#!/usr/bin/env bash
# Prepare the branch to publish as `develop` of a tier repository, bridging over filter changes.
#
# Run this from the Tier 0 (full) repository:
#
#   publish_tier.sh [-b BRANCH] [-p PUBLISHED] [-q PUBLISHED_BRANCH] [-o OUT_BRANCH] [-n] SYSTEM TIER
#
#   SYSTEM           forecasting system (e.g., gcafs)
#   TIER             tier to publish: 1, 1.5 or 2
#   -b               Tier 0 branch to filter (default: develop)
#   -p               path or URL of the published tier repository (omit for the very first publish)
#   -q               branch of PUBLISHED that holds the tier develop (default: develop)
#   -o               name of the local branch to create (default: hwd/publish/SYSTEM-tierTIER-TIMESTAMP)
#   -n               only report what would be done
#
# The filtered history is rewritten whenever the filter lists change, so the new filtered develop no longer
# contains the commits of the published develop, and feature branches (and forks) cannot merge it. When
# that happens this script creates a BRIDGE commit: a merge whose first parent is the published develop and
# whose second parent is the new filtered develop, with the tree of the filtered develop. The result is a
# descendant of the published develop, so it is a plain fast-forward push:
#
#   git push PUBLISHED OUT_BRANCH:develop
#
# and `git merge develop` works in every existing branch and fork. If the published develop is already an
# ancestor of the filtered develop (the filter did not change) no bridge is needed and the result is the
# filtered develop itself. Bridge commits carry the trailer "HWD-Bridge:"; sync_tiers.sh recognizes them (and the older "HSD-Bridge:" trailer).
#
# Before publishing, bring all changes made in the tier repository back to Tier 0 with sync_tiers.sh: the
# bridge takes the tree of the filtered Tier 0 branch, so anything only present in the tier repository
# would be dropped from the tree (the diff stat is printed so this can be checked).
#
# Requires josh-filter (cargo install josh-cli --locked).

set -eu

usage() {
  sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 1
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

branch="develop"
published=""
published_branch="develop"
out_branch=""
check_only="NO"
while getopts ":b:p:q:o:nh" opt; do
  case "${opt}" in
    b) branch="${OPTARG}" ;;
    p) published="${OPTARG}" ;;
    q) published_branch="${OPTARG}" ;;
    o) out_branch="${OPTARG}" ;;
    n) check_only="YES" ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -eq 2 ]] || usage
system="$1"
tier="$2"
[[ "${tier}" != "0" ]] || die "Tier 0 is not filtered; there is nothing to publish"

hwd_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
top_dir="$(git -C "${hwd_dir}" rev-parse --show-toplevel)"
cd "${top_dir}"
command -v josh-filter > /dev/null || die "josh-filter not found (cargo install josh-cli --locked)"
git rev-parse --verify --quiet "refs/heads/${branch}" > /dev/null || die "Branch '${branch}' does not exist here"

filter="$("${hwd_dir}/make_filter.sh" "${system}" "${tier}")"
filtered_ref="refs/hwd/publish/${system}-tier${tier}"
published_ref="refs/hwd/published/${system}-tier${tier}"
[[ -n "${out_branch}" ]] || out_branch="hwd/publish/${system}-tier${tier}-$(date +%Y%m%d%H%M%S)"
if [[ "${check_only}" == "NO" ]]; then
  git rev-parse --verify --quiet "refs/heads/${out_branch}" > /dev/null && die "Branch '${out_branch}' already exists"
fi

echo "Filtering ${branch} to tier ${tier} ..."
josh-filter --update "${filtered_ref}" "${filter}" "refs/heads/${branch}" > /dev/null
filtered_tip="$(git rev-parse "${filtered_ref}")"

result=""
if [[ -z "${published}" ]]; then
  echo "No published repository given: first publish."
  result="${filtered_tip}"
else
  echo "Fetching ${published_branch} from ${published} ..."
  git fetch --quiet --force "${published}" "${published_branch}:${published_ref}"
  published_tip="$(git rev-parse "${published_ref}")"
  if [[ "${published_tip}" == "${filtered_tip}" ]]; then
    echo "Nothing to do: the published ${published_branch} is already up to date."
    exit 0
  elif git merge-base --is-ancestor "${filtered_tip}" "${published_tip}"; then
    echo "Nothing to do: the published ${published_branch} already contains the filtered ${branch}."
    exit 0
  elif git merge-base --is-ancestor "${published_tip}" "${filtered_tip}"; then
    echo "The filter did not change history: fast-forward, no bridge needed."
    result="${filtered_tip}"
  else
    echo "The filtered history no longer contains the published ${published_branch} (the filter changed): creating a bridge."
    echo
    echo "Differences between the published tree and the new tree:"
    git diff --stat "${published_tip}" "${filtered_tip}" | tail -25
    echo
    if [[ "${check_only}" == "YES" ]]; then
      echo "Check only: no branch created."
      exit 0
    fi
    result="$(git commit-tree "${filtered_tip}^{tree}" -p "${published_tip}" -p "${filtered_tip}" -F - << MSG
HWD bridge: ${system} tier ${tier} filter update

Joins the published history with the history filtered by the current lists
so that existing branches and forks can merge this branch.

HWD-Bridge: ${system} tier ${tier}
MSG
    )"
  fi
fi

if [[ "${check_only}" == "YES" ]]; then
  echo "Check only: would publish $(git log -1 --format='%h %s' "${result}")"
  exit 0
fi
git branch -q "${out_branch}" "${result}"
echo "Created branch '${out_branch}' at $(git log -1 --format='%h %s' "${result}")."
if [[ -n "${published}" ]]; then
  echo "Publish it (a fast-forward) with:  git push ${published} ${out_branch}:${published_branch}"
else
  echo "Create the tier repository from it:  git init -b develop NEW && cd NEW && git fetch ${top_dir} ${out_branch} && git checkout -B develop FETCH_HEAD"
fi
