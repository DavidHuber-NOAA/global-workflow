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
for loader, module_name, is_pkg in pkgutil.iter_modules(['ecflowgw']):
    # Get the list of importable classes with EcFlowSuite in their name
    print(f"Importing module: {module_name}")
    # Skip the ecflow_definitions and ecflow_setup modules as they do not contain EcFlowSuite classes
    # and require access to the ecflow module, which is not guaranteed at this point.
    if module_name == "ecflow_definitions" or module_name == "ecflow_setup":
        continue
    module = import_module(f"ecflowgw.{module_name}")
    class_names = [name for name in dir(module) if "EcFlowSuite" in name]
    for class_name in class_names:
        app_class = getattr(module, class_name)
        # Register application configuration
        # EcFlowSuite classes are expected to be named as <AppName>EcFlowSuite, e.g.,
        # GFSCycledEcFlowSuite
        # Name the registered name as <app_name>_<mode>, e.g., gfs_cycled
        app_name = class_name.split('EcFlowSuite')[0].lower()
        if 'cycled' in class_name.lower():
            mode = 'cycled'
            _class_mode = 'cycled'
        elif 'forecastonly' in class_name.lower():
            mode = 'forecast-only'
            _class_mode = 'forecastonly'
        else:
            # This is most likely a parent class or method. Skip.
            continue

        app = class_name.lower().split('ecflowsuite')[0].split(_class_mode)[0]

        # Actually perform the registration
        ecflow_suite_factory.register(f"{app}_{mode}", app_class)
