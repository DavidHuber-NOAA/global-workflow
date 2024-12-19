#!/usr/bin/env python3

"""
Entry point for setting up a compute-node build
"""

import glob
import os
import shutil
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from hosts import Host

import setup_xml

from wxflow import parse_yaml


_here = os.path.dirname(__file__)
_top = os.path.abspath(os.path.join(os.path.abspath(_here), '..'))
expdir = os.path.join(_top, "sorc", "build")


def fill_expdir():
    """
    Method to copy config files from workflow to experiment directory
    """
    configdir = os.path.join(_top, "parm", "config", "build")
    configs = glob.glob(f'{configdir}/config.*')
    if len(configs) == 0:
        raise IOError(f'no config files found in {configdir}')
    for config in configs:
        shutil.copy(config, expdir)

    return


def update_configs(host, inputs):

    # Read in the YAML file to fill out templates
    yaml_path = inputs.yaml
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f'YAML file does not exist, check path: {yaml_path}')
    yaml_dict = parse_yaml(path=yaml_path)

    # Update config.base
    base_dict = {
        "@HOMEgfs@": _top,
        "@EXPDIR@": expdir,
        "@MACHINE@": host.machine.upper()}

    # Add/override 'base'-specific declarations in base_dict
    base_dict = dict(base_dict, **get_template_dict(yaml_dict))

    base_input = os.path.join(_top, "parm", "config", "build", "config.base")
    base_output = os.path.join(expdir, 'config.base')
    edit_config(base_input, base_output, host.info, base_dict)

    return


def edit_config(input_config, output_config, host_info, config_dict):
    """
    Given a templated input_config filename, parse it based on config_dict and
    host_info and write it out to the output_config filename.
    """

    # Override defaults with machine-specific defaults
    host_dict = get_template_dict(host_info)
    config_dict = dict(config_dict, **host_dict)

    # Read input config
    with open(input_config, 'rt') as fi:
        config_str = fi.read()

    # Substitute from config_dict
    for key, val in config_dict.items():
        config_str = config_str.replace(key, str(val))

    # Write output config
    with open(output_config, 'wt') as fo:
        fo.write(config_str)

    print(f'EDITED:  {output_config} as per user input.')

    return


def get_template_dict(input_dict):
    # Reads a templated input dictionary and updates the output

    output_dict = dict()

    for key, value in input_dict.items():
        # In some cases, the same config may be templated twice
        # Prevent adding additional "@"s
        if "@" in key:
            output_dict[f'{key}'] = value
        else:
            output_dict[f'@{key}@'] = value

    return output_dict


def input_args(*argv):
    """
    Method to collect user arguments for `setup_build.py`
    """

    description = """
        Setup files and directories to start a compute build.
    """

    parser = ArgumentParser(description=description,
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('--yaml', help='Input YAML file',
                        type=str, required=False, default='build_opts.yaml')
    parser.add_argument('--account', help='HPC account to use; default is host-dependent', required=False, default=os.getenv('HPC_ACCOUNT'))

    inputs = parser.parse_args(list(*argv) if len(argv) else None)

    return inputs


def main(*argv):

    user_inputs = input_args(*argv)
    host = Host()

    # Update the default host account if the user supplied one
    if user_inputs.account is not None:
        host.info.ACCOUNT = user_inputs.account

    fill_expdir()
    update_configs(host, user_inputs)

    setup_xml.main([expdir])


if __name__ == '__main__':

    main()
