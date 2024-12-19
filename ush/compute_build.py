#!/usr/bin/env python3

"""
Entry point for setting up a compute-node build
"""

import os
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from hosts import Host

from wxflow import parse_yaml


_here = os.path.dirname(__file__)
_top = os.path.abspath(os.path.join(os.path.abspath(_here), '..'))
expdir = os.path.join(_top, "sorc", "build")


def combine_dicts(host, inputs):

    # Read in the YAML file to fill out templates
    yaml_path = inputs.yaml
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f'YAML file does not exist, check path: {yaml_path}')
    yaml_dict = parse_yaml(path=yaml_path)

    # Update config.base
    base_dict = {
        "HOMEgfs": _top,
        "EXPDIR": expdir,
        "MACHINE": host.machine.upper()}

    # Add/override 'base'-specific declarations in base_dict
    return dict(base_dict, **get_template_dict(yaml_dict))


def get_template_dict(input_dict):
    # Reads a templated input dictionary and updates the output

    output_dict = dict()

    for key, value in input_dict.items():
        output_dict[f'{key}'] = value

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

    yaml_dict = combine_dicts(host, user_inputs)


if __name__ == '__main__':

    main()
