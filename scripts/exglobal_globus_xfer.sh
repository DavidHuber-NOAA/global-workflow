#! /usr/bin/env bash

source "${HOMEgfs}/ush/preamble.sh"

##############################################
# Begin JOB SPECIFIC work
##############################################

###############################################################
# Check that data was archived locally
if [[ ${LOCALARCH} != "YES" ]]; then
   echo "Local archival disabled, no data to send via globus!"
   status=1
   exit "${status}"
fi

###############################################################

# Test for rstprod data and passwordless ssh

has_rstprod=".false."
for file in $(find ${ATARDIRloc}/${CDATE} -name "*${RUN}*"); do
   if [[ -f $file ]]; then
      if [[ $(stat -c "%G" ${file}) -eq "rstprod" ]]; then
         has_rstprod=".true."
      fi
   fi
done

if [[ ${has_rstprod} = ".true." ]]; then
   echo "Archives contain restricted data; verifying this can be sent to target machine"
   rstprod_sample="${REMOTE_INV_DIR}/test_rstprod"
   test_rstprod_commands="set -ex; mkdir -p ${REMOTE_INV_DIR}; touch ${rstprod_sample}"
   test_rstprod_commands="${test_rstprod_commands}; chgrp rstprod ${rstprod_sample}; rm -f ${rstprod_sample}"
   ssh -t ${REMOTE_USER}@${TARGET_DTN} "${test_rstprod_commands}"
   status=$?
   if [[ $status != 0 ]]; then
      echo "Unable to create test rstprod file on remote system"
      echo "Verify your remote username, DTN, rstprod access, and location"
      exit 2
   fi
fi

# Send the files to be archived via globus and retain the task ID
local_target="${LOCAL_GLOBUS_ADDR}:${ATARDIRloc}/${CDATE}"
remote_target_dir="${REMOTE_TARGET_DIR}"
globus_target="${REMOTE_GLOBUS_ADDR}:${remote_target_dir}"

rm -f send_list
rstprod_files=()
for file in $(find ${ATARDIRloc}/${CDATE} -name "*${RUN}*"); do
   echo "${file} $(basename ${file})" >> send_list
   if [[ $(stat -c "%G" ${file}) -eq "rstprod" ]]; then
      rstprod_files+=("$file")
   fi
done

${GLOBUS_XFR} --batch "send_list" "${local_target}" "${globus_target}" > globus_output

status=$?
if [ $status -ne 0 ]; then
   echo "Globus data transfer failed. Double check Globus IDs and make sure you're logged in and endpoints are activated."
   exit $status
fi

#Get the globus task number and wait until complete
task_id=$(cat globus_output | grep "Task ID" | sed "s/Task ID: \(.*\)/\1/")

${GLOBUS_WAIT} "${task_id}"

status=$?
if [ ${status} -ne 0 ]; then
   echo "Globus data transfer failed after initialization."
   #Run chgrp commands on any rstprod files that were transferred, ignoring errors
   for file in "${rstprod_files[@]}"; do
      chgrp_cmd="chgrp rstprod ${remote_target_dir}/$(basename $file)"
      ssh -t "${REMOTE_USER}@${TARGET_DTN}" "${chgrp_cmd}"
   done
   exit ${status}
fi

#Remove previous copy of the hpss log file used to notify that the job is complete, if it exists
remote_inv_target_dir="${REMOTE_INV_DIR}"
hpss_log_base=hpss.${PSLOT}.${CDATE}.log
hpss_log="${remote_inv_target_dir}/${hpss_log_base}"
tmp_log="${remote_target_dir}/tmp.${PSLOT}.${CDATE}.log"
globus_target="${REMOTE_GLOBUS_ADDR}:${remote_target_dir}"
${GLOBUS_RM} ${REMOTE_GLOBUS_ADDR}:${hpss_log} > rm_hpsslog_output

${GLOBUS_WAIT} "${task_id}"

status=$?
if [ ${status} -ne 0 ]; then
   echo "Globus data transfer failed after initialization."
   exit ${status}
fi

######Generate a script to push the archives that were just sent to the remote server (Niagara) onward to HPSS
inv_fname="inventory.${PSLOT}.${CDATE}"
loc_inv="${ATARDIRloc}/${inv_fname}"
targ_inv="${remote_inv_target_dir}/${inv_fname}"
file_list=$(find ${ATARDIRloc}/${CDATE} -type f)

rm -f ${loc_inv}
touch ${loc_inv}
echo "#!/usr/bin/bash" >> ${loc_inv}
echo "source /etc/bashrc" >> ${loc_inv}
echo "machine=${machine}" >> ${loc_inv}
echo "module load hpss" >> ${loc_inv}
echo "hsi \"mkdir -p ${ATARDIR}/${CDATE}\" >> ${tmp_log} 2>&1" >> ${loc_inv}

for file in ${file_list}; do
   sent_fname=$(basename ${file})
   echo "hsi put ${remote_target_dir}/${sent_fname} : ${ATARDIR}/${CDATE}/${sent_fname} >> ${tmp_log} 2>&1" >> ${loc_inv}
   echo "if [[ \$? != 0 ]]; then" >> ${loc_inv}
   echo "   echo 'Failed to send ${sent_fname} to HPSS, aborting' >> ${tmp_log} 2>&1" >> ${loc_inv}
   echo "   exit 33" >> ${loc_inv}
   echo "fi" >> ${loc_inv}
   # Change rstprod files' group on HPSS after transfer
   if [[ " ${rstprod_files[*]} " =~ " ${file} " ]]; then
      echo "hsi chgrp rstprod ${ATARDIR}/${CDATE}/${sent_fname} >> ${tmp_log} 2>&1" >> ${loc_inv}
      echo "if [[ \$? != 0 ]]; then" >> ${loc_inv}
      echo "   echo 'Failed to change group for ${sent_fname} on HPSS, aborting' >> ${tmp_log} 2>&1" >> ${loc_inv}
      echo "   exit 34" >> ${loc_inv}
      echo "fi" >> ${loc_inv}
   fi
done
echo "mv ${tmp_log} ${hpss_log}" >> ${loc_inv}

#Send the inventory HPSS script and retain the task number
local_target="${LOCAL_GLOBUS_ADDR}:${loc_inv}"
globus_target="${REMOTE_GLOBUS_ADDR}:${targ_inv}"
${GLOBUS_XFR} ${local_target} ${globus_target} > globus_inv_output

status=$?
if [ ${status} -ne 0 ]; then
   echo "Globus HPSS script transfer failed."
   exit ${status}
fi

#Write a script to push data to HPSS
[[ -f push_inv_hpss.sh ]] && rm -f push_inv_hpss.sh

cat > push_inv_hpss.sh << EOF

#!/usr/bin/bash
# push_inv_to_hpss.sh
# Purpose:  Executes inventory scripts sent via globus jobs to facilitate
# pushing archives to HPSS from systems that do not have HPSS connections.

set -eu

#Move inventory scripts to a temporary directory and then execute them
#so they are not executed by subsequent cron calls
work_dir=\$(mktemp -d)

count=0
for script in ${REMOTE_INV_DIR}/inventory*; do
   [[ -e \${script} ]] && mv \${script} \${work_dir} && count=\$((count+1))
done

if [[ \$count -gt 0 ]]; then
   #Execute the scripts
   for script in \${work_dir}/*; do
      [[ -e \${script} ]] && bash \${script}
   done
fi

#Remove the working directory now that we're done with it
rm -rf \${work_dir}

exit 0
EOF

local_target="${LOCAL_GLOBUS_ADDR}:$(pwd)/push_inv_hpss.sh"
globus_target="${REMOTE_GLOBUS_ADDR}:${remote_inv_target_dir}/push_inv_hpss.sh"
${GLOBUS_XFR} ${local_target} ${globus_target} > globus_push_output

#Get the globus task numbers and wait until complete
task_id_inv=$(cat globus_inv_output | grep "Task ID" | sed "s/Task ID: \(.*\)/\1/")
task_id_push=$(cat globus_push_output | grep "Task ID" | sed "s/Task ID: \(.*\)/\1/")

${GLOBUS_WAIT} "${task_id_inv}"
${GLOBUS_WAIT} "${task_id_push}"

status=$?
if [ ${status} -ne 0 ]; then
   echo "Globus HPSS script transfer failed after creation."
   exit ${status}
fi

#Look for the notification file on the remote system indicating the HPSS transfer(s) are complete
globus_target="${REMOTE_GLOBUS_ADDR}:${remote_inv_target_dir}"
transfer_complete=0
set +e
count=0
check_inv=1
while [[ ${transfer_complete} = 0 ]]; do
   sleep 30s
   globus_glob=$(${GLOBUS_LS} ${globus_target})
   for file in ${globus_glob}; do
      found=$( echo ${file} | grep ${hpss_log_base} | wc -l)
      if [[ ${found} = 1 ]]; then
         transfer_complete=1
      elif [[ ${found} > 1 ]]; then
         echo "Too many matching HPSS logs in remote directory"
         exit 2
      fi
   done

   [[ check_inv = 0 ]] && continue

   count=$((count+1))
   #If we get over 10 minutes and the inventory files are still present, there is likely a problem with cron
   if [[ $count -gt 20 ]]; then
      inv_list=$(${GLOBUS_LS} ${globus_target})
      for file in ${inv_list}; do
         inv_count=$(echo "${file}" | grep ${inv_fname} | wc -l)
         if [[ ${inv_count} != 0 ]]; then
            echo "Remote script file has not been touched, cron likely not activated on remote server"
            echo "Enter a crontab entry like the following on the remote system and try again"
            echo "*/5 * * * * [[ -e ${REMOTE_INV_DIR}/push_inv_hpss.sh ]] && bash ${REMOTE_INV_DIR}/push_inv_hpss.sh"
            exit 3
         fi
      done
      #If it has moved, then the HPSS transfer is ongoing; skip this if loop hereafter.
      check_inv=0
   fi

done
set_strict

#Clean up
rm -f globus_output

exit 0
