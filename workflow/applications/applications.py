#!/usr/bin/env python3

from typing import Dict, List, Any
from datetime import timedelta
from hosts import Host
from wxflow import Configuration, to_timedelta
from abc import ABC, ABCMeta, abstractmethod

__all__ = ['AppConfig']


class AppConfigInit(ABCMeta):
    def __call__(cls, *args, **kwargs):
        '''
        We want the child classes to be able to define additional settings
          before we source the configs and complete the rest of the process,
          so break init up into two methods, one to run first (both in the
          base class and the child class) and one to finalize the initiali-
          zation after both have completed.
        '''
        obj = type.__call__(cls, *args, **kwargs)
        obj._init_finalize(*args, **kwargs)
        return obj


class AppConfig(ABC, metaclass=AppConfigInit):

    VALID_MODES = ['cycled', 'forecast-only']

    def __init__(self, conf: Configuration) -> None:

        self.scheduler = Host().scheduler

        _base = conf.parse_config('config.base')
        # Define here so the child __init__ functions can use it; will
        # be overwritten later during _init_finalize().
        self._base = _base

        self.mode = _base['MODE']

        if self.mode not in self.VALID_MODES:
            raise NotImplementedError(f'{self.mode} is not a valid application mode.\n' +
                                      'Valid application modes are:\n' +
                                      f'{", ".join(self.VALID_MODES)}')

        self.net = _base['NET']
        self.model_app = _base.get('APP', 'ATM')
        self.do_atm = _base.get('DO_ATM', True)
        self.do_wave = _base.get('DO_WAVE', False)
        self.do_wave_bnd = _base.get('DOBNDPNT_WAVE', False)
        self.do_ocean = _base.get('DO_OCN', False)
        self.do_ice = _base.get('DO_ICE', False)
        self.do_aero = _base.get('DO_AERO', False)
        self.do_bufrsnd = _base.get('DO_BUFRSND', False)
        self.do_gempak = _base.get('DO_GEMPAK', False)
        self.do_awips = _base.get('DO_AWIPS', False)
        self.do_verfozn = _base.get('DO_VERFOZN', True)
        self.do_verfrad = _base.get('DO_VERFRAD', True)
        self.do_vminmon = _base.get('DO_VMINMON', True)
        self.do_tracker = _base.get('DO_TRACKER', True)
        self.do_genesis = _base.get('DO_GENESIS', True)
        self.do_genesis_fsu = _base.get('DO_GENESIS_FSU', False)
        self.do_metp = _base.get('DO_METP', False)
        self.do_upp = not _base.get('WRITE_DOPOST', True)
        self.do_goes = _base.get('DO_GOES', False)
        self.do_mos = _base.get('DO_MOS', False)

        self.do_hpssarch = _base.get('HPSSARCH', False)

        self.nens = _base.get('NMEM_ENS', 0)

        self.wave_cdumps = None
        if self.do_wave:
            wave_cdump = _base.get('WAVE_CDUMP', 'BOTH').lower()
            if wave_cdump in ['both']:
                self.wave_cdumps = ['gfs', 'gdas']
            elif wave_cdump in ['gfs', 'gdas']:
                self.wave_cdumps = [wave_cdump]

    def _init_finalize(self, conf: Configuration):
        print("Finalizing initialize")

        # Get a list of all possible config_files that would be part of the application
        self.configs_names = self._get_app_configs()

        # Source the config_files for the jobs in the application
        self.configs = self._source_configs(conf, verbose=False)

        # Update the base config dictionary base on application
        self.configs['base'] = self._update_base(self.configs['base'])

        # Save base in the internal state since it is often needed
        self._base = self.configs['base']

        # Get more configuration options into the class attributes
        self.gfs_cyc = self._base.get('gfs_cyc')

        # Get task names for the application
        self.task_names = self.get_task_names()

        # Populate configs with resource definitions
        self.task_name_configs = self._populate_task_configs()

        # Finally, re-source the config files
        self.configs = self._source_configs(conf, verbose=True)

    def _populate_task_configs(self, resource_yaml='resources.yaml.j2'):
        """
        Add task-specific information to the configuration files
        Inputs:
        -------
        """

        expdir = self._base["EXPDIR"]
        yaml_filename = os.path.join(expdir, "resources.yaml.j2")

        resources = parse_j2yaml(yaml_filename,
                                 self._base,
                                 allow_missing=False)

        if not resources['check_configuration']['valid']:
            conf = resources['check_configuration']
            for key in conf if "valid_" in key and not conf[key]:
                component = key.replace("valid_", "")
                print(conf["reason_" + component])

            raise ValueError("Invalid configuration specified in config.base.")

        for run in self.task_names.keys():
            for task in self.task_names[run]:
                # Construct the config filename
                config_name = os.path.join(expdir, "config." + task)

                # Get the run- and task-specific variables from the parsed yaml
                variables = {}
                task_vars = resources[task]
                variables.update(task_vars["parameters"]) if "parameters" in task_vars
                variables.update(task_vars[run]) if run in task_vars

                # Check that resources were defined
                if len(variables) == 0:
                    raise ValueError(
                      f"No resources are defined for task {task_name} in {yaml_filename}")
                elif "num_PEs" not in variables:
                    raise KeyError(
                      f"{yaml_filename} does not define PE count for {task_name}")
                elif "walltime" not in variables:
                    raise KeyError(
                      f"{yaml_filename} does not define walltime for {task_name}")

                # Add the definitions to the top of the config file after the shebang
                # Read the entirety of the config file
                with open(config_path, 'r') as cfg_file:
                    config_contents = cfg_file.readlines

                # Add the new definitions starting on line 2
                index = 1
                config_contents.insert(index, "if [[ ${RUN} == " + RUN + " ]]; then\n")
                index += 1
                for variable, value in variables.items():
                    config_contents.insert(index, f"export {variable}={value}\n")
                    index += 1

                config_contents.insert(index, "fi\n")

                with open(config_path, "w") as cfg_file:
                    cfg_file.writelines(config_contents)

    @abstractmethod
    def _get_app_configs(self):
        pass

    @staticmethod
    @abstractmethod
    def _update_base(base_in: Dict[str, Any]) -> Dict[str, Any]:
        '''
        Make final updates to base and return an updated copy

        Parameters
        ----------
        base_in: Dict
                 Beginning base settings

        Returns
        -------
        Dict: A copy of base_in with possible modifications based on the
              net and mode.

        '''
        pass

    def _source_configs(self, conf: Configuration, verbose=False) -> Dict[str, Any]:
        """
        Given the configuration object and jobs,
        source the configurations for each config and return a dictionary
        Every config depends on "config.base"
        """

        configs = dict()

        # Return config.base as well
        configs['base'] = conf.parse_config('config.base')

        # Source the list of all config_files involved in the application
        for config in self.configs_names:

            # All must source config.base first
            files = ['config.base']

            if config in ['eobs', 'eomg']:
                files += ['config.anal', 'config.eobs']
            elif config in ['eupd']:
                files += ['config.anal', 'config.eupd']
            elif config in ['efcs']:
                files += ['config.fcst', 'config.efcs']
            elif config in ['atmanlinit', 'atmanlvar', 'atmanlfv3inc']:
                files += ['config.atmanl', f'config.{config}']
            elif config in ['atmensanlinit', 'atmensanlrun']:
                files += ['config.atmensanl', f'config.{config}']
            elif 'wave' in config:
                files += ['config.wave', f'config.{config}']
            else:
                files += [f'config.{config}']

            print(f'sourcing config.{config}') if verbose
            configs[config] = conf.parse_config(files)

        return configs

    @abstractmethod
    def get_task_names(self) -> Dict[str, List[str]]:
        '''
        Create a list of task names for each CDUMP valid for the configuation.

        Parameters
        ----------
        None

        Returns
        -------
        Dict[str, List[str]]: Lists of tasks for each CDUMP.

        '''
        pass

    @staticmethod
    def get_gfs_interval(gfs_cyc: int) -> timedelta:
        """
        return interval in hours based on gfs_cyc
        """

        gfs_internal_map = {'1': '24H', '2': '12H', '4': '6H'}

        try:
            return to_timedelta(gfs_internal_map[str(gfs_cyc)])
        except KeyError:
            raise KeyError(f'Invalid gfs_cyc = {gfs_cyc}')
