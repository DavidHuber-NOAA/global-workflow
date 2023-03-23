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

# Send the files to be archived via globus and retain the task ID
local_target="${LOCAL_GLOBUS_ADDR}:${ATARDIRloc}/${CDATE}"
remote_target_dir="/collab1/data/${REMOTE_USERNAME}/${PSLOT}/${CDATE}"
globus_target="${REMOTE_GLOBUS_ADDR}:${remote_target_dir}"

rm -f send_list
for file in $(find ${ATARDIRloc}/${CDATE} -name "*${RUN}*"); do
   echo "${file} $(basename ${file})" >> send_list
done

${GLOBUS_XFR} --batch "send_list" ${local_target} ${globus_target} > globus_output

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
   exit ${status}
fi

#Remove previous copy of the hpss log file used to notify that the job is complete, if it exists
remote_inv_target_dir="/collab1/data/${REMOTE_USERNAME}/inventory"
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

#Send the HPSS push script and retain the task number
local_target="${LOCAL_GLOBUS_ADDR}:${USHgfs}/push_inv_hpss.sh"
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
         if [[ inv_count != 0 ]]; then
            echo "Remote script file has not been touched, cron likely not activated on remote server"
            echo "If the remote is Niagara, enter a crontab entry like the following and try again"
            echo "*/5 * * * * [[ -e /collab1/data/$LOGNAME/inventory/push_inv_hpss.sh ]] && bash /collab1/data/$LOGNAME/inventory/push_inv_hpss.sh"
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
