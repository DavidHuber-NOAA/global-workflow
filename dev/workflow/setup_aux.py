#!/usr/bin/env python3

"""
Entry point for rendering the Jinja2-templated auxiliary workflow (aux.xml.j2)
into a Rocoto XML workflow file.

NOTES:
    The dev/ush/gw_setup.sh script must be sourced before running this script
    to set up the Python environment with the wxflow library.
"""

import os
from logging import getLogger
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from wxflow import Jinja, Logger, logit

_here = os.path.dirname(os.path.abspath(__file__))
_top = os.path.abspath(os.path.join(_here, '../..'))

# Setup the logger
logger = getLogger(__name__)


def input_args():
    """
    Method to collect user arguments for ``setup_aux.py``

    Parameters
    ----------
    None

    Returns
    -------
    argparse.Namespace
        Parsed command-line arguments
    """

    description = """
        Renders the Jinja2-templated auxiliary workflow XML (aux.xml.j2)
        into a Rocoto XML workflow file for use with the Rocoto workflow manager.

        The dev/ush/gw_setup.sh script must be sourced before running this script
        to ensure the Python environment with wxflow is properly configured.
        """

    parser = ArgumentParser(description=description,
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('--start-date',
                        help='Start date for the workflow cycles in YYYYMMDDHH format',
                        type=str, required=True, dest='start_date')
    parser.add_argument('--end-date',
                        help='End date for the workflow cycles in YYYYMMDDHH format',
                        type=str, required=True, dest='end_date')
    parser.add_argument('--HOMEglobal',
                        help='Full path to the global workflow home directory',
                        type=str, default=_top)
    parser.add_argument('--EXP-aux',
                        help='Full path to the auxiliary experiment directory',
                        type=str, required=True, dest='EXP_aux')
    parser.add_argument('--ECF-OUT-gfs',
                        help='Full path to the GFS ecFlow output directory; used as triggers',
                        type=str, required=True, dest='ECF_OUT_gfs')
    parser.add_argument('--COM-aux',
                        help='Full path to the auxiliary COM directory',
                        type=str, required=True, dest='COM_aux')
    parser.add_argument('--DATAROOT-aux',
                        help='Full path to the auxiliary DATAROOT directory',
                        type=str, required=True, dest='DATAROOT_aux')
    parser.add_argument('--output',
                        help='Full path for the rendered aux.xml output file. '
                             'Defaults to <EXP_aux>/aux.xml',
                        type=str, default=None)

    return parser.parse_args()


@logit(logger)
def main():

    user_inputs = input_args()

    template_path = os.path.join(_top, 'dev', 'parm', 'aux', 'aux.xml.j2')

    if user_inputs.output is None:
        output_path = os.path.join(user_inputs.EXP_aux, 'aux.xml')
    else:
        output_path = user_inputs.output

    context = {
        'start_date': user_inputs.start_date,
        'end_date': user_inputs.end_date,
        'HOMEglobal': user_inputs.HOMEglobal,
        'EXP_aux': user_inputs.EXP_aux,
        'ECF_OUT_gfs': user_inputs.ECF_OUT_gfs,
        'COM_aux': user_inputs.COM_aux,
        'DATAROOT_aux': user_inputs.DATAROOT_aux,
    }

    logger.info(f'Rendering aux.xml template: {template_path}')
    Jinja(template_path, context).save(output_path)
    logger.info(f'Rendered aux.xml written to: {output_path}')


if __name__ == '__main__':

    # Setup the logger
    logger = Logger(logfile_path=os.environ.get("LOGFILE_PATH"),
                    level=os.environ.get("LOGGING_LEVEL", "INFO"),
                    colored_log=os.environ.get("COLORED_LOG", True))

    main()
