#!/usr/bin/env python3

"""
Unit tests for cycle-specific forecast length functionality.

Tests the ability to run different forecast cycles (00z, 06z, 12z, 18z)
to different output lengths across all workflow systems.
"""

import unittest
from rocoto.tasks import Tasks
from wxflow import to_datetime, to_timedelta


class TestCycleSpecificFHMAX(unittest.TestCase):
    """Test cycle-specific FHMAX functionality."""

    def test_get_cycle_specific_fhmax_with_all_cycles(self):
        """Test retrieving cycle-specific FHMAX when all cycles are defined."""
        config = {
            'FHMAX_GFS': 120,
            'FHMAX_GFS_00': 384,
            'FHMAX_GFS_06': 180,
            'FHMAX_GFS_12': 384,
            'FHMAX_GFS_18': 180
        }

        # Test each cycle
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, '00'), 384)
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, '06'), 180)
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, '12'), 384)
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, '18'), 180)

    def test_get_cycle_specific_fhmax_fallback(self):
        """Test fallback to default FHMAX_GFS when cycle-specific not defined."""
        config = {
            'FHMAX_GFS': 120,
        }

        # All cycles should fall back to default
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, '00'), 120)
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, '06'), 120)
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, '12'), 120)
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, '18'), 120)

    def test_get_cycle_specific_fhmax_partial(self):
        """Test partial cycle-specific FHMAX definitions."""
        config = {
            'FHMAX_GFS': 120,
            'FHMAX_GFS_00': 384,
            'FHMAX_GFS_12': 384,
        }

        # Defined cycles use specific values
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, '00'), 384)
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, '12'), 384)

        # Undefined cycles fall back to default
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, '06'), 120)
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, '18'), 120)

    def test_get_cycle_specific_fhmax_none_cycle(self):
        """Test FHMAX retrieval with None cycle parameter."""
        config = {
            'FHMAX_GFS': 120,
            'FHMAX_GFS_00': 384,
        }

        # None should return default
        self.assertEqual(Tasks._get_cycle_specific_fhmax(config, None), 120)

    def test_get_forecast_hours_for_cycle(self):
        """Test forecast hour generation for specific cycles."""
        config = {
            'FHMAX_GFS': 120,
            'FHMAX_GFS_00': 384,
            'FHMAX_GFS_06': 180,
            'FHMAX_HF_GFS': 48,
            'FHOUT_HF_GFS': 3,
            'FHOUT_GFS': 6,
            'FHMIN': 0
        }

        # Test 00z cycle (384 hours)
        fhrs_00 = Tasks._get_forecast_hours_for_cycle('gfs', config, '00', 'atmos')
        self.assertEqual(len(fhrs_00), 73)
        self.assertEqual(fhrs_00[0], 0)
        self.assertEqual(fhrs_00[-1], 384)

        # Test 06z cycle (180 hours)
        fhrs_06 = Tasks._get_forecast_hours_for_cycle('gfs', config, '06', 'atmos')
        self.assertEqual(len(fhrs_06), 39)
        self.assertEqual(fhrs_06[0], 0)
        self.assertEqual(fhrs_06[-1], 180)

    def test_forecast_hours_high_frequency_period(self):
        """Test that high-frequency output is correctly handled."""
        config = {
            'FHMAX_GFS': 120,
            'FHMAX_GFS_00': 384,
            'FHMAX_HF_GFS': 48,
            'FHOUT_HF_GFS': 3,
            'FHOUT_GFS': 6,
            'FHMIN': 0
        }

        fhrs = Tasks._get_forecast_hours_for_cycle('gfs', config, '00', 'atmos')

        # Check high-frequency period (0-48 every 3 hours)
        hf_hours = [fhr for fhr in fhrs if fhr <= 48]
        expected_hf = list(range(0, 51, 3))
        self.assertEqual(hf_hours, expected_hf)

        # Check standard frequency period (48-384 every 6 hours)
        std_hours = [fhr for fhr in fhrs if fhr > 48]
        expected_std = list(range(54, 390, 6))
        self.assertEqual(std_hours, expected_std)

    def test_forecast_hours_ocean_component(self):
        """Test forecast hour generation for ocean component."""
        config = {
            'FHMAX_GFS': 120,
            'FHMAX_GFS_00': 384,
            'FHMAX_HF_GFS': 48,
            'FHOUT_HF_GFS': 3,
            'FHOUT_GFS': 6,
            'FHOUT_OCN_GFS': 6,
            'FHOUT_OCN': 6,
            'FHMIN': 0
        }

        # Ocean should not use high-frequency output
        fhrs_ocean = Tasks._get_forecast_hours_for_cycle('gfs', config, '00', 'ocean')

        # All hours should use standard output frequency
        expected = list(range(0, 390, 6))
        self.assertEqual(fhrs_ocean, expected)


if __name__ == '__main__':
    unittest.main()
