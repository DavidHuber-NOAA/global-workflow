#!/usr/bin/env python3

"""
Entry point for rendering the Jinja2-templated auxiliary workflow (aux.xml.j2)
into a Rocoto XML workflow file.

Workflow configuration is read from a Jinja2-templated YAML file
(see dev/parm/aux/aux.yaml.j2 for the default template). When --config-base is
provided, variables from the target config.base are used to render the YAML
template before generating the XML. If no --config path is provided, the script
locates the repository root via ``git rev-parse`` and uses
``<HOMEglobal>/dev/parm/aux/aux.yaml.j2``.

NOTES:
    The dev/ush/gw_setup.sh script must be sourced before running this script
    to set up the Python environment with the wxflow library.
"""

import os
from datetime import datetime, timedelta
from logging import getLogger
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from wxflow import Configuration, Executable, Jinja, Logger, logit, parse_j2yaml, to_YMDH
from wxflow.executable import ProcessError

_here = os.path.dirname(os.path.abspath(__file__))

# Setup the logger
logger = getLogger(__name__)

# Required keys in the rendered configuration context
_REQUIRED_CONFIG_KEYS = ['start_date', 'end_date', 'EXP_aux',
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
        git = Executable('git')
        result = git('-C', _here, 'rev-parse', '--show-toplevel', output=str)
        return result.strip()
    except ProcessError as e:
        raise RuntimeError(f"Failed to determine HOMEglobal via git: {e}") from e


def calc_start_end_metp_dates(start_date, end_date):
    """
    Calculate the start and end dates for the METplus METP tool based on the
    provided workflow start and end dates. METplus runs on the 18z cycle only.

    Parameters
    ----------
    start_date : str
        Workflow start date in YYYYMMDDHHMM format
    end_date : str
        Workflow end date in YYYYMMDDHHMM format

    Returns
    -------
    tuple of str
        Tuple containing the calculated start and end dates for METP in YYYYMMDDHHMM format
    """

    start_dt = datetime.strptime(start_date, '%Y%m%d%H%M')
    end_dt = datetime.strptime(end_date, '%Y%m%d%H%M')

    # METP start: 18z cycle on the day before the workflow start date
    metp_start_dt = (start_dt - timedelta(days=1)).replace(hour=18, minute=0, second=0)

    # METP end: 18z cycle on the workflow end date
    metp_end_dt = end_dt.replace(hour=18, minute=0, second=0)

    metp_start_str = metp_start_dt.strftime('%Y%m%d%H%M')
    metp_end_str = metp_end_dt.strftime('%Y%m%d%H%M')

    return metp_start_str, metp_end_str


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

        Workflow configuration is read from a Jinja2-templated YAML file. When
        --config-base is provided, variables from the target config.base are used
        to substitute defaults in the YAML template automatically.

        The dev/ush/gw_setup.sh script must be sourced before running this script
        to ensure the Python environment with wxflow is properly configured.
        """

    parser = ArgumentParser(description=description,
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('--config',
                        help='Full path to the aux configuration YAML (or YAML.j2) file. '
                             'Defaults to <HOMEglobal>/dev/parm/aux/aux.yaml.j2',
                        type=str, default=None)

    parser.add_argument('--config-base',
                        help='Full path to the experiment config.base file. '
                             'When provided, variables from config.base are used to '
                             'render the YAML template before generating the XML.',
                        type=str, default=None)

    parser.add_argument('--crontab',
                        help='Write a crontab entry for running rocotorun against '
                             'the generated aux.xml. Written to <EXP_aux>/aux.crontab '
                             'by default.',
                        action='store_true', default=False)

    parser.add_argument('--crontab-file',
                        help='Full path for the output crontab file. '
                             'Defaults to <EXP_aux>/aux.crontab.',
                        type=str, default=None)

    return parser.parse_args()


def _parse_config_base(config_base_path):
    """
    Parse a config.base file using wxflow Configuration and return a dict
    of all exported variables. Datetime objects are converted to YYYYMMDDHH
    strings for use in Jinja2 templates.

    Parameters
    ----------
    config_base_path : str
        Full path to the config.base file

    Returns
    -------
    dict
        Dictionary of variables exported by config.base, with datetime objects
        converted to YYYYMMDDHH strings
    """
    config_base_path = os.path.abspath(config_base_path)
    config_dir = os.path.dirname(config_base_path)
    config_name = os.path.basename(config_base_path)
    cfg = Configuration(config_dir)
    raw = cfg.parse_config(config_name)
    # Convert datetime objects to YYYYMMDDHH strings so Jinja2 templates can
    # use them with simple string concatenation (e.g. "{{ SDATE }}00")
    return {k: to_YMDH(v) if isinstance(v, datetime) else v
            for k, v in raw.items()}


def _write_crontab(exp_aux, xml_path, db_path,
                   crontab_file=None, cronint=5):
    """
    Write a crontab entry to execute rocotorun every ``cronint`` minutes.

    Parameters
    ----------
    exp_aux : str
        Path to the auxiliary experiment directory
    xml_path : str
        Full path to the generated aux.xml file
    db_path : str
        Full path to the rocoto database file (aux.db)
    crontab_file : str, optional
        Output path for the crontab file. Defaults to ``<exp_aux>/aux.crontab``.
    cronint : int, optional
        Crontab interval in minutes. Defaults to 5.
    """

    rocotorun = None
    try:
        rocotorun = Executable('rocotorun')
    except Exception:
        pass

    if rocotorun is None:
        logger.warning('rocotorun not found; crontab will not be created')
        return

    rocotoruncmd = rocotorun.command
    rocotorunstr = f'{rocotoruncmd} -d {db_path} -w {xml_path}'
    cronintstr = f'*/{cronint} * * * *'

    crontab_strings = [
        '',
        '#################### aux_gfs ####################',
        f'SHELL="/bin/bash"',
        f'{cronintstr} {rocotorunstr}',
        '#################################################################',
        ''
    ]

    if crontab_file is None:
        crontab_file = os.path.join(exp_aux, 'aux.crontab')

    with open(crontab_file, 'w') as fh:
        fh.write('\n'.join(crontab_strings))

    logger.info(f'Crontab written to: {crontab_file}')
    print('*' * 55)
    print(f'Please add the contents of\n  {crontab_file}\n'
          f'to your crontab with: crontab -l >> {crontab_file} && crontab {crontab_file}')
    print('*' * 55)


@logit(logger)
def main():

    user_inputs = input_args()

    # Determine HOMEglobal early so it can be used as a default config path
    HOMEglobal = _get_HOMEglobal()

    # Resolve the YAML config path (may be a .j2 template)
    if user_inputs.config is None:
        config_path = os.path.join(HOMEglobal, 'dev', 'parm', 'aux', 'aux.yaml.j2')
    else:
        config_path = user_inputs.config

    logger.info(f'Reading aux configuration: {config_path}')

    # Build the Jinja2 rendering context.
    # If --config-base is given, seed the context with variables from config.base.
    j2_context = {'HOMEglobal': HOMEglobal}
    if user_inputs.config_base is not None:
        logger.info(f'Parsing config.base: {user_inputs.config_base}')
        base_vars = _parse_config_base(user_inputs.config_base)
        j2_context.update(base_vars)
        logger.info(f'Loaded {len(base_vars)} variables from config.base')

    # Render the YAML template (or load plain YAML) to produce the final context
    if config_path.endswith('.j2'):
        context = parse_j2yaml(config_path, j2_context)
    else:
        import yaml
        with open(config_path, 'r') as f:
            context = yaml.safe_load(f)

    # Validate required keys
    missing_keys = [key for key in _REQUIRED_CONFIG_KEYS if not context.get(key)]
    if missing_keys:
        raise KeyError(f"Required key(s) missing or empty in config {config_path}: "
                       f"{', '.join(missing_keys)}")

    # Calculate METP cycle dates (18z offset cycles for METplus verification)
    metp_start_date, metp_end_date = calc_start_end_metp_dates(
        context['start_date'], context['end_date'])
    context['start_date_metp'] = metp_start_date
    context['end_date_metp'] = metp_end_date
    logger.info(f"Calculated METP start: {metp_start_date}, end: {metp_end_date}")

    # Ensure HOMEglobal is in context (may have been set by config.base)
    if 'HOMEglobal' not in context:
        context['HOMEglobal'] = HOMEglobal
        logger.info(f"HOMEglobal not in rendered config; set to: {HOMEglobal}")

    template_path = os.path.join(context['HOMEglobal'], 'dev', 'workflow', 'aux', 'aux.xml.j2')
    output_path = context.get('output') or os.path.join(context['EXP_aux'], 'aux.xml')

    # Create the output directory if it does not already exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    logger.info(f'Rendering aux.xml template: {template_path}')
    Jinja(template_path, context).save(output_path)
    logger.info(f'Rendered aux.xml written to: {output_path}')

    # Optionally write a crontab entry for running rocotorun
    if user_inputs.crontab:
        db_path = os.path.splitext(output_path)[0] + '.db'
        _write_crontab(
            exp_aux=context['EXP_aux'],
            xml_path=output_path,
            db_path=db_path,
            crontab_file=user_inputs.crontab_file
        )


if __name__ == '__main__':

    # Setup the logger
    logger = Logger(logfile_path=os.environ.get("LOGFILE_PATH"),
                    level=os.environ.get("LOGGING_LEVEL", "INFO"),
                    colored_log=os.environ.get("COLORED_LOG", True))

    main()
