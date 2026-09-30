#!/usr/bin/env python3
"""
Generate a GitLab CI child pipeline for the set of PR-case experiments
that are supported on a given host.

The list of supported cases is resolved entirely from
`dev/workflow/generate_workflows.sh -L` (via get_host_case_list.get_host_cases),
which in turn is driven solely by each case YAML's `net` and
`skip_ci_on_hosts` keys (dev/ci/cases/pr/*.yaml). No host/case support
information is hard-coded here or anywhere else in the GitLab CI
configuration -- this script only arranges the resolved case names into the
job/parallel-matrix structure that GitLab CI requires.

The generated YAML is a self-contained pipeline: it includes the shared
templates it needs (dev/ci/gitlab-ci-templates.yml and
dev/ci/gitlab-ci-cases.yml) and defines `setup_experiments`, `run_experiments`,
and `finalize_success`/`finalize_fail` jobs using a `parallel: matrix:` built
from the resolved case list.
"""
import argparse
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from get_host_case_list import get_host_cases  # noqa: E402


def build_pipeline(host, cases):
    """
    Build the child pipeline dict for a single host's set of resolved cases.

    Args:
        host (str): Host/machine name (e.g. "hera")
        cases (list): List of case names supported on this host

    Returns:
        dict: A GitLab CI pipeline configuration, ready to be dumped as YAML
    """
    pipeline = {
        'include': [
            {'local': 'dev/ci/gitlab-ci-templates.yml'},
            {'local': 'dev/ci/gitlab-ci-cases.yml'},
        ],
        'stages': ['setup_tests', 'run_tests', 'finalize'],
    }

    if not cases:
        # No cases are supported on this host; emit a no-op pipeline rather
        # than an invalid empty parallel:matrix.
        pipeline['no_cases'] = {
            'stage': 'setup_tests',
            'script': [f'echo "No PR cases are supported on {host}; nothing to do."'],
            'rules': [{'when': 'always'}],
        }
        return pipeline

    matrix = [{'caseName': cases}]

    pipeline['setup_experiments'] = {
        'extends': '.setup_experiment_template',
        'variables': {'machine': host},
        'tags': [host],
        'parallel': {'matrix': matrix},
    }

    pipeline['run_experiments'] = {
        'extends': '.run_experiments_template',
        'variables': {'machine': host},
        'tags': [host],
        'needs': ['setup_experiments'],
        'parallel': {'matrix': matrix},
    }

    pipeline['finalize_success'] = {
        'extends': '.finalize_success_template',
        'variables': {'machine': host},
        'tags': [host],
        'needs': [{'job': 'run_experiments', 'optional': True}],
        'when': 'on_success',
    }

    pipeline['finalize_fail'] = {
        'extends': '.finalize_fail_template',
        'variables': {'machine': host},
        'tags': [host],
        'needs': [{'job': 'run_experiments', 'optional': True}],
        'when': 'on_failure',
    }

    return pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, help='Host/machine name (e.g. hera)')
    parser.add_argument('--homeglobal', default=None,
                         help='Path to the global-workflow repository root (default: auto-detected)')
    parser.add_argument('--cases-dir', default=None,
                         help='Path to the directory of case YAMLs (default: {homeglobal}/dev/ci/cases/pr)')
    parser.add_argument('--output', default=None,
                         help='Output file for the generated pipeline YAML (default: stdout)')
    args = parser.parse_args()

    cases = get_host_cases(args.host, HOMEglobal=args.homeglobal, cases_dir=args.cases_dir)
    pipeline = build_pipeline(args.host, cases)

    yaml_text = yaml.safe_dump(pipeline, sort_keys=False, default_flow_style=False)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(yaml_text)
        print(f"Wrote generated pipeline for host '{args.host}' ({len(cases)} case(s)) to {args.output}")
    else:
        print(yaml_text)


if __name__ == '__main__':
    main()
