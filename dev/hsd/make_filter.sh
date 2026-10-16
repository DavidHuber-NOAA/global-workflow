#!/usr/bin/env bash
# Build a JOSH filter specification for a tier of the hierarchical system design (HSD).
#
# Usage: make_filter.sh SYSTEM TIER
#   SYSTEM  forecasting system (currently only "gcafs")
#   TIER    0, 1, 1.5 or 2
#
# Example: josh-filter "$(./make_filter.sh gcafs 2)" HEAD

set -eu

usage() {
  sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
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

entries=()
for t in "${tiers[@]}"; do
  list="${hsd_dir}/${system}.${t}.list"
  [[ -f "${list}" ]] || { echo "Missing list ${list}" >&2; exit 1; }
  while IFS= read -r line; do
    [[ -z "${line}" || "${line}" == \#* ]] && continue
    if [[ -d "${top_dir}/${line}" ]]; then line="${line}/"; fi
    entries+=("::${line}")
  done < "${list}"
done

if [[ ${#entries[@]} -eq 0 ]]; then
  echo ":/"
else
  (IFS=,; echo ":exclude[${entries[*]}]")
fi
