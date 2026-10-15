"""
Factory module for application configurations.

This module provides a factory pattern implementation for creating
application configurations for different forecast systems including
GFS, GEFS, SFS, and GCAFS. It registers each application configuration
class with the wxflow Factory to allow dynamic creation based on
application name and mode.

Notes
-----
Uses the wxflow Factory class to register and create application configurations.
Each application has its own configuration class that inherits from AppConfig.
"""

from wxflow import Factory
import pkgutil
from importlib import import_module

# Initialize the application configuration factory
app_config_factory = Factory('AppConfig')

# Go through all of the modules in the applications package and import them dynamically
for loader, module_name, is_pkg in pkgutil.iter_modules(['applications']):
    print(f"Importing module: {module_name}")
    # Get the list of importable classes with AppConfig in their name
    module = import_module(f"applications.{module_name}")
    class_names = [name for name in dir(module) if "AppConfig" in name and name != "AppConfig"]
    for class_name in class_names:
        print(f"Registering application configuration: {class_name}")
        app_class = getattr(module, class_name)
        # Register application configuration
        # AppConfig classes are expected to be named as <AppName>AppConfig, e.g.,
        # GFSCycledAppConfig
        # Name the registered name as <app_name>_<mode>, e.g., gfs_cycled
        app_name = class_name.split('AppConfig')[0].lower()
        if 'cycled' in class_name.lower():
            mode = 'cycled'
            app = class_name.lower().split('appconfig')[0].strip('cycled')
        elif 'forecastonly' in class_name.lower():
            mode = 'forecast-only'
            print(f"{class_name.lower()}")
            print(f"{class_name.lower().split('appconfig')}")
            print(f"{class_name.lower().split('appconfig')[0]}")
            print(f"{class_name.lower().split('appconfig')[0].strip('forecastonly')}")
            app = class_name.lower().split('appconfig')[0].strip('forecastonly')
        else:
            # This is most likely a parent class or method. Skip.
            continue

        # Actually perform the registration
        app_config_factory.register(f"{app}_{mode}", app_class)
        print(f"Registered {app_class} as {app}_{mode} in the factory.")
