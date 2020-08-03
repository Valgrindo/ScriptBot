from __future__ import annotations
"""
An implementation of the Frame abstraction, consisting of field and qualifiers for them.

CS 799.06 Independent Study in NLP
Rochester Institute of Technology
:author: Sergey Goldobin
:date: 08/03/2020 13:14
"""

from typing import *
from os.path import isdir, isfile, join
from os import listdir
import re

from bs4 import Tag, BeautifulSoup
from utils import selective_iterator


class Frame:
    """
    A representation of a script frame.
    Each frame is a collection of fields and required lexical categories and senses for those fields.
    """

    _FRAMES = set()  # type: Set[Frame]

    class FrameParseException(Exception):
        """
        Am Exception indicating an error with the frame's syntax.
        """
        pass

    class FieldFilter:
        """
        An representation for lexical and semantic restrictions on frame fields.
        """
        def __init__(self, filter_str: str):
            """
            :param filter_str: A string of the form "lexical_r | semantic_r_1, semantic_r_2, ..."
            """
            match = re.findall(r"(\S+\s?)\|\s?(\S+\s?)(,\S+\s?)*", filter_str.strip('\n\r '))[0]
            match = list(filter(lambda x: bool(x), map(lambda s: s.strip(', '), match)))
            self.lexical = match[0]
            self.semantic = match[1:]

        def __repr__(self):
            return f'{self.lexical} | {self.semantic}'

        def __str__(self):
            return self.__repr__()

    @staticmethod
    def parse_set(fname: str) -> Set[Frame]:
        """
        Parse a set of sequential frames from a file.
        :param fname: Source file name.
        :return:
        """
        result = set()  # type: Set[Frame]
        if not isfile(fname):
            raise ValueError(f'Invalid frame source file: {fname}')

        with open(fname, 'r') as fp:
            bs = BeautifulSoup(fp, 'xml')

        frame_root = bs.find('frames')
        if not frame_root:
            raise Frame.FrameParseException("Required <frames> tag not found.")

        for elem in selective_iterator(frame_root, 'frame', Frame.FrameParseException):
            f = Frame.parse_frame(elem)
            result.add(f)  # Add the frame to the set of local frames.

        return result

    @staticmethod
    def parse_frame(elem: Tag) -> Frame:
        f = Frame(elem.attrs['name'].lower())  # Create a frame with the name specified in the tag.
        for line in elem.text.split('\n'):
            line = line.strip('\n\r ')
            if not line:
                continue
            # Each line in side the <frame> tag is of the following form:
            # field_name: lexical_filter | semantic_filter_1, [semantic_filter_2, ...]
            # Parse the pattern into a dynamic set of fields.
            split_data = line.split(':')
            f_name = split_data[0].strip()
            f_filter = Frame.FieldFilter(split_data[1])
            setattr(f, f_name, f_filter)
        return f

    @staticmethod
    def initialize(directory: str) -> NoReturn:
        """
        Initialize a global frame collection.
        :param directory: global frames directory.
        :return: None
        """
        if not isdir(directory):
            raise ValueError(f'Invalid frame source directory: {directory}')

        for item in listdir(directory):
            try:
                full_path = join(directory, item)
                for frame in Frame.parse_set(full_path):
                    Frame._FRAMES.add(frame)
            except Frame.FrameParseException as fe:
                print(f'Error in frame set {item}: {fe}')

    """
    INSTANCE METHODS
    """

    def __init__(self, name: str):
        self.name = name

        # Fields are added dynamically by the parser.

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__()

