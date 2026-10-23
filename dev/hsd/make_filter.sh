#!/usr/bin/env bash
# Build a JOSH filter specification for a tier of the hierarchical system design (HSD).
#
# Usage: make_filter.sh SYSTEM TIER
#   SYSTEM  forecasting system (currently only "gcafs")
#   TIER    0, 1, 1.5 or 2
#
# The filter excludes the paths in the tier lists. Symbolic links that are kept but whose target is excluded
# (for example dev/parm/config/gcafs/config.X -> ../gfs/config.X when dev/parm/config/gfs is excluded) would
# dangle, so the filter is a "mapped" filter: the link is dropped and the target file is placed at the link's
# path. Edits to such a file in a tier repository are applied to the target (and the link is kept) by the
# reverse filter. Only links to regular files with the same name as the link are mapped.
#
# Example: josh-filter "$(./make_filter.sh gcafs 2)" HEAD

set -eu

usage() {
  sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 1
}

[[ $# -eq 2 ]] || usage

system="$1"
tier="$2"
hsd_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
top_dir="$(cd "${hsd_dir}/../.." && pwd)"

case "${tier}" in
  0) tiers=() ;;
  1) tiers=(tier1) ;;
  1.5) tiers=(tier1 tier1p5) ;;
  2) tiers=(tier1 tier1p5 tier2) ;;
  *) echo "Unknown tier '${tier}'" >&2; usage ;;
esac

patterns=()
entries=()
for t in "${tiers[@]}"; do
  list="${hsd_dir}/${system}.${t}.list"
  [[ -f "${list}" ]] || { echo "Missing list ${list}" >&2; exit 1; }
  while IFS= read -r line; do
    [[ -z "${line}" || "${line}" == \#* ]] && continue
    patterns+=("${line}")
    # Directories need a trailing slash; submodules (gitlinks) must not have one
    if [[ -d "${top_dir}/${line}" ]] && ! git -C "${top_dir}" ls-files -s -- "${line}" | grep -q '^160000'; then
      line="${line}/"
    fi
    entries+=("::${line}")
  done < "${list}"
done

if [[ ${#entries[@]} -eq 0 ]]; then
  echo ":/"
  exit 0
fi

# Returns 0 if the path (or a parent directory) is matched by an entry of the tier lists
is_excluded() {
  local path="$1" pattern
  for pattern in "${patterns[@]}"; do
    # shellcheck disable=SC2053
    if [[ "${path}" == ${pattern} || "${path}" == ${pattern}/* ]]; then
      return 0
    fi
  done
  return 1
}

# Find kept links whose target is excluded; group the target files by (source dir, destination dir)
declare -A groups=()
while read -r mode _ _ link; do
  [[ "${mode}" == "120000" ]] || continue
  is_excluded "${link}" && continue
  target="$(git -C "${top_dir}" cat-file -p ":${link}")"
  resolved="$(realpath -m "/$(dirname "${link}")/${target}")"
  resolved="${resolved#/}"
  is_excluded "${resolved}" || continue
  target_mode="$(git -C "${top_dir}" ls-files -s -- "${resolved}" | awk '{print $1}')"
  if [[ "${target_mode}" != "100644" && "${target_mode}" != "100755" ]]; then
    echo "WARNING: ${link} -> ${target} points to an excluded path that is not a regular file; it is left as a (dangling) link" >&2
    continue
  fi
  if [[ "$(basename "${resolved}")" != "$(basename "${link}")" ]]; then
    echo "ERROR: ${link} -> ${target} has a different file name; the mapping needs the same name" >&2
    exit 1
  fi
  key="$(dirname "${resolved}")|$(dirname "${link}")"
  groups["${key}"]+="${groups[${key}]:+,}::$(basename "${link}")"
done < <(git -C "${top_dir}" ls-files -s | sort -k4)

# Links that are mapped must also be excluded in their original form (the target file replaces them)
mapped=()
for key in "${!groups[@]}"; do
  src="${key%%|*}"
  dest="${key##*|}"
  mapped+=(":/${src}:[${groups[${key}]}]:prefix=${dest}")
  IFS=, read -r -a names <<< "${groups[${key}]}"
  for name in "${names[@]}"; do
    entries+=("::${dest}/${name#::}")
  done
done

if [[ ${#mapped[@]} -eq 0 ]]; then
  (IFS=,; echo ":exclude[${entries[*]}]")
else
  (IFS=,; echo ":[:exclude[${entries[*]}],${mapped[*]}]")
fi
