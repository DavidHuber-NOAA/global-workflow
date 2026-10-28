#!/usr/bin/env python3

"""
Entry point for setting up a builds of global-workflow programs
"""

import glob
import math
import os
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from typing import Dict, List

from wxflow import parse_yaml, AttrDict, to_timedelta, timedelta_to_HMS

from hosts import Host
import rocoto.rocoto as rocoto


_here = os.path.dirname(__file__)
HOMEglobal = os.path.abspath(os.path.join(os.path.abspath(_here), '../..'))
SORC_DIR = os.path.join(HOMEglobal, 'sorc')
DEFAULT_YAML = os.path.join(SORC_DIR, 'build_opts.yaml')
SYSTEMS_DIR = os.path.join(SORC_DIR, 'build_systems')


def input_args(*argv):
    """
    Method to collect user arguments for `setup_buildxml.py`
    """

    description = """
        Setup buildXML to compile global-workflow programs.
    """

    parser = ArgumentParser(description=description,
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('--account', help='HPC account to use (required unless --list-systems is given)', required=False)
    parser.add_argument('--yaml', help='Input YAML file',
                        type=str, required=False, default=DEFAULT_YAML)
    parser.add_argument('--systems', help='Space-separated system(s) to build, or "all". Available systems are '
                        'discovered from build_systems/*.yaml. Defaults to default_system in the YAML file.',
                        required=False, default='')
    parser.add_argument('--list-systems', help='Print the available systems and exit', action='store_true')
    parser.add_argument('--debug', help='Build in debug mode', required=False, action='store_true')

    inputs = parser.parse_args(list(*argv) if len(argv) else None)
    if not inputs.list_systems and not inputs.account:
        parser.error('--account is required')

    return inputs


def discover_systems(yaml_file: str) -> Dict:
    """Find the systems that are available in this repository.

    Each ``build_systems/<system>.yaml`` file next to ``yaml_file`` defines one system: the file
    name is the system name, ``components`` lists what is built for it and ``build`` holds the
    build entries that only that system uses. Removing the file removes the system.

    Parameters
    ----------
    yaml_file : str
        Path to the shared build options YAML file.

    Returns
    -------
    Dict
        Mapping of system name to its parsed YAML contents, sorted by name.
    """

    systems_dir = os.path.join(os.path.dirname(os.path.abspath(yaml_file)), 'build_systems')
    systems = {}
    for path in sorted(glob.glob(os.path.join(systems_dir, '*.yaml'))):
        systems[os.path.splitext(os.path.basename(path))[0]] = AttrDict(parse_yaml(path))
    return systems


def merge_systems(build_specs: Dict, systems: Dict) -> Dict:
    """Merge the discovered systems into the shared build specifications.

    Parameters
    ----------
    build_specs : Dict
        Parsed shared build options (``build_opts.yaml``).
    systems : Dict
        Systems returned by ``discover_systems``.

    Returns
    -------
    Dict
        ``build_specs`` with ``systems`` and ``build`` including every discovered system, and
        ``system_entries`` naming the build entries that came from a system file.

    Raises
    ------
    ValueError
        If a build entry is defined in more than one place.
    """

    build_specs.setdefault('systems', AttrDict())
    build_specs.system_entries = []
    for name, system in systems.items():
        build_specs.systems[name] = list(system.get('components', []))
        for entry, spec in system.get('build', {}).items():
            if entry in build_specs.build:
                raise ValueError(f"Build entry '{entry}' of system '{name}' is already defined elsewhere")
            build_specs.build[entry] = spec
            build_specs.system_entries.append(entry)

    return build_specs


def missing_requirements(task_spec: Dict) -> List[str]:
    """List what a build entry needs that is not present in this repository.

    Parameters
    ----------
    task_spec : Dict
        Build entry with a ``command`` and an optional ``requires`` list of paths relative to ``sorc/``.

    Returns
    -------
    List[str]
        Paths (relative to ``sorc/``) of the build script and required sources that do not exist.
    """

    script = task_spec.command.split()[0]
    needed = [script] + list(task_spec.get('requires', []))
    return [os.path.normpath(path) for path in needed if not os.path.exists(os.path.join(SORC_DIR, path))]


def select_builds(build_specs: Dict, requested: List[str]) -> List[str]:
    """Choose the build entries for the requested systems.

    Parameters
    ----------
    build_specs : Dict
        Build specifications that include the discovered systems.
    requested : List[str]
        Requested system names, or ``['all']``. An empty list selects ``default_system``.

    Returns
    -------
    List[str]
        Names of the build entries to run, in the order they are defined.

    Raises
    ------
    KeyError
        If a requested system is not available.
    FileNotFoundError
        If an explicitly requested system needs a script or source that is not present. Entries
        shared between systems (defined in the shared YAML file) are optional and skipped instead.
    """

    available = [name for name in build_specs.systems if name != 'common']
    explicit = 'all' not in requested

    if not requested:
        default = build_specs.get('default_system', None)
        requested = [default if default in available else available[0]]

    if explicit:
        unknown = [name for name in requested if name not in available]
        if unknown:
            raise KeyError(f"{', '.join(unknown)} is not a valid global-workflow system! "
                           f"Available systems: {', '.join(available)}")
        names = set(build_specs.systems.get('common', []))
        for name in requested:
            names.update(build_specs.systems[name])
    else:
        names = set(build_specs.build)

    selected = []
    for entry, spec in build_specs.build.items():
        if entry not in names:
            continue
        missing = missing_requirements(spec)
        if missing:
            if explicit and entry in build_specs.system_entries:
                raise FileNotFoundError(f"Cannot build '{entry}': missing {', '.join('sorc/' + m for m in missing)}")
            print(f"NOTICE: skipping '{entry}', missing {', '.join('sorc/' + m for m in missing)}", file=sys.stderr)
            continue
        selected.append(entry)

    return selected


def get_task_spec(task_name: str, task_spec: Dict, host_spec: Dict) -> Dict:
    """
    Generate a task specification dictionary for a given task.

    Parameters
    ----------
    task_name: str
        The name of the task.
    task_spec: Dict
        The specification of the task, containing command, walltime, and cores.
    host_spec: Dict
        The specification of the host, containing account, queue, partition, and native.

    Returns:
    --------
    task_dict: Dict
        A dictionary containing the task specification, including resources and other task-related information.
    """

    task_dict = AttrDict()
    task_dict.task_name = task_name
    task_dict.cycledef = "build"
    task_dict.maxtries = 1
    task_dict.command = f"cd {HOMEglobal}/sorc/; {task_spec.command} -j {task_spec.cores}"
    if host_spec.debug:
        task_dict.command = f"{task_dict.command} -d"
    task_dict.job_name = task_name
    task_dict.log = f"{HOMEglobal}/sorc/logs/{task_name}.log"

    task_dict.resources = AttrDict()
    task_dict.resources.account = host_spec.account
    task_dict.resources.queue = host_spec.queue
    task_dict.resources.partition = host_spec.partition
    task_dict.resources.walltime = task_spec.walltime
    task_dict.resources.native = host_spec.native
    task_dict.resources.memory = task_spec.get("memory", None)
    task_dict.resources.nodes = 1
    task_dict.resources.ntasks = task_spec.cores
    task_dict.resources.ppn = task_spec.cores
    task_dict.resources.scheduler = host_spec.scheduler
    task_dict.resources.threads = 1

    # Slurm 26.05+ on Gaea requires explicit --nodes alongside --ntasks.
    # When the host YAML declares CPUS_PER_NODE, compute the node count and
    # append --nodes to the native scheduler flags. Hosts without the field
    # are unaffected (their Slurm version does not enforce this).
    cpus_per_node = host_spec.get("cpus_per_node", 0)
    if cpus_per_node > 0 and host_spec.scheduler == "slurm":
        nodes = math.ceil(task_spec.cores / cpus_per_node)
        native = task_dict.resources.native or ''
        task_dict.resources.native = f"{native} --nodes={nodes}".strip()

    return task_dict


def get_build_specs(build_specs: Dict, host_spec: Dict) -> Dict:
    """Generate build specifications from a rendered yaml AttrDict

    Parameters
    ----------
    build_specs : Dict
        Build specifications and any host-specific overrides
    host_spec: Dict
        The specification of the host, containing account, queue, partition, and native.

    Returns
    -------
    build_specs: Dict
        Overridden build specifications
    """

    # Initialize exclude_nodes from the top-level of the YAML if present
    build_specs.exclude_nodes = build_specs.get("exclude_nodes", None)

    # Get host overrides, if present
    if build_specs.get("host_override", None) is None or build_specs.host_override.get(host_spec.machine, None) is None:
        # Nothing to override, return with original build_specs
        return build_specs

    override = build_specs.host_override[host_spec.machine]

    # Check for host-specific node exclusions
    if "exclude_nodes" in override:
        build_specs.exclude_nodes = override.exclude_nodes

    override_build = override.get("build", {})
    for key in build_specs.build:
        # Override the specific build specs if the key and spec is present in the
        if key in override_build:
            for spec in override_build[key]:
                build_specs.build[key][spec] = override_build[key][spec]

        # Otherwise, take the blanket exceptions and apply to the job
        else:
            if 'max_cores' in override:
                if build_specs.build[key].cores > override.max_cores:
                    # Adjust the walltime based on the ratio of max_cores/build.walltime
                    in_walltime = to_timedelta(build_specs.build[key].walltime)
                    override_walltime = in_walltime * (build_specs.build[key].cores / override.max_cores)
                    build_specs.build[key].cores = override.max_cores
                    build_specs.build[key].walltime = timedelta_to_HMS(override_walltime)

            if 'max_memory' in override and 'memory' in build_specs.build[key]:
                if build_specs.build[key].memory > override.max_memory:
                    build_specs.build[key].memory = override.max_memory

            # Adjust build walltime by the walltime_ratio
            build_specs.build[key].walltime = timedelta_to_HMS(
                to_timedelta(build_specs.build[key].walltime) * override.walltime_ratio)

    return build_specs


def get_host_specs(host: Dict) -> Dict:
    """Generate host specs for the build.xml file based on Host() info

    Parameters
    ----------
    host : Dict
        Host information returned by Host()

    Returns
    -------
    specs: Dict
        Consolidated compute specifics needed for the XML
    """

    native = None
    partition = None

    if host.info.SCHEDULER in ['pbspro']:
        native = '-l place=vscatter'
    elif host.info.SCHEDULER in ['slurm']:
        native = '--export=NONE'
        if host.info.get("PARTITION_BUILD", "") != "":
            partition = host.info.PARTITION_BUILD
        elif host.info.get("PARTITION_BATCH", "") != "":
            partition = host.info.PARTITION_BATCH

    if host.info.get("RESERVATION", "") != "":
        native += f' --reservation={host.info.RESERVATION}'

    if host.info.get("CLUSTERS_BUILD", None) is not None:
        native += f' --clusters={host.info.CLUSTERS_BUILD}'
    elif host.info.get("CLUSTERS", None) is not None:
        native += f' --clusters={host.info.CLUSTERS}'

    specs = AttrDict()
    specs.scheduler = host.info.SCHEDULER
    specs.queue = host.info.QUEUE
    specs.partition = partition
    specs.native = native
    specs.machine = host.machine
    specs.cpus_per_node = host.info.get("CPUS_PER_NODE", 0)

    return specs


def main(*argv):

    user_inputs = input_args(*argv)

    if user_inputs.list_systems:
        print(' '.join(discover_systems(user_inputs.yaml)))
        return

    # Gather host specs and place the user supplied options such as
    # account and debug into the host_specs dict
    host_specs = get_host_specs(Host())
    host_specs.account = user_inputs.account
    host_specs.debug = user_inputs.debug

    # Retrieve build specifications from the shared yaml and the discovered systems
    user_yaml_dict = AttrDict(parse_yaml(user_inputs.yaml))
    systems = discover_systems(user_inputs.yaml)

    user_yaml_dict = merge_systems(user_yaml_dict, systems)
    build_specs = get_build_specs(user_yaml_dict, host_specs)

    # Apply node exclusions to the native scheduler flags
    if build_specs.exclude_nodes:
        if host_specs.scheduler == 'slurm':
            host_specs.native += f" --exclude={build_specs.exclude_nodes}"
        elif host_specs.scheduler == 'pbspro':
            # PBS logic: -l host!=node1 -l host!=node2 ...
            nodes = build_specs.exclude_nodes.split(',')
            pbs_exclude = " ".join([f"-l host!={n.strip()}" for n in nodes])
            host_specs.native += f" {pbs_exclude}"

    builds = select_builds(build_specs, user_inputs.systems.split())

    # Build the task specs from the build specs and host specs
    task_specs = AttrDict()
    for task_name in builds:
        task_specs[task_name] = get_task_spec(task_name, build_specs.build[task_name], host_specs)

    # Start building the XML
    strings = ['<?xml version="1.0"?>',
               '<!DOCTYPE workflow', '[', '<!ENTITY PSLOT "build">', ']>',
               f'<workflow realtime="F" scheduler="{host_specs.scheduler}" cyclethrottle="1" taskthrottle="25">',
               f'\t<log verbosity="10">{HOMEglobal}/sorc/logs/build.log</log>',
               '\t<cycledef group="build">190001010000 190001010000 24:00:00</cycledef>',
               '\n']
    xml_header = '\n'.join(strings)
    xml_footer = '\n</workflow>\n'

    task_list = []
    for _, task_spec in task_specs.items():
        task_list.append(rocoto.create_task(task_spec))
    xml_tasks = '\n'.join(task_list)

    xml = ''.join([xml_header, xml_tasks, xml_footer])
    xml_file = f"{HOMEglobal}/sorc/build.xml"
    with open(xml_file, 'w') as fh:
        fh.write(xml)


if __name__ == '__main__':
    main()
