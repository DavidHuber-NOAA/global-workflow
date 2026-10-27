"""
pygfs
=====

This package provides task classes and utilities for the GFS workflow, including analysis, chemistry, ensemble, marine, snow, and forecast processing.

Modules
-------
- task.analysis: Analysis task
- task.chem_fire_emission: Chemistry fire emissions task
- task.nxs_emission: NEXUS emissions task
- task.aero_analysis: Aerosol analysis task
- task.aero_bmatrix: Aerosol background matrix task
- task.atm_analysis: Atmospheric analysis task
- task.atmens_analysis: Atmospheric ensemble analysis task
- task.ensemble_recenter: Ensemble recentering task
- task.fv3_analysis_calc: FV3 analysis calculation task
- task.marine_bmat: Marine background matrix task
- task.offline_analysis: Offline analysis task
- task.snow_analysis: Snow analysis task
- task.snowens_analysis: Snow ensemble analysis task
- task.upp: Unified Post Processor (UPP) task
- task.oceanice_products: Ocean/ice products task
- task.gfs_forecast: GFS forecast task
- utils.marine_da_utils: Marine data assimilation utilities
- task.fetch: Fetch task

Attributes
----------
__docformat__ : str
    The documentation format for the module.
__version__ : str
    The version of the pygfs package.
pygfs_directory : str
    The absolute path to the pygfs package directory.
"""

import os
from importlib import import_module

# Task classes are imported on first use so that a filtered (HWD tier) repository
# does not need the modules of the tasks it does not support.
_task_modules = {
    'Analysis': '.task.analysis',
    'ChemFireEmissions': '.task.chem_fire_emission',
    'NEXUSEmissions': '.task.nexus_emission',
    'AerosolAnalysis': '.task.aero_analysis',
    'AerosolBMatrix': '.task.aero_bmatrix',
    'AtmAnalysis': '.task.atm_analysis',
    'AtmEnsAnalysis': '.task.atmens_analysis',
    'EnsembleRecenter': '.task.ensemble_recenter',
    'FV3AnalysisCalc': '.task.fv3_analysis_calc',
    'MarineBMat': '.task.marine_bmat',
    'OfflineAnalysis': '.task.offline_analysis',
    'SnowAnalysis': '.task.snow_analysis',
    'SnowEnsAnalysis': '.task.snowens_analysis',
    'UPP': '.task.upp',
    'OceanIceProducts': '.task.oceanice_products',
    'GFSForecast': '.task.gfs_forecast',
    'Fetch': '.task.fetch',
    'MarineRecenter': '.task.marine_recenter',
}


def __getattr__(name):
    """Import a task class lazily when it is first accessed."""
    if name == 'marine_da_utils':
        return import_module('.utils.marine_da_utils', __name__)
    if name in _task_modules:
        return getattr(import_module(_task_modules[name], __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__docformat__ = "restructuredtext"
__version__ = "0.1.0"
pygfs_directory = os.path.dirname(__file__)
