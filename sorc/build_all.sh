#! /usr/bin/env bash

set +x
#------------------------------------
# Exception handling is now included.
#
# USER DEFINED STUFF:
#
#------------------------------------

#------------------------------------
# END USER DEFINED STUFF
#------------------------------------
function _usage() {
  cat << EOF
Builds all of the global-workflow components by calling the individual build scripts in parallel.

Usage: ${BASH_SOURCE[0]} [-a UFS_app][-c build_config][-d][-f][-h][-j n][-v] [gfs] [gefs] [sfs] [gsi] [gdas]
  -a UFS_app:
    Build a specific UFS app instead of the default.  This will be applied to all UFS (GFS, GEFS, SFS) builds.
  -c:
    Submit the build jobs to compute nodes
  -d:
    Build in debug mode
  -f:
    Build the UFS model(s) using the -DFASTER=ON option.
  -h:
    Print this help message and exit
  -k:
    Kill all builds if any build fails
  -v:
    Execute all build scripts with -v option to turn on verbose where supported
  -A:
    HPC account to use for the compute-node builds
    (default is \$HOMEgfs/ci/platforms/config.\$machine:\$HPC_ACCOUNT)

  Specified systems (gfs, gefs, sfs, gsi, gdas) are non-exclusive, so they can be built together.
EOF
  exit 1
}

# shellcheck disable=SC2155
readonly HOMEgfs=$(cd "$(dirname "$(readlink -f -n "${BASH_SOURCE[0]}" )" )/.." && pwd -P)
cd "${HOMEgfs}/sorc" || exit 1

_build_ufs_opt=""
_build_debug=""
_verbose_opt=""
_build_job_max=20
_quick_kill="NO"
_compute_build="NO"
_hpc_account="default"
# Reset option counter in case this script is sourced
OPTIND=1
while getopts ":a:cdfhj:kA:v" option; do
  case "${option}" in
    a) _build_ufs_opt+="-a ${OPTARG} ";;
    c) _compute_build="YES" ;;
    f) _build_ufs_opt+="-f ";;
    d) _build_debug="-d" ;;
    h) _usage;;
    k) _quick_kill="YES" ;;
    A) _hpc_account="${OPTARG}"
    v) _verbose_opt="-v";;
    :)
      echo "[${BASH_SOURCE[0]}]: ${option} requires an argument"
      _usage
      ;;
    *)
      echo "[${BASH_SOURCE[0]}]: Unrecognized option: ${option}"
      _usage
      ;;
  esac
  shift $((OPTIND-1))
done

supported_systems=("gfs" "gefs" "sfs" "gsi" "gdas")
gfs_builds="gfs gfs_utils ufs_utils upp ww3_struct"
gefs_builds="gefs gfs_utils ufs_utils upp ww3_struct"
sfs_builds="sfs gfs_utils ufs_utils upp ww3_unstruct"
gsi_builds="gsi_enkf gsi_monitor gsi_utils"
gdas_builds="gdas gsi_monitor gsi_utils"

# Builds that will use a whole compute node each
compute_builds="gfs gefs sfs"
# Service node builds
# The GDASApp (for now) needs to be compiled on the service node
service_builds="gdas gfs_utils ufs_utils upp ww3_struct ww3_unstruct gsi gsi_utils gsi_monitor"

# Jobs per build ("min max")
declare -A build_jobs build_opts build_scripts
build_jobs["gfs"]=8
build_jobs["gefs"]=8
build_jobs["sfs"]=8
build_jobs["gdas"]=8
build_jobs["gsi_enkf"]=2
build_jobs["gfs_utils"]=1
build_jobs["ufs_utils"]=1
build_jobs["ww3_unstruct"]=1
build_jobs["ww3_struct"]=1
build_jobs["gsi_utils"]=1
build_jobs["gsi_monitor"]=1
build_jobs["gfs_utils"]=1
build_jobs["upp"]=1

# Establish build options for each job
build_opts["gfs"]="${wave_opt} ${_build_ufs_opt} ${_verbose_opt} ${_build_debug} ${_gfs_exec}"
build_opts["gefs"]="${wave_opt} ${_build_ufs_opt} ${_verbose_opt} ${_build_debug} ${_gefs_exec}"
build_opts["sfs"]="${wave_opt} ${_build_ufs_opt} ${_verbose_opt} ${_build_debug} ${_sfs_exec}"
build_opts["upp"]="${_build_debug}"
build_opts["ww3_unstruct"]="${_verbose_opt} ${_build_debug}"
build_opts["ww3_struct"]="-w ${_verbose_opt} ${_build_debug}"
build_opts["gdas"]="${_verbose_opt} ${_build_debug}"
build_opts["ufs_utils"]="${_verbose_opt} ${_build_debug}"
build_opts["gfs_utils"]="${_verbose_opt} ${_build_debug}"
build_opts["gsi_utils"]="${_verbose_opt} ${_build_debug}"
build_opts["gsi_enkf"]="${_verbose_opt} ${_build_debug}"
build_opts["gsi_monitor"]="${_verbose_opt} ${_build_debug}"

# Set the build script name for each build
build_scripts["gfs"]="build_ufs.sh"
build_scripts["gefs"]="build_ufs.sh"
build_scripts["sfs"]="build_ufs.sh"
build_scripts["gdas"]="build_gdas.sh"
build_scripts["gsi_enkf"]="build_gsi_enkf.sh"
build_scripts["gfs_utils"]="build_gfs_utils.sh"
build_scripts["ufs_utils"]="build_ufs_utils.sh"
build_scripts["ww3_unstruct"]="build_ww3_prepost.sh"
build_scripts["ww3_struct"]="build_ww3_prepost.sh"
build_scripts["gsi_utils"]="build_gsi_utils.sh"
build_scripts["gsi_monitor"]="build_gsi_monitor.sh"
build_scripts["gfs_utils"]="build_gfs_utils.sh"
build_scripts["upp"]="build_upp.sh"

# Check the requested systems to make sure we can build them
declare -A builds
system_count=0
for system in ${@}; do
   if [[ " ${supported_systems[*]} " =~ " ${system} " ]];
      (( system_count += 1 ))
      build_list_name="${system}_builds"
      for build in ${!build_list_name}; do
         builds["${build}"]="yes"
      done
   else
      echo "Unsupported build system: ${system}"
      _usage
   fi
done

# If no build systems were selected, build just the gfs
if [[ ${system_count} -eq 0 ]]; then
   system_count=1
   builds["gfs"]="yes"
fi

# Create directories
mkdir -p "${HOMEgfs}/sorc/logs" "${HOMEgfs}/exec"

# If we are running this on compute nodes, then call compute_build.sh with the list of builds

if [[ "${_compute_build}" == "YES" ]]; then 
   #shellcheck disable=SC2086
   compute_build.sh -a "${_hpc_account}" ${!builds[@]}
   stat=$?
   exit ${stat}
fi

# Otherwise, we are building locally

#------------------------------------
# GET MACHINE
#------------------------------------
export COMPILER="intel"
source "${HOMEgfs}/ush/detect_machine.sh"
source "${HOMEgfs}/ush/module-setup.sh"
if [[ -z "${MACHINE_ID}" ]]; then
  echo "FATAL: Unable to determine target machine"
  exit 1
fi

#------------------------------------
# SOURCE BUILD VERSION FILES
#------------------------------------
# TODO: Commented out until components aligned for build
#source ../versions/build.ver

#------------------------------------
# Exception Handling Init
#------------------------------------
# Disable shellcheck warning about single quotes not being substituted.
# shellcheck disable=SC2016
ERRSCRIPT=${ERRSCRIPT:-'eval [[ $errs = 0 ]]'}
# shellcheck disable=
errs=0

#------------------------------------
# Check which builds to do and assign # of build jobs
#------------------------------------

echo "Building ${build_list}"

procs_in_use=0
declare -A build_ids

check_builds()
{
   for chk_build in "${!builds[@]}"; do
      # Check if the build is complete and if so what the status was
      if [[ -n "${build_ids[${chk_build}]+0}" ]]; then
         if ! ps -p "${build_ids[${chk_build}]}" > /dev/null; then
            wait "${build_ids[${chk_build}]}"
            build_stat=$?
            if [[ ${build_stat} != 0 ]]; then
               echo "build_${chk_build}.sh failed!  Exiting!"
               echo "Check logs/build_${chk_build}.log for details."
               echo "logs/build_${chk_build}.log" > "${HOMEgfs}/sorc/logs/error.logs"
               for kill_build in "${!builds[@]}"; do
                  if [[ -n "${build_ids[${kill_build}]+0}" ]]; then
                     pkill -P "${build_ids[${kill_build}]}"
                  fi
               done
               return "${build_stat}"
            fi
         fi
      fi
   done
   return 0
}

builds_started=0
# Now start looping through all of the jobs until everything is done
while [[ ${builds_started} -lt ${#builds[@]} ]]; do
   for build in "${!builds[@]}"; do
      # Has the job started?
      if [[ -n "${build_jobs[${build}]+0}" && -z "${build_ids[${build}]+0}" ]]; then
         # Do we have enough processors to run it?
         if [[ ${_build_job_max} -ge $(( build_jobs[build] + procs_in_use )) ]]; then
            # double-quoting build_opts here will not work since it is a string of options
            #shellcheck disable=SC2086
            "./build_${build}.sh" ${build_opts[${build}]:-} -j "${build_jobs[${build}]}" > \
               "${logs_dir}/build_${build}.log" 2>&1 &
            build_ids["${build}"]=$!
            echo "Starting build_${build}.sh"
            procs_in_use=$(( procs_in_use + build_jobs[${build}] ))
         fi
      fi
   done

   # Check if all builds have completed
   # Also recalculate how many processors are in use to account for completed builds
   builds_started=0
   procs_in_use=0
   for build in "${!builds[@]}"; do
      # Has the build started?
      if [[ -n "${build_ids[${build}]+0}" ]]; then
         builds_started=$(( builds_started + 1))
         # Calculate how many processors are in use
         # Is the build still running?
         if ps -p "${build_ids[${build}]}" > /dev/null; then
            procs_in_use=$(( procs_in_use + builds["${build}"] ))
         fi
      fi
   done

   # If requested, check if any build has failed and exit if so
   if [[ "${_quick_kill}" == "YES" ]]; then
      check_builds
      build_stat=$?
      if (( build_stat != 0 )); then
         exit "${build_stat}"
      fi
   fi

   sleep 5s
done


# Wait for all jobs to complete and check return statuses
while [[ "${#builds[@]}" -gt 0 ]]; do

   # If requested, check if any build has failed and exit if so
   if [[ "${_quick_kill}" == "YES" ]]; then
      check_builds
      build_stat=$?
      if [[ ${build_stat} != 0 ]]; then
         exit "${build_stat}"
      fi
   fi

   for build in "${!builds[@]}"; do
      # Test if each job is complete and if so, notify and remove from the array
      if [[ -n "${build_ids[${build}]+0}" ]]; then
         if ! ps -p "${build_ids[${build}]}" > /dev/null; then
            wait "${build_ids[${build}]}"
            build_stat=$?
            errs=$((errs+build_stat))
            if [[ ${build_stat} == 0 ]]; then
               echo "${build_scripts[${build}]} completed successfully!"
            else
               echo "${build_scripts[${build}]} failed with status ${build_stat}!"
            fi

            # Remove the completed build from the list of PIDs
            unset 'build_ids[${build}]'
            unset 'builds[${build}]'
         fi
      fi
   done

   sleep 5s
done

#------------------------------------
# Exception Handling
#------------------------------------
if (( errs != 0 )); then
  cat << EOF
BUILD ERROR: One or more components failed to build
  Check the associated build log(s) for details.
EOF
  ${ERRSCRIPT} || exit "${errs}"
fi

echo;echo " .... Build system finished .... "

exit 0
