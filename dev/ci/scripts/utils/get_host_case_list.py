#!/usr/bin/env python3
import os
import subprocess
import sys
from wxflow import find_upward


def get_host_cases(host, HOMEglobal=None, cases_dir=None):
    """
    Get list of test cases supported on a host.

    This is a thin wrapper around `dev/workflow/generate_workflows.sh -L`,
    which is the single source of truth for resolving which cases are
    supported on a given host (based on each case YAML's `net` and
    `skip_ci_on_hosts` keys). Keeping the CI system driven by
    generate_workflows.sh avoids having a second, independent
    implementation of that selection logic drift out of sync.

    Args:
        host (str): Host name to check (e.g. "hera", "gaeac6")
        HOMEglobal (str, optional): Path to the global-workflow repository root directory
        cases_dir (str, optional): Path to the directory containing case YAMLs.
            Defaults to {HOMEglobal}/dev/ci/cases/pr

    Returns:
        list: List of case names (without extension) supported on the host
    """
    HOMEglobal = HOMEglobal or find_upward('.github')
    cases_dir = cases_dir or os.path.join(HOMEglobal, 'dev', 'ci', 'cases', 'pr')
    generate_workflows = os.path.join(HOMEglobal, 'dev', 'workflow', 'generate_workflows.sh')

    env = os.environ.copy()
    # Force the host of interest regardless of the machine this is run on;
    # generate_workflows.sh -L honors an already-set MACHINE_ID and skips
    # machine (re-)detection.
    env['MACHINE_ID'] = host

    cmd = [
        generate_workflows,
        '-G', '-E', '-S', '-C',  # Consider all systems (gfs, gefs, sfs, gcafs)
        '-L',                    # List-only mode; resolve but don't build/create anything
        '-H', HOMEglobal,
        '-Y', cases_dir,
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"generate_workflows.sh -L failed for host '{host}' (exit {result.returncode}):\n"
            f"{result.stderr}"
        )

    # generate_workflows.sh -L prints informational lines (e.g. "Running all
    # ... cases in ...") in addition to the resolved case names, one per
    # line. Case names are exactly the basenames (no extension) of the YAML
    # files found in cases_dir, so use that to filter out any other output.
    valid_cases = {
        os.path.splitext(name)[0]
        for name in os.listdir(cases_dir)
        if name.endswith('.yaml')
    }

    return [line.strip() for line in result.stdout.splitlines() if line.strip() in valid_cases]


if __name__ == '__main__':
    # When run as a script, maintain the original behavior
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print('Usage: get_host_case_list.py <host_name>')
        sys.exit(1)

    host = sys.argv[1]
    cases = get_host_cases(host)
    print(' '.join(cases))
