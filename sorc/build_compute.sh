#!/usr/bin/env bash

set -eu

# shellcheck disable=SC2155,SC2312
HOMEgfs=$(cd "$(dirname "$(readlink -f -n "${BASH_SOURCE[0]}" )" )/.." && pwd -P)
cd "${HOMEgfs}/sorc" || exit 1

export HPC_ACCOUNT=${1:?"A compute allocation is required to be specified"}

echo "Sourcing global-workflow modules ..."
source "${HOMEgfs}/workflow/gw_setup.sh"

echo "Generating build.xml for building global-workflow programs on compute nodes ..."
${HOMEgfs}/workflow/build_compute.py --yaml ${HOMEgfs}/workflow/build_opts.yaml
rc=$?
if (( rc != 0 )); then
  echo "FATAL ERROR: ${BASH_SOURCE[0]} failed to create 'build.xml'"
fi

echo "Launching builds in parallel on compute nodes ..."
rocotorun -v 10 -w build.xml -d build.db

exit 0
