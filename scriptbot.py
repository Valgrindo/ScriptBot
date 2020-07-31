"""
A simple frame-based conversation agent capable of fulfilling script and engaging in a back-and-forth with the user
to elicit additional information if inputs are malformed or incomplete.

CS 799.06 Independent Study in NLP
Rochester Institute of Technology
:author: Sergey Goldobin
:date: 07/31/2020 13:27
"""

import argparse
from os.path import isfile, isdir
from os import listdir
from typing import *

from script import Script, Frame

DEFAULT_SCRIPT_DIR = '~\\scripts'
DEFAULT_FRAME_DIR = '~\\frames'


def main():
    """
    Entry point for the program. Scan for available scripts and ask for one to execute.
    :return:
    """
    argp = argparse.ArgumentParser()
    argp.add_argument('-s', '--script', help='Path to a script file to execute.', required=True)
    args = argp.parse_args()

    if not isfile(args.script):
        raise ValueError(f'Script file {args.script} not found!')

    Frame.initialize(DEFAULT_FRAME_DIR)
    Script.initialize(DEFAULT_SCRIPT_DIR)

    script = Script.get(args.script)
    script.execute()


if __name__ == '__main__':
    main()
