from applications.applications import AppConfig
from wxflow import Configuration
from typing import Dict, Any


class BuildAppConfig(AppConfig):
    '''
    Class to define compute build configurations
    '''
    _valid_builds = ["gfs", "gefs", "sfs", "upp", "ufs_utils", "gfs_utils", "gdas", "gsi", "gsi_monitor", "gsi_utils"]

    def __init__(self, conf: Configuration):
        super().__init__(conf)

        self.runs = ["build"]

    def _get_run_options(self, conf: Configuration) -> Dict[str, Any]:

        # The only build options are the systems to build
        base = conf.parse_config('config.base')
        build_options = {}
        for build in self._valid_builds:
            build_options[f"build_{build}"] = base.get(f"BUILD_{build}", False)

        run_options = {"build": build_options}

        return run_options

    @staticmethod
    def _update_base(base_in):

        base_out = base_in.copy()
        base_out['RUN'] = 'gfs'

        return base_out

    def _get_app_configs(self, run):
        """
        Returns the config file required for the build app
        """

        configs = ['compile']

        return configs

    def get_task_names(self):
        """
        Get the task names for all the tasks in the forecast-only application.
        Note that the order of the task names matters in the XML.
        This is the place where that order is set.
        """

        tasks = []

        options = self.run_options["build"]

        for build in self._valid_builds:
            if options[f'build_{build}']:
                tasks += [f'compile_{build}']

        return {f"build": tasks}
