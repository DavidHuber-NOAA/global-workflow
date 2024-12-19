#! /usr/bin/env bash

source "${HOMEgfs}/ush/preamble.sh"

export job="compile_${BUILD}"
export jobid="${job}.$$"

###############################################################
# Execute the JJOB
"${HOMEgfs}/jobs/JBUILD_COMPILE"
status=$?
exit "${status}"
