# CI Case Configuration Guide

## Overview

The CI test case configuration for the Global Workflow uses a **single source of truth** approach where individual case YAML files define which hosts should skip each test case. The host-specific test matrices in `gitlab-ci-hosts.yml` are automatically generated from these case configurations.

## Single Source of Truth

**Case YAML files** (`dev/ci/cases/pr/*.yaml`) are the authoritative source for test case configurations. Each case file can optionally include a `skip_ci_on_hosts` section listing which computing platforms should NOT run that test case.

### Example Case Configuration

```yaml
experiment:
  net: gfs
  mode: cycled
  pslot: {{ 'pslot' | getenv }}
  app: ATM
  # ... other experiment settings ...

skip_ci_on_hosts:
  - orion
  - hercules
  - awsepicglobalworkflow

workflow:
  engine: rocoto
  # ... workflow settings ...
```

In this example, the test case will run on all configured hosts EXCEPT `orion`, `hercules`, and `awsepicglobalworkflow`.

## Adding a New Test Case

To add a new CI test case:

1. **Create the case YAML file** in `dev/ci/cases/pr/`
   - Follow the naming convention: `<descriptive_name>.yaml`
   - Include all required experiment configuration
   
2. **Add skip_ci_on_hosts section** (if needed)
   - List any hosts that should NOT run this case
   - Omit this section if the case should run on all hosts

3. **Regenerate the GitLab host matrices**
   ```bash
   python dev/ci/scripts/utils/generate_host_case_matrix.py --update
   ```

4. **Verify the changes**
   ```bash
   git diff dev/ci/gitlab-ci-hosts.yml
   ```

5. **Commit both files**
   ```bash
   git add dev/ci/cases/pr/<your_case>.yaml dev/ci/gitlab-ci-hosts.yml
   git commit -m "Add new test case: <your_case>"
   ```

## Modifying Host Support for Existing Cases

To change which hosts run an existing test case:

1. **Edit the case YAML file** (`dev/ci/cases/pr/<case_name>.yaml`)
   - Add or remove hosts from the `skip_ci_on_hosts` list
   - Add the section if it doesn't exist
   - Remove the section if the case should run on all hosts

2. **Regenerate the GitLab host matrices**
   ```bash
   python dev/ci/scripts/utils/generate_host_case_matrix.py --update
   ```

3. **Verify and commit changes**
   ```bash
   git diff dev/ci/cases/pr/<case_name>.yaml dev/ci/gitlab-ci-hosts.yml
   git add dev/ci/cases/pr/<case_name>.yaml dev/ci/gitlab-ci-hosts.yml
   git commit -m "Update host support for <case_name>"
   ```

## generate_host_case_matrix.py Script

This utility script generates the host case matrices in `gitlab-ci-hosts.yml` from the individual case YAML files.

### Usage

```bash
# View generated matrices (stdout)
python dev/ci/scripts/utils/generate_host_case_matrix.py

# Save to a file
python dev/ci/scripts/utils/generate_host_case_matrix.py --output matrices.yml

# Update gitlab-ci-hosts.yml directly
python dev/ci/scripts/utils/generate_host_case_matrix.py --update

# Dry run to see what would change
python dev/ci/scripts/utils/generate_host_case_matrix.py --update --dry-run

# Generate for specific hosts only
python dev/ci/scripts/utils/generate_host_case_matrix.py --hosts hera orion
```

### How It Works

1. Discovers all test case YAML files in `dev/ci/cases/pr/`
2. Parses the `skip_ci_on_hosts` section from each case
3. For each configured host, builds a list of cases that don't skip that host
4. Generates YAML anchor definitions (`.hostname_cases_matrix: &hostname_cases`)
5. Updates the matrices section in `gitlab-ci-hosts.yml`

### Auto-Detection of Hosts

By default, the script auto-detects which hosts to generate matrices for by reading the existing host definitions in `gitlab-ci-hosts.yml`. This ensures consistency with the GitLab CI pipeline configuration.

## Local Testing with generate_workflows.sh

The `generate_workflows.sh` script automatically respects the `skip_ci_on_hosts` configuration when selecting test cases to run locally. No additional changes are needed - the script uses the `get_host_case_list.py` utility which reads the skip tags directly from case YAML files.

### Example Local Usage

```bash
# Run all GFS cases supported on the current machine
./dev/workflow/generate_workflows.sh -G /path/to/RUNTESTS

# Run specific cases (will skip unsupported ones with a warning)
./dev/workflow/generate_workflows.sh -y "C48_ATM C96_atm3DVar" /path/to/RUNTESTS
```

## CI Validation

The `test_ci_matrix_validation.py` unit test ensures that the matrices in `gitlab-ci-hosts.yml` remain consistent with the `skip_ci_on_hosts` tags in case files. This test will fail if:

- A host's matrix includes a case that has that host in its skip list
- A host's matrix is missing a case that should run on that host

Run the validation test:
```bash
pytest dev/ci/scripts/unittests/test_ci_matrix_validation.py -v
```

## Architecture Benefits

This single source of truth approach provides several advantages:

1. **Consistency**: Both local testing and GitLab CI use the same configuration
2. **Maintainability**: Only one location to update when adding or modifying cases
3. **Validation**: Automated tests ensure matrices stay in sync with case configurations
4. **Clarity**: Easy to see which hosts support each test case
5. **Automation**: Generate matrices automatically with a simple command

## Troubleshooting

### Matrix validation test failing

If `test_ci_matrix_validation.py` fails, it means the matrices in `gitlab-ci-hosts.yml` are out of sync with the case configurations:

```bash
# Regenerate matrices
python dev/ci/scripts/utils/generate_host_case_matrix.py --update

# Re-run validation
pytest dev/ci/scripts/unittests/test_ci_matrix_validation.py -v
```

### Case not running on expected host

1. Check the `skip_ci_on_hosts` section in the case YAML
2. Verify the host name matches exactly (case-sensitive)
3. Ensure matrices were regenerated after modifying the case
4. Check GitLab CI pipeline rules in `gitlab-ci-hosts.yml`

### Script reports "Could not find case matrix section"

The script expects a specific structure in `gitlab-ci-hosts.yml`. Ensure:
- The comment line `# Template matrices for case lists` exists
- Matrix definitions follow immediately after
- The `# Host: ` section markers are present

## Adding a New Host Platform

To add support for a new computing platform:

1. **Add the host to GitLab CI configuration** (`dev/ci/gitlab-ci-hosts.yml`)
   - Add build, setup, and run job definitions
   - Include the new host in the appropriate sections

2. **Add an empty matrix definition** for the new host:
   ```yaml
   .newhost_cases_matrix: &newhost_cases
     - caseName: []
   ```

3. **Generate matrices** to populate cases for the new host:
   ```bash
   python dev/ci/scripts/utils/generate_host_case_matrix.py --update
   ```

4. **Update case files** if any should skip the new host:
   - Edit relevant case YAMLs to add the new host to their skip lists
   - Regenerate matrices again

## Related Files

- `dev/ci/cases/pr/*.yaml` - Individual test case configurations (source of truth)
- `dev/ci/gitlab-ci-hosts.yml` - GitLab CI pipeline with generated host matrices
- `dev/ci/scripts/utils/generate_host_case_matrix.py` - Matrix generation script
- `dev/ci/scripts/utils/get_host_case_list.py` - Utility to get cases for a host
- `dev/ci/scripts/unittests/test_ci_matrix_validation.py` - Validation tests
- `dev/workflow/generate_workflows.sh` - Local experiment setup script
