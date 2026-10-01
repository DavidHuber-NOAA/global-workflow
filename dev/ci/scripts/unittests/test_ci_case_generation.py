"""
Unit tests for dynamic GitLab CI per-host case generation.

The GitLab CI pipeline no longer hand-maintains a static "which case runs on
which host" matrix. Instead, each host's case list is resolved at pipeline
run-time by `dev/workflow/generate_workflows.sh -L`, driven solely by each
case YAML's `skip_ci_on_hosts` key (dev/ci/cases/pr/*.yaml). These tests
validate that:
    - `get_host_case_list.get_host_cases()` (a thin wrapper around
      `generate_workflows.sh -L`) agrees with a simple, independent
      `skip_ci_on_hosts` parse for every known CI host
    - `generate_case_pipeline.build_pipeline()` turns a resolved case list
      into a valid GitLab CI child-pipeline structure
    - Adding/removing a host from a case's `skip_ci_on_hosts` list changes
      the resolved case list for that host accordingly
"""

import re
import sys
from pathlib import Path
from typing import Set

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'utils'))

from generate_case_pipeline import build_pipeline  # noqa: E402
from get_host_case_list import get_host_cases  # noqa: E402

# Hosts currently wired into dev/ci/gitlab-ci-hosts.yml
KNOWN_HOSTS = ['hera', 'gaeac6', 'orion', 'hercules', 'ursa', 'derecho']


def get_repo_root() -> Path:
    """Find repository root by looking for the .github directory."""
    for parent in [Path(__file__).resolve()] + list(Path(__file__).resolve().parents):
        if (parent / '.github').exists():
            return parent
    raise FileNotFoundError("Could not find repository root (.github directory)")


def extract_skip_hosts(case_file: Path) -> Set[str]:
    """
    Independently extract skip_ci_on_hosts from a case YAML file via regex,
    avoiding Jinja2 templating issues with full YAML parsing.
    """
    content = case_file.read_text()
    match = re.search(r'skip_ci_on_hosts:\s*\n((?:\s*-\s*\S+\s*\n)*)', content)
    if match:
        try:
            parsed = yaml.safe_load("skip_ci_on_hosts:\n" + match.group(1))
            skip_hosts = parsed.get('skip_ci_on_hosts', [])
            return set(skip_hosts) if skip_hosts else set()
        except yaml.YAMLError:
            pass
    return set()


@pytest.fixture(scope="module")
def repo_root() -> Path:
    return get_repo_root()


@pytest.fixture(scope="module")
def cases_dir(repo_root) -> Path:
    return repo_root / 'dev' / 'ci' / 'cases' / 'pr'


def expected_cases_for_host(host: str, cases_dir: Path) -> Set[str]:
    """Build the expected case list for a host purely from skip_ci_on_hosts tags."""
    expected = set()
    for case_file in sorted(cases_dir.glob('*.yaml')):
        if host not in extract_skip_hosts(case_file):
            expected.add(case_file.stem)
    return expected


@pytest.mark.parametrize("host", KNOWN_HOSTS)
def test_get_host_cases_matches_skip_ci_on_hosts(host, repo_root, cases_dir):
    """
    The resolved case list from generate_workflows.sh -L (via get_host_cases)
    must exactly match an independent skip_ci_on_hosts-based computation.
    """
    resolved = set(get_host_cases(host, HOMEglobal=str(repo_root), cases_dir=str(cases_dir)))
    expected = expected_cases_for_host(host, cases_dir)

    assert resolved == expected, (
        f"Resolved case list for host '{host}' does not match skip_ci_on_hosts tags.\n"
        f"Extra (resolved but should be skipped): {sorted(resolved - expected)}\n"
        f"Missing (should run but was not resolved): {sorted(expected - resolved)}"
    )


def test_get_host_cases_respects_new_skip_tag(repo_root, cases_dir, tmp_path):
    """
    Adding a host to a case's skip_ci_on_hosts list must remove that case
    from the host's resolved list; removing the tag must restore it.
    """
    host = KNOWN_HOSTS[0]
    resolved_before = set(get_host_cases(host, HOMEglobal=str(repo_root), cases_dir=str(cases_dir)))
    assert resolved_before, f"Expected at least one case to run on {host} before mutation"

    test_case_name = sorted(resolved_before)[0]
    test_case_file = cases_dir / f'{test_case_name}.yaml'
    original_content = test_case_file.read_text()

    if 'skip_ci_on_hosts:' in original_content:
        modified_content = original_content.replace(
            'skip_ci_on_hosts:', f'skip_ci_on_hosts:\n  - {host}', 1)
    elif 'workflow:' in original_content:
        # generate_workflows.sh locates skip_ci_on_hosts via
        # `sed '1,/skip_ci_on_hosts/ d'`, which deletes the entire file if
        # the pattern is placed on line 1, so it must not be inserted at the
        # very top of the file.
        modified_content = original_content.replace(
            'workflow:', f'skip_ci_on_hosts:\n  - {host}\n\nworkflow:', 1)
    else:
        modified_content = original_content + f'\nskip_ci_on_hosts:\n  - {host}\n'

    try:
        test_case_file.write_text(modified_content)
        resolved_after = set(get_host_cases(host, HOMEglobal=str(repo_root), cases_dir=str(cases_dir)))
        assert test_case_name not in resolved_after, (
            f"'{test_case_name}' should have been excluded for host '{host}' "
            f"after adding it to skip_ci_on_hosts"
        )
    finally:
        test_case_file.write_text(original_content)

    resolved_restored = set(get_host_cases(host, HOMEglobal=str(repo_root), cases_dir=str(cases_dir)))
    assert test_case_name in resolved_restored, "Case should be restored after reverting skip_ci_on_hosts"


@pytest.mark.parametrize("host", KNOWN_HOSTS)
def test_build_pipeline_structure(host, repo_root, cases_dir):
    """The generated child pipeline dict must be well-formed GitLab CI YAML."""
    cases = sorted(expected_cases_for_host(host, cases_dir))
    pipeline = build_pipeline(host, cases)

    # Must round-trip through YAML cleanly
    dumped = yaml.safe_dump(pipeline, sort_keys=False)
    reloaded = yaml.safe_load(dumped)
    assert reloaded == pipeline

    assert 'include' in pipeline
    assert 'stages' in pipeline

    if cases:
        assert pipeline['setup_experiments']['parallel']['matrix'] == [{'caseName': cases}]
        assert pipeline['run_experiments']['parallel']['matrix'] == [{'caseName': cases}]
        assert pipeline['setup_experiments']['variables']['machine'] == host
        assert pipeline['finalize_success']['when'] == 'on_success'
        assert pipeline['finalize_fail']['when'] == 'on_failure'
    else:
        assert 'no_cases' in pipeline


def test_build_pipeline_handles_zero_cases():
    """A host with no supported cases must emit a valid no-op pipeline."""
    pipeline = build_pipeline('nohost', [])
    assert 'no_cases' in pipeline
    assert 'setup_experiments' not in pipeline
    yaml.safe_dump(pipeline)  # must not raise
