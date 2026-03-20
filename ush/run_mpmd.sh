#!/usr/bin/env bash

################################################################################
#
# UNIX Script Documentation Block
# Script name:         run_mpmd.sh
# Script description:  Run multiple commands in MPMD mode or serially
#
# Author:   Rahul Mahajan and David Huber
#
# Org:      NCEP/EMC
#
# Abstract: This script runs multiple commands in MPMD mode. It is used to run
#           multiple serial commands in parallel using the CFP (Coupled Framework
#           Parallelism) feature of the workflow. The script handles chunking of the
#           commands to avoid oversubscription of resources.
#
#           The script supports two command file formats:
#
#           1. Simple format (default): One command per line, each assumed to be a
#              single-core, single-threaded task.
#                 ./command1 arg1 arg2
#                 ./command2 arg1
#
#           2. Table format: Each line is a quoted table of command, number of MPI
#              tasks, and number of threads per task. If the second or third column
#              is missing, they default to 1. This enables multi-core and
#              multi-threaded heterogeneous MPMD jobs.
#                 "./gfs_model" "128" "2"
#                 "${HOMEgfs}/ush/product_manager.sh ./file_list.txt" "1" "1"
#
# Environment variables:
#           USE_CFP: If set to YES, run in MPMD mode, else run in serial mode. Default is 'NO'.
#           launcher: Command to launch the MPMD job. Default is empty.
#                     Supported launchers are 'srun' and 'mpiexec'.
#           mpmd_opt: Additional options to pass to the launcher. Default is empty.
#                     Only used for simple format command files.
#                     Example:
#                            srun: "--multi-prog --output=mpmd.%j.%t.out"
#                         mpiexec: "--cpu-bind verbose,core cfp"
#
# Input:
#           cmdfile: File containing commands to execute in MPMD/serial mode
#
# Command line:
#           run_mpmd.sh cmdfile
#
################################################################################

cmdfile=${1:?"run_mpmd requires an input file containing commands to execute in MPMD/serial mode"}

# Determine launcher type
if [[ "${launcher:-}" =~ ^srun.* ]]; then #  srun-based system e.g. Hera, Orion, etc.
    _mpmd_launcher=srun
elif [[ "${launcher:-}" =~ ^mpiexec.* ]]; then # mpiexec-based system e.g. WCOSS2
    _mpmd_launcher=mpiexec
else
    echo "WARNING: Unsupported or empty launcher: '${launcher:-}', using serial mode instead"
    echo "         Supported launchers are 'srun' and 'mpiexec'"
    _mpmd_launcher=unsupported
fi

# Check if we are running a supported launcher
if [[ "${_mpmd_launcher}" == "srun" || "${_mpmd_launcher}" == "mpiexec" ]]; then
    echo "INFO: Detected launcher '${_mpmd_launcher}', will attempt to run in MPMD mode if USE_CFP is set to YES"
    if [[ -z "${max_tasks_per_node:-}" || -z "${ntasks:-}" ]]; then
        echo "WARNING: max_tasks_per_node and/or ntasks is not set, disabling MPMD mode."
        USE_CFP=NO
    else
        USE_CFP=${USE_CFP:-"NO"}
        max_tasks_per_node=$((ntasks < max_tasks_per_node ? ntasks : max_tasks_per_node))
    fi
else
    USE_CFP="NO"
fi

# Functions to detect and parse table format command files.
is_table_format() {
    # Detect if a command file uses the table format.
    # Table format lines start with a double quote.
    # Returns 0 (true) if table format, 1 (false) otherwise.
    # Note: Detection is based on the first non-empty, non-comment line.
    #       Mixed format files are not supported.
    local file="${1}"
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "${line}" || "${line}" =~ ^[[:space:]]*# ]] && continue
        if [[ "${line}" =~ ^[[:space:]]*\" ]]; then
            return 0
        else
            return 1
        fi
    done < "${file}"
    return 1
}

parse_table_line() {
    # Parse a table format line into command, ntasks, and nthreads.
    # Expected format: "command" ["ntasks"] ["nthreads"]
    # Sets global variables: _tbl_cmd, _tbl_ntasks, _tbl_nthreads
    local line="${1}"
    local _raw
    _raw=$(echo "${line}" | awk -F'"' '{
        cmd = $2
        ntasks = (NF >= 4 && $4 != "") ? $4 : 1
        nthreads = (NF >= 6 && $6 != "") ? $6 : 1
        printf "%s\t%s\t%s", cmd, ntasks, nthreads
    }')
    IFS=$'\t' read -r _tbl_cmd _tbl_ntasks _tbl_nthreads <<< "${_raw}"
}

# If USE_CFP is not set or is not YES, run in serial mode
if [[ "${USE_CFP}" != "YES" ]]; then
    echo "INFO: Using serial mode for MPMD job"
    rc=0
    if is_table_format "${cmdfile}"; then
        echo "INFO: Detected table format command file"
        while IFS= read -r line; do
            [[ -z "${line}" || "${line}" =~ ^[[:space:]]*# ]] && continue
            parse_table_line "${line}"
            OMP_NUM_THREADS=${_tbl_nthreads} bash -c "${_tbl_cmd}" >> mpmd.out 2>&1 && true
            rc=$?
            if [[ ${rc} -ne 0 ]]; then break; fi
        done < "${cmdfile}"
    else
        chmod 755 "${cmdfile}"
        bash +x "${cmdfile}" > mpmd.out 2>&1 && true
        rc=$?
    fi
    if [[ -s mpmd.out ]]; then
        cat mpmd.out
    fi
    exit "${rc}"
fi

# Establish the MPMD chunk file pattern.
mpmd_cmdfile="${DATA:-}/mpmd_cmdfile"
rm -f "${mpmd_cmdfile}"*

# Functions to support MPMD execution
chunk_mpmd() {
    # Usage chunk_mpmd cmdfile chunk_size chunk_num chunk_file
    # This takes a chunk of the full mpmd command file and creates a new chunk
    # file with the specified number of lines
    # Inputs:
    #   cmdfile: the full mpmd command file to read from and modify
    #   chunk_size: the number of lines to include in the chunk file
    #   chunk_num: the chunk number (used to determine which lines from the cmdfile to include in the chunk file)
    #   chunk_file: the name of the chunk file to create
    # Use this function when the number of MPMD tasks is greater than the maximum tasks per node.
    local mpmd_file="${1}"
    local chunk_sz="${2}"
    local chunk_num="${3}"
    local chunk_file="${4}"
    if [[ ! -s "${mpmd_file}" ]]; then
        echo "ERROR: MPMD command file '${mpmd_file}' is empty or does not exist."
        return 1
    fi

    if [[ -f "${chunk_file}" ]]; then
        echo "ERROR: chunk file '${chunk_file}' already exists!"
        return 1
    fi

    # Determine which line to start reading from
    local _start_line=$(((chunk_num - 1) * chunk_sz + 1))
    local _end_line=$((chunk_num * chunk_sz))

    # mpiexec needs to know the interpreter
    if [[ "${_mpmd_launcher}" == "mpiexec" ]]; then
        echo "#!/usr/bin/bash" > "${chunk_file}"
    fi

    local _counter=1
    while IFS= read -r line; do
        if [[ ${_counter} -ge ${_start_line} && ${_counter} -le ${_end_line} ]]; then
            local i=$((_counter - _start_line))
            # Slurm requires a counter in front of each line in the script
            if [[ "${_mpmd_launcher}" == "srun" ]]; then
                echo "${i} ${line}" >> "${chunk_file}"
            elif [[ "${_mpmd_launcher}" == "mpiexec" ]]; then
                echo "${line} > mpmd.${i}.out 2>&1" >> "${chunk_file}"
            fi
            err=$?
            if [[ ${err} -ne 0 ]]; then
                echo "ERROR: Failed to write line '${line}' to chunk file '${chunk_file}'"
                return "${err}"
            fi
        fi
        ((_counter = _counter + 1))
    done < "${mpmd_file}"

    return 0
}

cat_outputs() {
    # This function concatenates the output files from the MPMD job and prints them to stdout.
    # It also removes the individual output files after concatenation.

    # Optional argument to issue error if no output files are found.
    _err_on_empty="${1:-false}"
    out_files=$(find . -name 'mpmd.*.out')
    if [[ -z "${out_files}" ]]; then
        if [[ "${_err_on_empty}" == "true" ]]; then
            echo "ERROR: No output files found for MPMD job"
            return 1
        else
            # Nothing to do, return success.
            return 0
        fi
    fi
    for file in ${out_files}; do
        {
            echo "BEGIN OUTPUT FROM ${file}"
            cat "${file}"
            echo "END OUTPUT FROM ${file}"
        } >> mpmd.out
        rm -f "${file}"
    done
}

run_table_mpmd() {
    # Run a table format MPMD command file using heterogeneous job steps.
    # Each entry in the table specifies a command, the number of MPI tasks,
    # and the number of threads. Entries are chunked based on the total
    # available tasks (ntasks) to avoid oversubscription.
    local cmdfile="${1}"

    # Parse all table entries
    local -a cmds=()
    local -a task_counts=()
    local -a thread_counts=()

    while IFS= read -r line; do
        [[ -z "${line}" || "${line}" =~ ^[[:space:]]*# ]] && continue
        parse_table_line "${line}"
        cmds+=("${_tbl_cmd}")
        task_counts+=("${_tbl_ntasks}")
        thread_counts+=("${_tbl_nthreads}")
    done < "${cmdfile}"

    local n_entries=${#cmds[@]}
    if [[ ${n_entries} -eq 0 ]]; then
        echo "ERROR: No valid entries found in table format command file."
        return 1
    fi

    # Process entries in chunks that fit within the total allocation
    local err=0
    local chunk_start=0
    local total_allocated_tasks=${ntasks:-1}

    while [[ ${chunk_start} -lt ${n_entries} ]]; do
        local chunk_tasks=0
        local chunk_end=${chunk_start}

        # Accumulate entries until adding the next would exceed available tasks
        while [[ ${chunk_end} -lt ${n_entries} ]]; do
            local next_tasks=$((chunk_tasks + task_counts[chunk_end]))
            #if [[ ${chunk_tasks} -gt 0 && ${next_tasks} -gt ${total_allocated_tasks} ]]; then
            #    break
            #fi
            if [[ ${task_counts[chunk_end]} -gt ${total_allocated_tasks} ]]; then
                echo "WARNING: Entry $((chunk_end + 1)) requires ${task_counts[chunk_end]} tasks but only ${total_allocated_tasks} are allocated."
            fi
            chunk_tasks=${next_tasks}
            chunk_end=$((chunk_end + 1))
        done

        # Build the heterogeneous launch command for this chunk
        local launch_args=""
        local first=true

        cpu_list=
        for ((idx = chunk_start; idx < chunk_end; idx++)); do
            # Create a wrapper script that sets OMP_NUM_THREADS and runs the command
            local wrapper="${mpmd_cmdfile}.wrapper.${idx}"
            cat > "${wrapper}" << WRAP_EOF
#!/bin/bash
export OMP_NUM_THREADS=${thread_counts[idx]}
exec ${cmds[idx]}
WRAP_EOF
            chmod 755 "${wrapper}"

            if [[ "${first}" != "true" ]]; then
                launch_args+=" :"
            fi
            first=false

            if [[ "${_mpmd_launcher}" == "srun" ]]; then
                launch_args+=" -n ${task_counts[idx]} -c ${thread_counts[idx]} ${wrapper}"
            elif [[ "${_mpmd_launcher}" == "mpiexec" ]]; then
                # --depth sets CPUs per rank (for thread placement), --cpu-bind depth
                # binds each rank to its assigned CPUs based on the depth value.
                # Almost works!! launch_args+=" -n ${task_counts[idx]} --env OMP_PLACES=threads --env OMP_PROC_BIND=spread --env OMP_NUM_THREADS=${thread_counts[idx]} --cpu-bind verbose,none ${cmds[idx]}"
                # Test config
                list=$(seq -s, 0 $((task_counts[idx] - 1)))
                if [[ -z "${cpu_list}" ]]; then 
                    cpu_list="${list}"
                else
                    cpu_list="${cpu_list},${list}"
                fi
                launch_args+=" -n ${task_counts[idx]} ${cmds[idx]}"
            fi
        done

        echo "INFO: Launching table MPMD chunk (entries $((chunk_start + 1))-${chunk_end} of ${n_entries}, total tasks: ${chunk_tasks})"

        if [[ "${_mpmd_launcher}" == "srun" ]]; then
            unset_strict
            # shellcheck disable=SC2086
            ${launcher:-} ${launch_args} >> mpmd.out 2>&1
            set_strict
        elif [[ "${_mpmd_launcher}" == "mpiexec" ]]; then
            # shellcheck disable=SC2086
            ${launcher:-} --cpu-bind verbose,list:${cpu_list} ${launch_args} >> mpmd.out 2>&1
        fi
        err=$?

        if [[ ${err} -ne 0 ]]; then
            echo "ERROR: Table MPMD job failed for entries $((chunk_start + 1))-${chunk_end}"
            break
        fi

        chunk_start=${chunk_end}
    done

    # Cleanup wrapper scripts on success
    if [[ ${err} -eq 0 ]]; then
        rm -f "${mpmd_cmdfile}.wrapper."*
    fi

    return "${err}"
}

# Check for table format and run accordingly
if is_table_format "${cmdfile}"; then
    echo "INFO: Detected table format command file, using heterogeneous MPMD mode"
    run_table_mpmd "${cmdfile}"
    err=$?
    if [[ -s mpmd.out ]]; then
        cat mpmd.out
    else
        echo "WARNING: No output files found for MPMD job"
    fi
    exit "${err}"
fi

# Simple format MPMD execution (single-core, single-threaded tasks)
# Set OMP_NUM_THREADS to 1 to avoid oversubscription
export OMP_NUM_THREADS=1

cat << EOF
INFO: Executing MPMD job, STDOUT and STDERR redirected for each process separately
INFO: On failure, logs for each job will be available in ${DATA}/mpmd.proc_num.out
INFO: The proc_num corresponds to the line in '${cmdfile}'
EOF

# Determine the number of MPMD processes from incoming ${cmdfile}
nm=$(wc -l < "${cmdfile}")

# Test if the number of lines in the cmdfile is greater than the number of tasks per node ($max_tasks_per_node).

if [[ ${nm} -gt ${max_tasks_per_node:-1} ]]; then
    # If needed, split the cmdfile and run it in chunks.
    # For now, keep all MPMD tasks on one node.
    # TODO: consider running the MPMD job across multiple nodes.
    echo "INFO: Number of MPMD tasks (${nm}) is greater than the maximum tasks per node (${max_tasks_per_node:-1})."
    echo "      Running MPMD job in chunks of ${max_tasks_per_node:-1} tasks per node."
    chunk_size=${max_tasks_per_node:-1}
else
    # Otherwise, we can run all MPMD tasks in one chunk.
    chunk_size=${nm}
fi

# Start chunking through the MPMD command file.
chunk_num=1
err=0
for ((i = 0; i < nm; i += chunk_size)); do
    chunk_file="${mpmd_cmdfile}.chunk${chunk_num}"
    chunk_mpmd "${cmdfile}" "${chunk_size}" "${chunk_num}" "${chunk_file}"
    err=$?
    if [[ ${err} -ne 0 ]]; then
        echo "ERROR: Failed to create chunk file '${chunk_file}' from '${cmdfile}'"
        break
    fi
    chmod 755 "${chunk_file}"
    # Count the number of lines not including commented lines (i.e. shebangs)
    n_mpmd_tasks=$(grep -v -c "^ *#" < "${chunk_file}")
    if [[ "${_mpmd_launcher}" == "srun" ]]; then
        unset_strict
        # shellcheck disable=SC2086
        ${launcher:-} ${mpmd_opt:-} -n "${n_mpmd_tasks}" "${chunk_file}"
        set_strict
    elif [[ "${_mpmd_launcher}" == "mpiexec" ]]; then
        # shellcheck disable=SC2086
        ${launcher:-} -np "${n_mpmd_tasks}" ${mpmd_opt:-} "${chunk_file}"
    fi
    err=$?
    if [[ ${err} -ne 0 ]]; then
        echo "ERROR: MPMD job failed for ${chunk_file}"
        break
    fi
    # Call cat_outputs and error if no outputs are found.
    cat_outputs "true"
    err=$?
    if [[ ${err} -ne 0 ]]; then
        echo "ERROR: No output files found for MPMD job for chunk file '${chunk_file}'"
        break
    fi
    ((chunk_num = chunk_num + 1))
done

# On success remove the command file and any chunk files.
if [[ ${err} -eq 0 ]]; then
    rm -f "${mpmd_cmdfile}.chunk"*
fi

# Concatenate any remaining output files if they exist
cat_outputs
if [[ -s mpmd.out ]]; then
    cat mpmd.out
else
    echo "WARNING: No output files found for MPMD job"
fi

exit "${err}"
