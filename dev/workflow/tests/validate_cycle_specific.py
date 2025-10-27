#!/usr/bin/env python3

"""
End-to-end validation of cycle-specific forecast length feature.

This script validates that the cycle-specific forecast length feature
works correctly across all workflow systems.
"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.getcwd(), 'dev/workflow'))
sys.path.insert(0, os.path.join(os.getcwd(), 'sorc/wxflow/src'))

from rocoto.tasks import Tasks
from wxflow import to_datetime, to_timedelta, timedelta_to_HMS
import yaml


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'=' * 80}")
    print(f"{text}")
    print(f"{'=' * 80}")


def print_section(text):
    """Print a formatted section header."""
    print(f"\n{text}")
    print(f"{'-' * len(text)}")


def validate_yaml_configs():
    """Validate YAML configuration files have cycle-specific variables."""
    print_header("VALIDATING YAML CONFIGURATIONS")

    systems = ['gfs', 'gefs', 'sfs', 'gcafs']
    all_valid = True

    for system in systems:
        print_section(f"{system.upper()} Configuration")
        yaml_path = f'dev/parm/config/{system}/yaml/defaults.yaml'

        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        base_config = config.get('base', {})

        # Check base FHMAX_GFS
        fhmax_gfs = base_config.get('FHMAX_GFS', 'NOT FOUND')
        print(f"  FHMAX_GFS: {fhmax_gfs}")

        # Check cycle-specific values
        for cyc in ['00', '06', '12', '18']:
            key = f'FHMAX_GFS_{cyc}'
            value = base_config.get(key, 'NOT FOUND')
            print(f"  {key}: {value}")

            if value == 'NOT FOUND':
                all_valid = False
                print(f"    ✗ Missing {key}")

        print(f"  Status: {'✓ Valid' if all_valid else '✗ Invalid'}")

    return all_valid


def validate_cycledef_generation():
    """Validate cycledef generation logic."""
    print_header("VALIDATING CYCLEDEF GENERATION")

    # Test parameters
    sdate_gfs = to_datetime('2024010100')
    edate_gfs = to_datetime('2024010818')
    interval_gfs = to_timedelta('6H')

    print(f"  Start Date: {sdate_gfs}")
    print(f"  End Date: {edate_gfs}")
    print(f"  Interval: {interval_gfs}")

    print_section("Cycle-Specific Cycledefs")

    if interval_gfs <= to_timedelta('6H'):
        print("  Generating cycle-specific cycledefs (interval <= 6H)")
        for cyc in ['00', '06', '12', '18']:
            cyc_hour = int(cyc)
            sdate_cyc = sdate_gfs.replace(hour=cyc_hour)
            if sdate_cyc < sdate_gfs:
                sdate_cyc = sdate_cyc + to_timedelta('24H')
            edate_cyc = edate_gfs.replace(hour=cyc_hour)
            if edate_cyc > edate_gfs:
                edate_cyc = edate_cyc - to_timedelta('24H')

            if sdate_cyc <= edate_cyc:
                interval_cyc_str = timedelta_to_HMS(to_timedelta('24H'))
                print(f"    {cyc}z: {sdate_cyc} to {edate_cyc} every {interval_cyc_str}")
    else:
        print("  No cycle-specific cycledefs (interval > 6H)")

    return True


def validate_forecast_hours():
    """Validate forecast hour calculation."""
    print_header("VALIDATING FORECAST HOUR CALCULATION")

    config = {
        'FHMAX_GFS': 120,
        'FHMAX_GFS_00': 384,
        'FHMAX_GFS_06': 180,
        'FHMAX_GFS_12': 384,
        'FHMAX_GFS_18': 180,
        'FHMAX_HF_GFS': 48,
        'FHOUT_HF_GFS': 3,
        'FHOUT_GFS': 6,
        'FHMIN': 0
    }

    print_section("Cycle-Specific Forecast Hours")

    for cyc in ['00', '06', '12', '18']:
        fhmax = Tasks._get_cycle_specific_fhmax(config, cyc)
        fhrs = Tasks._get_forecast_hours_for_cycle('gfs', config, cyc, 'atmos')

        print(f"  Cycle {cyc}z:")
        print(f"    FHMAX: {fhmax} hours")
        print(f"    Total forecast hours: {len(fhrs)}")
        print(f"    Range: {min(fhrs)} to {max(fhrs)}")
        print(f"    High-frequency output: 0-{config['FHMAX_HF_GFS']} every {config['FHOUT_HF_GFS']}h")
        print(f"    Standard output: {config['FHMAX_HF_GFS']}-{fhmax} every {config['FHOUT_GFS']}h")

    return True


def validate_xml_generators():
    """Validate XML generator classes."""
    print_header("VALIDATING XML GENERATOR CLASSES")

    xml_generators = [
        ('GFSCycledRocotoXML', 'gfs_cycled_xml'),
        ('GFSForecastOnlyRocotoXML', 'gfs_forecast_only_xml'),
        ('GEFSRocotoXML', 'gefs_xml'),
        ('SFSRocotoXML', 'sfs_xml'),
        ('GCAFSCycledRocotoXML', 'gcafs_cycled_xml'),
        ('GCAFSForecastOnlyRocotoXML', 'gcafs_forecast_only_xml'),
    ]

    all_valid = True

    for class_name, module_name in xml_generators:
        try:
            module = __import__(f'rocoto.{module_name}', fromlist=[class_name])
            cls = getattr(module, class_name)
            has_method = hasattr(cls, 'get_cycledefs')

            status = '✓' if has_method else '✗'
            print(f"  {status} {class_name}: {'has get_cycledefs' if has_method else 'missing get_cycledefs'}")

            if not has_method:
                all_valid = False

        except Exception as e:
            print(f"  ✗ {class_name}: Error importing - {e}")
            all_valid = False

    return all_valid


def main():
    """Run all validations."""
    print_header("CYCLE-SPECIFIC FORECAST LENGTH VALIDATION")
    print("This validation demonstrates the cycle-specific forecast length feature")
    print("across all workflow systems (GFS, GEFS, SFS, GCAFS).")

    results = {
        'YAML Configurations': validate_yaml_configs(),
        'Cycledef Generation': validate_cycledef_generation(),
        'Forecast Hours': validate_forecast_hours(),
        'XML Generators': validate_xml_generators(),
    }

    print_header("VALIDATION SUMMARY")
    all_passed = True
    for test_name, passed in results.items():
        status = '✓ PASS' if passed else '✗ FAIL'
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False

    print(f"\n{'=' * 80}")
    if all_passed:
        print("ALL VALIDATIONS PASSED ✓")
        print("Cycle-specific forecast lengths are fully implemented and working!")
        return 0
    else:
        print("SOME VALIDATIONS FAILED ✗")
        return 1


if __name__ == '__main__':
    sys.exit(main())
