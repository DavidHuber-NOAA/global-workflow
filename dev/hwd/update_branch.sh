#!/usr/bin/env bash
# Move a feature branch of a filtered (tier) repository onto a develop whose filter has changed.
#
# When the filter lists change, `josh-filter` rewrites the history of the tier repository, so the new
# develop shares no commits with the old one and `git merge develop` fails with "refusing to merge
# unrelated histories". This script finds the commit of the old develop that the feature branch was
# started from and replays only the branch's own commits on top of the new develop (git rebase --onto).
#
#   update_branch.sh [-r REMOTE] [-d DEVELOP] [-o OLD_BASE] [-n] [BRANCH]
#
#   BRANCH   branch to update (default: the current branch)
#   -r       remote that holds the new develop (default: origin)
#   -d       name of the develop branch (default: develop)
#   -o       commit of the OLD develop the branch was started from (default: detected automatically)
#   -n       only report what would happen
#
# Run it from the tier repository. Afterwards push with `git push --force-with-lease`.

set -eu

usage() {
  sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 1
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

remote="origin"
develop="develop"
old_base=""
dry_run="NO"
while getopts ":r:d:o:nh" opt; do
  case "${opt}" in
    r) remote="${OPTARG}" ;;
    d) develop="${OPTARG}" ;;
    o) old_base="${OPTARG}" ;;
    n) dry_run="YES" ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -le 1 ]] || usage

branch="${1:-$(git symbolic-ref --quiet --short HEAD || true)}"
[[ -n "${branch}" ]] || die "Not on a branch; give the branch name"
git rev-parse --verify --quiet "refs/heads/${branch}" > /dev/null || die "Branch '${branch}' does not exist"
[[ "${branch}" != "${develop}" ]] || die "Refusing to update ${develop} itself"
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || die "Working tree has uncommitted changes; commit or stash them first"
[[ ! -d "$(git rev-parse --git-dir)/rebase-merge" && ! -d "$(git rev-parse --git-dir)/rebase-apply" ]] \
  || die "A rebase is already in progress (git rebase --continue, or --abort)"

# Remember where the old develop was BEFORE fetching moves it
remote_ref="refs/remotes/${remote}/${develop}"
old_tips=()
for ref in "${remote_ref}" "refs/heads/${develop}"; do
  git rev-parse --verify --quiet "${ref}" > /dev/null && old_tips+=("$(git rev-parse "${ref}")")
done

echo "Fetching ${develop} from ${remote} ..."
git fetch --quiet "${remote}" "${develop}"
new_tip="$(git rev-parse "${remote_ref}")"

if git merge-base "${branch}" "${new_tip}" > /dev/null 2>&1; then
  echo "${branch} shares history with ${remote}/${develop}: the filter did not change for this branch."
  echo "Update it normally:  git merge ${remote}/${develop}"
  exit 0
fi

# Older positions of the remote develop are still in the reflog (and may be a local develop)
while read -r sha; do
  old_tips+=("${sha}")
done < <(git reflog show --format=%H "${remote_ref}" 2> /dev/null || true)
while read -r sha; do
  old_tips+=("${sha}")
done < <(git reflog show --format=%H "refs/heads/${develop}" 2> /dev/null || true)

if [[ -z "${old_base}" ]]; then
  # The base is the newest fork point of the branch with any earlier develop
  best=""
  best_time=0
  for tip in "${old_tips[@]}"; do
    [[ "${tip}" != "${new_tip}" ]] || continue
    fork="$(git merge-base "${branch}" "${tip}" 2> /dev/null || true)"
    [[ -n "${fork}" ]] || continue
    when="$(git log -1 --format=%ct "${fork}")"
    if [[ "${when}" -gt "${best_time}" ]]; then
      best="${fork}"
      best_time="${when}"
    fi
  done
  [[ -n "${best}" ]] || die "Could not find the old ${develop} this branch was started from. \
Find it with 'git log --first-parent ${branch}' and pass it with -o COMMIT."
  old_base="${best}"
fi
git rev-parse --verify --quiet "${old_base}^{commit}" > /dev/null || die "Old base '${old_base}' is not a commit"
git merge-base --is-ancestor "${old_base}" "${branch}" || die "Old base ${old_base} is not part of ${branch}"

count="$(git rev-list --count "${old_base}..${branch}")"
echo "Old develop commit : $(git log -1 --format='%h %s' "${old_base}")"
echo "New develop        : $(git log -1 --format='%h %s' "${new_tip}")"
echo "Commits to replay  : ${count}"
git log --oneline "${old_base}..${branch}" | head -20

if [[ "${dry_run}" == "YES" ]]; then
  echo "Dry run: nothing changed."
  exit 0
fi

backup="${branch}-before-filter-update"
git branch -f "${backup}" "${branch}"
echo "Saved the current branch as '${backup}'."
echo "Replaying onto ${remote}/${develop} ..."
git checkout --quiet "${branch}"
if git rebase --onto "${new_tip}" "${old_base}" "${branch}"; then
  echo
  echo "Done. ${branch} is now based on ${remote}/${develop}."
  echo "Push with:  git push --force-with-lease ${remote} ${branch}"
else
  echo
  echo "Conflicts: resolve them, then 'git add' the files and 'git rebase --continue'"
  echo "(or 'git rebase --abort' to go back; '${backup}' keeps the original branch)."
  exit 1
fi
