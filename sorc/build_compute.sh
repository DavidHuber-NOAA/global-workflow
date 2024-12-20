#!/usr/bin/env bash

function _usage() {
  cat << EOF
Builds all of the global-workflow components on compute nodes.

Usage: ${BASH_SOURCE[0]} [-h][-v][-A <hpc-account>][-s gfs,gefs,sfs,all]
  -h:
    Print this help message and exit
  -v:
    Verbose mode (this script only)
  -A:
    HPC account to use for the compute-node builds
    (default is \$HOMEgfs/ci/platforms/config.\$machine:\$HPC_ACCOUNT)
  -s:
    Specify a system to build.  Valid options are "gfs", "gefs", "sfs", or "all".
    (default is "all")
EOF
  exit 1
}
# This script launches compute-node builds of selected submodules
# Two positional arguments are accepted:

set -eu

rocoto_verbose_opt=""
system="all"

while getopts ":A:vs:" option; do
  case "${option}" in
    h) _usage;;
    A) export HPC_ACCOUNT="${OPTARG}" ;;
    v) verbose_opt="-v" && rocoto_verbose_opt="-v10";;
    s) system="${OPTARG}" ;;
    :)
      echo "[${BASH_SOURCE[0]}]: ${option} requires an argument"
      _usage
      ;;
    *)
      echo "[${BASH_SOURCE[0]}]: Unrecognized option: ${option}"
      _usage
      ;;
  esac
done

# shellcheck disable=SC2155,SC2312
HOMEgfs=$(cd "$(dirname "$(readlink -f -n "${BASH_SOURCE[0]}" )" )/.." && pwd -P)
cd "${HOMEgfs}/sorc" || exit 1

export HPC_ACCOUNT=${1:?"A compute allocation needs to be specified"}

echo "Sourcing global-workflow modules ..."
source "${HOMEgfs}/workflow/gw_setup.sh"

echo "Generating build.xml for building global-workflow programs on compute nodes ..."
set +e
${HOMEgfs}/workflow/build_compute.py --yaml ${HOMEgfs}/workflow/build_opts.yaml --system ${system}
rc=$?
if (( rc != 0 )); then
  echo "FATAL ERROR: ${BASH_SOURCE[0]} failed to create 'build.xml' with error code ${rc}"
  exit 1
fi

echo "Launching builds in parallel on compute nodes ..."
finished=false
rocotorun -w build.xml -d build.db
while [[ "${finished}" == "false" ]]; do
   sleep 3m
   state="$("${HOMEgfs}/ci/scripts/utils/rocotostat.py" -w build.xml -d build.db)"
   echo "Rocoto is in state ${state}"
   if [[ "${state}" == "DONE" ]]; then
      finished=true
   elif [[ "${state}" == "RUNNING" ]]; then
      finished=false
   elif [[ "${state}" == "DEAD" ]]; then
      echo "FATAL ERROR: ${BASH_SOURCE[0]} one or more builds failed!"
      # TODO add capability to determine which build(s) failed
      exit 2
   else
      echo "FATAL ERROR: ${BASH_SOURCE[0]} rocoto failed with state '${state}'"
      exit 3
   fi
done

echo "All builds completed successfully!"

exit 0
