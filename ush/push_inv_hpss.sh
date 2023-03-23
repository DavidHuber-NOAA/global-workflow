#!/usr/bin/bash
# push_inv_to_hpss.sh
# Purpose:  Executes inventory scripts sent to Niagara via globus jobs
#           to facilitate pushing archives to HPSS from systems that do
#           not have HPSS connections.

set -eu

#Move inventory scripts to a temporary directory and then execute them
#so they are not executed by subsequent cron calls
work_dir=$(mktemp -d)

count=0
for script in /collab1/data/${LOGNAME}/inventory/inventory*; do
   if [[ -e ${script} ]]; then
      mv ${script} ${work_dir}
      count=$((count+1))
   fi
done

if [[ $count -gt 0 ]]; then
   #Execute the scripts
   for script in ${work_dir}/*; do
      [[ ${script} ]] && bash ${script}
   done
fi

exit 0
