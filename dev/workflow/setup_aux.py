#!/usr/bin/env python3

"""
Entry point for rendering the Jinja2-templated auxiliary workflow (aux.xml.j2)
into a Rocoto XML workflow file.

The configuration for the rendering is read from a YAML config file
(see dev/parm/aux/config.aux.j2 for a sample). Values in the config file
may use Jinja2 expressions that reference environment variables.

NOTES:
    The dev/ush/gw_setup.sh script must be sourced before running this script
    to set up the Python environment with the wxflow library.
"""

import os
import subprocess
from logging import getLogger
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from wxflow import Jinja, Logger, logit, parse_j2yaml

_here = os.path.dirname(os.path.abspath(__file__))

# Setup the logger
logger = getLogger(__name__)

# Required keys in the configuration file
_REQUIRED_CONFIG_KEYS = ['start_date', 'end_date', 'HOMEglobal', 'EXP_aux',
                         'ECF_OUT_gfs', 'COM_aux', 'DATAROOT_aux']


def _get_HOMEglobal():
    """
    Determine the repository root directory using ``git rev-parse``.

    Parameters
    ----------
    None

    Returns
    -------
    str
        Absolute path to the repository root directory

    Raises
    ------
    RuntimeError
        If the git command fails
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, check=True,
            cwd=_here
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to determine HOMEglobal via git: {e}") from e


def input_args(HOMEglobal):
    """
    Method to collect user arguments for ``setup_aux.py``

    Parameters
    ----------
    HOMEglobal : str
        Absolute path to the repository root directory

    Returns
    -------
    argparse.Namespace
        Parsed command-line arguments
    """

    _default_config = os.path.join(HOMEglobal, 'dev', 'parm', 'aux', 'config.aux')

    description = """
        Renders the Jinja2-templated auxiliary workflow XML (aux.xml.j2)
        into a Rocoto XML workflow file for use with the Rocoto workflow manager.

        Workflow configuration is read from a YAML config file. Copy
        dev/parm/aux/config.aux.j2 to config.aux (or another path), fill in the
        values for your environment, and pass the path via --config.

        The dev/ush/gw_setup.sh script must be sourced before running this script
        to ensure the Python environment with wxflow is properly configured.
        """

    parser = ArgumentParser(description=description,
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('--config',
                        help='Full path to the aux configuration YAML file. '
                             f'Defaults to {_default_config}',
                        type=str, default=_default_config)

    return parser.parse_args()


@logit(logger)
def main():

    HOMEglobal = _get_HOMEglobal()
    user_inputs = input_args(HOMEglobal)

    template_path = os.path.join(HOMEglobal, 'dev', 'parm', 'aux', 'aux.xml.j2')

    logger.info(f'Reading aux configuration: {user_inputs.config}')
    context = parse_j2yaml(path=user_inputs.config, data=os.environ)

    missing_keys = [key for key in _REQUIRED_CONFIG_KEYS if key not in context]
    if missing_keys:
        raise KeyError(f"Required key(s) missing from config file {user_inputs.config}: "
                       f"{', '.join(missing_keys)}")

    output_path = context.get('output') or os.path.join(context['EXP_aux'], 'aux.xml')

    logger.info(f'Rendering aux.xml template: {template_path}')
    Jinja(template_path, context).save(output_path)
    logger.info(f'Rendered aux.xml written to: {output_path}')


if __name__ == '__main__':

    # Setup the logger
    logger = Logger(logfile_path=os.environ.get("LOGFILE_PATH"),
                    level=os.environ.get("LOGGING_LEVEL", "INFO"),
                    colored_log=os.environ.get("COLORED_LOG", True))

    main()
