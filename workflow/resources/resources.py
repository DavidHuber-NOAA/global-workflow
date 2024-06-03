#!/usr/bin/env python3

import re
from math import ceil, floor
from typing import Any, Dict, List

from hosts import Host
from wxflow import AttrDict


class ResourceConfig:

    def __init__(self) -> None:

        self.host_info = Host().host_info

    def parse_resource_yaml(self, yaml_filename: str, parse_dict: Dict[str, Any]) -> None:
        """ Parse the resources yaml with desired options and machine specs

        Parameters:
        -----------
            yaml_filename: str
                Filename of the jinja yaml to parse

            parse_dict: Dict
                Context dictionary to parse the yaml with
        """

        # Create a dictionary to parse the jinja yaml with
        parse_dict.update(self._get_host_info())
        self.resources = parse_j2yaml(yaml_filename,
                                      parse_dict,
                                      allow_missing=True)

        # Store the filename for error reporting later
        self.yaml_filename = yaml_filename

    def _get_host_info(self) -> Dict[Dict[str, Any]]:

        mem_per_core = self.host_info.MEM_PER_NODE / self.host_info.CORES_PER_NODE
        mem_per_core = f"{mem_per_core * 1024:.3f}MB"
        mem_per_node = f"{self.host_info.MEM_PER_NODE * 1024:.3f}MB"
        cores_per_node = self.CORES_PER_NODE

        return {"host_info": {"cores_per_node": cores_per_node,
                              "mem_per_node": mem_per_node,
                              "mem_per_core": mem_per_core}}

    def gen_task_config(self, task: str, run: str) -> Dict[str, Any]:
        """Generate task-specific resources and variables

        Parameters
        ----------
        task: str
            The name of the task

        run: str
            Which run is this for (gfs, gdas, enkfgfs, enkfgdas)

        Returns
        -------
        task_resources: Dict
            Resource definitions for the given task.
        task_variables: Dict
            Non-resource variables defined in the resource yaml.
        """

        # Check that the task has defined resources
        if task not in self.resources:
            raise KeyError(f"Resource definitions are undefined for {task}."
                           f"Add definitions to {self.yaml_filename}.")

        # Get the run- and task-specific specifications from the parsed yaml
        task_specs = {}
        task_vars = self.resources[task]
        task_specs.update(task_vars["parameters"]) if "parameters" in task_vars
        task_specs.update(task_vars[run]) if run in task_vars

        task_name = run + task
        # Check that resources were defined
        if len(task_specs) == 0:
            raise ValueError(
                f"No resources are defined for task {task_name} in {yaml_filename}")
        elif "num_PEs" not in task_specs:
            raise KeyError(
                f"{yaml_filename} does not define PE count for {task_name}")
        elif "walltime" not in task_specs:
            raise KeyError(
                f"{yaml_filename} does not define walltime for {task_name}")

        # Assign defaults for missing options
        task_specs["adjustable_PEs"] = True if "adjustable_PEs" not in task_specs
        task_specs["mem_per_PE"] = "default" if "mem_per_PE" not in task_specs
        if "threads" not in task_specs:
            task_specs["threadable"] = False
            task_specs["adjustable_threads"] = False
            task_specs["threads"] = 1
        else:
            # Check for valid threading options
            if "threadable" in task_specs:
                if task_specs["threadable"]:
                    raise KeyError(
                        f"{task_name} is marked threadable, but 'threads' was"
                        f"unspecified in {self.yaml_filename}")
                else:
                    task_specs["adjustable_threads"] = False
            elif "adjustable_threads" in task_specs:
                if task_specs["adjustable_threads"]:
                    raise KeyError(
                        f"{task_name} is marked threadable, but 'threads' was"
                        f"unspecified in {self.yaml_filename}")

            task_specs["threadable"] = False
            task_specs["adjustable_threads"] = False
            task_specs["threads"] = 1

        # Calculate total PEs, PEs per node, memory per node, and threads
        task_resources = self._calc_resources(task_name,
                                              task_specs.num_PEs,
                                              task_specs.threads,
                                              task_specs.threadable,
                                              task_specs.adjustable_threads,
                                              task_specs.adjustable_PEs,
                                              task_specs.mem_per_PE)

        # Get any resource-related variables defined for the task
        task_variables = ResourceConfig._get_variables(task_specs)

        # Return the task configuration
        return (task_resources, task_variables)

    def _calc_resources(self,
                        task_name: str,
                        num_PEs: int,
                        threads: int,
                        threadable: bool,
                        adjustable_threads: bool,
                        adjustable_PEs: bool,
                        mem_per_PE: str,
                        max_PEs_per_node: int = -1) -> Dict[str, Any]:
        """ Calculate resources for a specific task

        Parameters:
        -----------
        task_name: str
            The name of the task
        num_PEs: int
            Minimum number of PEs required for the task
        threads: int
            Number of threads
        threadable: bool
            Is the task threadable?
        adjustable_PEs: bool
            Can the number of PEs be adjusted?
        adjustable_threads: bool
            Can threads be adjusted?
        mem_per_PE: str
            Memory required per PE.  Can be on of
            "default": use (mem_per_core * threads)
            "max": use all of the memory on every node.
                   If nodes are filled completely, this is the same as "default".
            "<N><U>B": where <N> is an integer and <U> is either "G" (giga) or
                       "M" (mega).  "T" (terra) is not implemented, but there
                       may be a use case for it in the future.
        max_PEs_per_node: int
            Optional.  Specify maximum number of PEs that can run on a node.
            The default is cores/node.

        Returns:
        task_resources: Dict[str, Any]
            Final specifications for the task.
                num_PEs
                threads
                mem_per_node: str - memory required per node
                PEs_per_node: int - number of PEs to place on each node
                num_nodes: int - how many nodes to use
                exclusive: bool - does the job need whole nodes?
                    True if all cores are needed or all the memory is needed

        """

        # Test that the input memory requirement is valid
        if type(mem_per_PE) is not str:
            raise TypeError(
                f"mem_per_PE must be a string, but type {type(mem_per_PE)} given")
        elif not (mem_per_PE == "max" or mem_per_PE == "default"):
            # Convert bytes from e.g. mb to MB
            mem_per_PE = mem_per_PE.capitalize()
            if mem_per_PE.endswith("MB") or mem_per_PE.endswith("GB"):
                if not mem_per_PE[:-2].isdigit():
                    raise ValueError(
                        f"Invalid memory requirement for {task_name}: {mem_per_PE}")
            elif mem_per_PE.endswith("TB"):
                raise NotImplementedError(
                    f"Terrabyte memory requirement detected."
                    f"If there is a use case, then implement this option.")
            else:
                raise ValueError(
                    f"Invalid memory requirement for {task_name}: {mem_per_PE}")

        # Initialize the output task_resources
        task_resources = AttrDict({"num_PEs": num_PEs,
                                   "threads": threads,
                                   "mem_per_node": self.host_info.mem_per_node,
                                   "PEs_per_node": self.host_info.cores_per_node,
                                   "num_nodes": 1,
                                   "exclusive": True})

        # Calculate some oft-used constants
        host_cores_per_node = self.host_info.cores_per_node
        host_mem_per_node = self.host_info.mem_per_node
        host_mem_per_core = self.host_info.mem_per_core
        i_host_mem_per_node = str_mem_to_int(self.host_info.mem_per_node)
        i_host_mem_per_core = str_mem_to_int(self.host_info.mem_per_core)

        # If max_PEs_per_node is set, adjust host_cores_per_node to match
        if max_PEs_per_node != -1:
            host_cores_per_node = max_PEs_per_node

        # Take a first at how many nodes and PEs/node are required and
        # adjust for memory if necessary
        num_nodes = ceil(num_PEs * threads / cores_per_node)
        PEs_per_node = ceil(num_PEs / num_nodes / threads)

        def str_mem_to_int(str_mem: str) -> int:
            # Convert string memory requirements to integer megabytes
            if str_mem.endswith("MB"):
                return int(str_mem.rstrip("MB"))

            elif str_mem.endswith("GB"):
                return int(str_mem.rstrip("GB")) * 1024

        def int_mem_to_str(int_mem: int) -> str:
            # Convert integer megabytes to string "<int_mem>MB"
            return f"{int_mem}MB"

        # If default memory is specified, use host_mem_per_core * threads per task
        # and pack each node
        if mem_per_PE == "default":
            i_mem_per_PE = str_mem_to_int(host_mem_per_core) * threads
            task_resources.num_nodes = ceil(num_PEs * threads / host_cores_per_node)
            task_resources.PEs_per_node = floor(host_cores_per_node / threads)
            task_resources.mem_per_node = int_mem_to_str(i_mem_per_PE *
                                                         task_resources.PEs_per_node)

            return task_resources

        # If max memory is specified, use all node memory and pack each node
        elif mem_per_PE == "max":
            task_resources.num_nodes = ceil(num_PEs * threads / host_cores_per_node)
            task_resources.PEs_per_node = floor(host_cores_per_node / threads)
            task_resources.mem_per_node = host_mem_per_node
            task_resources.exclusive = True

            return task_resources

        # If we are here, then a specific memory request was made
        # Start calculating based on requested memory
        # Make an initial guess at the number of nodes, mem/PE, and PEs/node
        num_nodes = ceil(num_PEs * threads / host_cores_per_node)
        i_mem_per_PE = str_mem_to_int(mem_per_PE)
        PEs_per_node = floor(host_cores_per_node / threads)

        # Check if the memory request is already satisfied
        if i_mem_per_PE * num_PEs < i_host_mem_per_node * nodes:
            # The job fits already
            task_resources.PEs_per_node = PEs_per_node
            task_resources.mem_per_node = int_mem_to_str(i_mem_per_PE * PEs_per_node)
            task_resources.num_nodes = num_nodes

            return task_resources

        else:
            # The job needs more memory
            # Calculate how many PEs can fit on a node based on memory
            num_nodes = ceil(i_mem_per_PE * num_PEs / i_host_mem_per_node)
            PEs_per_node = ceil(num_PEs / num_nodes)

            def adjust_threads_for_mem(in_threads: int, in_mem_per_PE: int) -> List[int]:
                """ Adjust threading so memory requirements are met

                Parameters:
                -----------
                in_threads: int
                    Input thread count
                in_mem_per_PE: int
                    memory required per PE

                Retunrs:
                --------
                [output_threads, num_nodes, PEs_per_node]: List[int]
                    output_threads: int
                        Output thread count
                    num_nodes: int
                        Number of nodes based on new threadding
                    num_nodes: int
                        Number of nodes based on new threadding
                """

                # Search multiples of cores_per_node and find the next one that works.
                multiples = [i for i in range(host_cores_per_node)
                             if host_cores_per_node % i == 0 and i > in_threads]

                if len(multiples) == 0:
                    # No changes can be made
                    multiples = [in_threads]

                for output_threads in multiples:
                    num_nodes = ceil(i_mem_per_PE * num_PEs /
                                     i_host_mem_per_node)

                    PEs_per_node = ceil(num_PEs / num_nodes)
                    if PEs_per_node > 0:
                        # We found a workable solution, exit loop
                        break

                return [output_threads, num_nodes, PEs_per_node]

            if PEs_per_node > 0:
                # We have enough memory for this layout

                if not threadable:
                    # Not threadable, so the calculation is easy
                    i_mem_per_node = i_mem_per_PE * PEs_per_node
                    task_resources.mem_per_node = int_mem_to_str(i_mem_per_node)
                    task_resources.PEs_per_node = PEs_per_node
                    task_resources.num_nodes = ceil(num_PEs / PEs_per_node)
                    return task_resources

                elif threadable:
                    # Make sure each PE fits on one node.
                    if threads * PEs_per_node > host_cores_per_node:
                        # We need to adjust either threads or PEs_per_node
                        # If threads are adjustable, increase them until
                        # they fit on a node.
                        if adjustable_threads:
                            threads, nodes, PEs_per_node, mem_per_node = (
                                adjust_threads_for_mem(threads,
                                                       mem_per_PE,
                                                       host_mem_per_node))
                        else:
                            # Adjust PEs_per_node instead
                            PEs_per_node = ceil(host_cores_per_node / PEs_per_node)
                            nodes = num_PEs / PEs_per_node

                        task_resources.num_nodes = nodes
                        task_resources.PEs_per_node = PEs_per_node
                        task_resources.mem_per_node = int_mem_to_str(PEs_per_node * i_mem_per_PE)
                        task_resources.threads = threads
                        return task_resources

            else:  # PEs/node == 0
                # The memory requirement is too high
                # See if threads can be adjusted
                if threadable and adjustable_threads:
                    threads, num_nodes, PEs_per_node = (
                        adjust_threads_for_mem(threads,
                                               i_mem_per_PE,
                                               host_mem_per_node))

                    task_resources.threads = threads

                    # Check PEs/node again
                    if PEs_per_node > 0:
                        # We have a new workable threading scheme
                        task_resources.PEs_per_node = PEs_per_node
                        task_resources.mem_per_node = mem_per_PE * threads * PEs_per_node
                        task_resources.num_nodes = ceil(num_PEs / PEs_per_node)
                        task_resources.exclusive = True
                        print(
                            f"INFO OMP threads modified for {task_name} from"
                            f"     {old_threads} to {new_threads} to satisfy memory requirements")

                    else:
                        # Memory requirement is extreme, adjust downward
                        task_resources.PEs_per_node = 1
                        task_resources.mem_per_node = host_mem_per_node
                        task_resources.num_nodes = num_PEs
                        task_resources.exclusive = True
                        print(
                            f"WARNING {task_name} has a memory requirement of"
                            f"{mem_per_PE}, but the host only has {host_mem_per_node}."
                            f"Setting memory request to {host_mem_per_node}.")

                    return task_resources

                else:  # not threadable or not adjustable_threads

                    # Threading is not enabled and/or adjustable and the memory
                    # requirement is extreme, adjust it downward.
                    task_resources.PEs_per_node = 1
                    task_resources.mem_per_node = host_mem_per_node
                    task_resources.num_nodes = num_PEs
                    task_resources.exclusive = True
                    print(
                        f"WARNING {task_name} has a memory requirement of"
                        f"{mem_per_PE}, but the host only has {host_mem_per_node}."
                        f"Setting memory request to {host_mem_per_node}.")
