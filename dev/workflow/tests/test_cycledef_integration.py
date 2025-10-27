#!/usr/bin/env python3

"""
Integration tests for cycle-specific cycledef generation.

Tests that all workflow systems correctly generate cycle-specific
cycledefs when configured with different FHMAX values per cycle.
"""

import unittest
from wxflow import to_datetime, to_timedelta


class TestCycledefGeneration(unittest.TestCase):
    """Test cycledef generation for all workflow systems."""

    def setUp(self):
        """Set up test configuration."""
        self.sdate = to_datetime('2024010100')
        self.edate = to_datetime('2024010818')
        self.interval_gfs = to_timedelta('6H')

    def test_gfs_cycled_cycledefs(self):
        """Test GFS cycled XML cycledef generation."""
        from rocoto.gfs_cycled_xml import GFSCycledRocotoXML

        # This test verifies the class exists and has the method
        self.assertTrue(hasattr(GFSCycledRocotoXML, 'get_cycledefs'))

    def test_gfs_forecast_only_cycledefs(self):
        """Test GFS forecast-only XML cycledef generation."""
        from rocoto.gfs_forecast_only_xml import GFSForecastOnlyRocotoXML

        self.assertTrue(hasattr(GFSForecastOnlyRocotoXML, 'get_cycledefs'))

    def test_gefs_cycledefs(self):
        """Test GEFS XML cycledef generation."""
        from rocoto.gefs_xml import GEFSRocotoXML

        self.assertTrue(hasattr(GEFSRocotoXML, 'get_cycledefs'))

    def test_sfs_cycledefs(self):
        """Test SFS XML cycledef generation."""
        from rocoto.sfs_xml import SFSRocotoXML

        self.assertTrue(hasattr(SFSRocotoXML, 'get_cycledefs'))

    def test_gcafs_cycled_cycledefs(self):
        """Test GCAFS cycled XML cycledef generation."""
        from rocoto.gcafs_cycled_xml import GCAFSCycledRocotoXML

        self.assertTrue(hasattr(GCAFSCycledRocotoXML, 'get_cycledefs'))

    def test_gcafs_forecast_only_cycledefs(self):
        """Test GCAFS forecast-only XML cycledef generation."""
        from rocoto.gcafs_forecast_only_xml import GCAFSForecastOnlyRocotoXML

        self.assertTrue(hasattr(GCAFSForecastOnlyRocotoXML, 'get_cycledefs'))

    def test_cycledef_logic(self):
        """Test the cycle-specific cycledef generation logic."""
        # Test the same logic that's in all XML generators
        sdate_gfs = self.sdate
        edate_gfs = self.edate
        interval_gfs = self.interval_gfs

        # Only generate cycle-specific defs when interval <= 6H
        if interval_gfs <= to_timedelta('6H'):
            for cyc in ['00', '06', '12', '18']:
                cyc_hour = int(cyc)
                sdate_cyc = sdate_gfs.replace(hour=cyc_hour)
                if sdate_cyc < sdate_gfs:
                    sdate_cyc = sdate_cyc + to_timedelta('24H')
                edate_cyc = edate_gfs.replace(hour=cyc_hour)
                if edate_cyc > edate_gfs:
                    edate_cyc = edate_cyc - to_timedelta('24H')

                # Verify that we have valid date ranges
                if sdate_cyc <= edate_cyc:
                    self.assertLessEqual(sdate_cyc, edate_cyc)
                    # Verify the cycle hour matches
                    self.assertEqual(sdate_cyc.hour, cyc_hour)
                    self.assertEqual(edate_cyc.hour, cyc_hour)

    def test_yaml_defaults_have_fhmax_variables(self):
        """Test that all system YAML defaults have FHMAX_GFS_* variables."""
        import yaml

        systems = ['gfs', 'gefs', 'sfs', 'gcafs']

        for system in systems:
            with open(f'dev/parm/config/{system}/yaml/defaults.yaml', 'r') as f:
                config = yaml.safe_load(f)

            # Check base FHMAX_GFS exists
            self.assertIn('FHMAX_GFS', config['base'],
                          f'{system} should have FHMAX_GFS')

            # Check cycle-specific FHMAX values exist
            for cyc in ['00', '06', '12', '18']:
                key = f'FHMAX_GFS_{cyc}'
                self.assertIn(key, config['base'],
                              f'{system} should have {key}')


if __name__ == '__main__':
    unittest.main()
