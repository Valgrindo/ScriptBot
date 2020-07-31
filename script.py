from __future__ import annotations
"""
An implementation of the Script abstraction, consisting of Lines and Frames.

CS 799.06 Independent Study in NLP
Rochester Institute of Technology
:author: Sergey Goldobin
:date: 07/31/2020 15:34
"""

from bs4 import BeautifulSoup, Tag
from typing import *

from os.path import isdir, isfile
from os import listdir


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

    @staticmethod
    def parse_set(fname: str) -> Set[Frame]:
        """
        Parse a set of sequential frames from a file.
        :param fname: Source file name.
        :return:
        """
        pass

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
                for frame in Frame.parse_set(item):
                    Frame._FRAMES.add(frame)
            except Frame.FrameParseException as fe:
                print(f'Error in frame set {item}: {fe}')


class Script:
    """
    A representation of a script.
    A script is a collection of lines uttered by the bot with possible references to local and global knowledge, and
    a set of possible responses. A response is a set of expected frames and an action of either deferring to another
    script or continuing with the current one. Realized frames are added to local knowledge.
    """

    _SCRIPTS = set()  # type: Set[Script]

    """
    STATIC METHODS
    """

    @staticmethod
    def get(item):
        """
        Fetch a script by name.
        :param item: The name of the script to fetch.
        :return:
        """
        filtered_set = list(filter(lambda s: s.name == item, Script._SCRIPTS))
        if not filtered_set:
            raise KeyError(f'Script {item} not found.')

        return filtered_set[0]

    @staticmethod
    def initialize(directory: str) -> NoReturn:
        """
        Initialize a global script collection.
        :param directory: Scripts directory.
        :return: None
        """
        if not isdir(directory):
            raise ValueError(f'Invalid script source directory: {directory}')

        for item in listdir(directory):
            try:
                entity = Script(item)
                Script._SCRIPTS.add(entity)
            except Script.ScriptParseException as se:
                print(f'Error in script {item}: {se}')

    class ScriptParseException(Exception):
        """
        Am Exception indicating an error with the script's syntax.
        """
        pass

    """
    INSTANCE METHODS
    """

    def __init__(self, fname: str):
        """
        Intialize a script using an XMl file
        :param fname:
        """
        self._lines = []
        self.ref_frames = set()  # type: Set[Frame]

        with open(fname, 'r') as fp:
            bs = BeautifulSoup(fp, 'xml')
        root = bs.find('scenario')

        if not root:
            raise Script.ScriptParseException("Root <scenario> tag not found.")

        # root is expected to have two top-level tags: <dialogue> and <frames>
        dialogue_root = root.find('dialogue')
        if not dialogue_root:
            raise Script.ScriptParseException("Required <dialogue> tag not found.")

        # Dialogue consists of <lines>
        for elem in dialogue_root:
            if not isinstance(elem, Tag):
                # Skip comments, whitespace, etc.
                continue

            if elem.name != 'line':
                raise Script.ScriptParseException(f"Unexpected tag {elem.name}")
            # TODO: Process the individual line

        # All lines processed, now the local frames.
        frame_root = root.find('frames')
        if not frame_root:
            raise Script.ScriptParseException("Required <frames> tag not found.")

        # Frame collection consists of individual <frames>
        for elem in frame_root:
            if not isinstance(elem, Tag):
                # Skip comments, whitespace, etc.
                continue

            if elem.name != 'frame':
                raise Script.ScriptParseException(f"Unexpected tag {elem.name}")
            # TODO: Process the individual frame

        # All lines and frames processed,
        # TODO: Any post-processing necessary?

    def execute(self):
        """
        Begin line-by-line execution of the script.
        :return:
        """
        # frame matching algorithm idea:
        # For each word in a sentence:
        #   Check if the lexical category of the word matches any of the fields in the frame.
        #   For each matching field:
        #       Recurse on the set of hypernyms of the word until a matching sense is found or the search fails.
        pass

