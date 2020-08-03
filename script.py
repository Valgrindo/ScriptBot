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
from frame import Frame

from os.path import isdir, isfile, join
from os import listdir
from dataclasses import dataclass
from utils import selective_iterator, compose
from collections import namedtuple


class Response:
    """
    An expectation for a user's response. Contains a set of frames to be realized and an action to take.
    """
    def __init__(self):
        self.to_realize = []  # type: List[str]  # List of frame names
        self.action = ''  # type: Union[str, Tuple[str, str]]  # Either continue or defer to some other script
        self.transfer = False  # If the response defers, should local KD be transferred to the script?

    def satisfy(self, answer: str) -> Tuple[float, Set[Frame]]:
        """
        Check whether a given answer satisfies the requirements of this responce
        :param answer: A string answer provided by a user.
        :return: (satisfaction %, set of potentially incomplete frames)
        """
        raise NotImplementedError()


class Line:
    """
    A representation of a dialogue line in a script.
    """

    def __init__(self):
        self.text = ''
        self.responses = []  # type: List[Response]

    def display(self, frame_db: Set[Frame]):
        """
        Display the text of this line. Refer to the frame DB to fill in any references.
        :param frame_db:
        :return:
        """
        raise NotImplementedError()


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
                full_path = join(directory, item)
                entity = Script(full_path)
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
        self.name = ''

        with open(fname, 'r') as fp:
            bs = BeautifulSoup(fp, 'xml')
        root = bs.find('scenario')
        if not root:
            raise Script.ScriptParseException("Root <scenario> tag not found.")

        self.name = root.attrs['name'].lower()

        # root is expected to have two top-level tags: <dialogue> and <frames>
        dialogue_root = root.find('dialogue')
        if not dialogue_root:
            raise Script.ScriptParseException("Required <dialogue> tag not found.")

        # Dialogue consists of <lines>
        for elem in selective_iterator(dialogue_root, 'line', Script.ScriptParseException):
            line = Line()
            line.text = elem.text.strip('\n\r\t ')  # Copy over the provided string and all internal <f> references.

            # Now, process each response line:
            for rsp in selective_iterator(elem, 'response'):
                r = Response()
                expected_frame_names = list(map(compose(str.strip, str.lower), rsp.attrs['f'].split(',')))
                r.to_realize = expected_frame_names
                r.action = rsp.attrs['action']

                if 'transfer' in rsp.attrs:
                    r.transfer = True
                line.responses.append(r)
            self._lines.append(line)

        # All lines processed, now the local frames.
        frame_root = root.find('frames')
        if not frame_root:
            raise Script.ScriptParseException("Required <frames> tag not found.")

        # Frame collection consists of individual <frames>
        for elem in selective_iterator(frame_root, 'frame', Frame.FrameParseException):
            f = Frame.parse_frame(elem)
            self.ref_frames.add(f)  # Add the frame to the set of local frames.

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

