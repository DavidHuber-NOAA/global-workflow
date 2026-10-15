"""
Factory for creating ecFlow suite generators.

This module provides a factory that creates appropriate ecFlow suites
for different types of workflows (GFS, GEFS, SFS, GCAFS).
"""
from wxflow import Factory
import pkgutil
from importlib import import_module

# Create a factory for ecFlow suite objects
ecflow_suite_factory = Factory('ecFlowSuite')

# Go through all of the modules in the ecflow package and import them dynamically
for loader, module_name, is_pkg in pkgutil.iter_modules(['rocoto']):
    if "EcFlowSuite" in module_name:
        import_module(f"ecflow.{module_name}")
        # Register application configuration
        # EcFlowSuite classes are expected to be named as <AppName>EcFlowSuite, e.g.,
        # GFSCycledEcFlowSuite
        # Name the registered name as <app_name>_<mode>, e.g., gfs_cycled
        app_name = module_name.split('EcFlowSuite')[0].lower()
        if 'cycled' in module_name.lower():
            mode = 'cycled'
        elif 'forecastonly' in module_name.lower():
            mode = 'forecast-only'
        else:
            raise ValueError(f"Unknown mode for rocoto configuration: {module_name}")

        # Determine the app name by removing the mode and 'ecflowsuite' from the module name
        # The mode's registered name is hyphenated, so strip the hyphen
        app = module_name.lower().split('ecflowsuite')[0].split(mode.strip('-'))[0]
        app_class = getattr(import_module(f"ecflow.{module_name}"), f"{module_name}")
        # Actually perform the registration
        app_config_factory.register(f"{app}_{mode}", app_class)
