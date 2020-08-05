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
from nltk.corpus import wordnet as wd
from nltk import pos_tag
from nltk.corpus.reader.wordnet import Synset


class Frame:
    """
    A representation of a script frame.
    Each frame is a collection of fields and required lexical categories and senses for those fields.
    """

    _FRAMES = {}  # type: Dict[str, Frame]

    class FrameParseException(Exception):
        """
        Am Exception indicating an error with the frame's syntax.
        """
        pass

    class FieldFilter:
        """
        An representation for lexical and semantic restrictions on frame fields.
        """
        def __init__(self, filter_tag: Tag):
            """
            :param filter_tag: A bs4 tag with the Field element.
            """
            self.lexical = Frame.FieldFilter._parse_single_val_attr('lexical', filter_tag)  # type: str
            self.semantic = Frame.FieldFilter._parse_multival_attr('semantic', filter_tag)  # type: List[str]
            self.pos = Frame.FieldFilter._parse_multival_attr('pos', filter_tag)            # type: List[str]
            self.pattern = Frame.FieldFilter._parse_single_val_attr('pattern', filter_tag)  # type: str

        @staticmethod
        def _parse_multival_attr(attr, tag):
            if attr not in tag.attrs or tag.attrs[attr] == '*':
                return None

            data = tag.attrs[attr]
            return [s.strip(' ') for s in data.split(',')]

        @staticmethod
        def _parse_single_val_attr(attr, tag):
            if attr not in tag.attrs or tag.attrs[attr] == '*':
                return None

            data = tag.attrs[attr]
            return data.strip(' ')

        def __repr__(self):
            return f'Lexical: {self.lexical}, Semantic: {self.semantic}, PoS: {self.pos}, Pattern: {self.pattern}'

        def __str__(self):
            return self.__repr__()

        def word_match(self, word: str) -> bool:
            """
            Test whether a given word satisfies the restrictions of this field filter.
            :param word: The word to test.
            :return:
            """
            if self.pattern:
                match = re.match(self.pattern, word)
                if not match:
                    return False

            if self.pos:
                match = pos_tag([word])[0][1] in self.pos
                if not match:
                    return False

            return True

        def sense_match(self, sense: Synset) -> bool:
            """
            Test whether a given sense satisfies the restrictions of this field filter.
            :param sense: The sense to test.
            :return:
            """
            if self.lexical:
                match = sense.lexname() == self.lexical
                if not match:
                    return False

            if self.semantic:
                match = any([sense.name()[:sense.name().rfind('.')] == s for s in self.semantic])
                if not match:
                    return match

            return True


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

        for field in selective_iterator(elem, 'field'):
            # Each frame field is an XML attribute of the following form:
            # <field name="..." [lexical="..."] [semantic="..."] [pos="..."] [pattern="..."]/>
            # Where name is the name of the frame, and the rest are optional filters.
            # An absence of a tag indicates a wildcard that matches anything.
            f_name = field.attrs['name']
            f_filter = Frame.FieldFilter(field)
            f.fields[f_name] = f_filter

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
                    Frame.store(frame)
            except Frame.FrameParseException as fe:
                print(f'Error in frame set {item}: {fe}')

    @staticmethod
    def get(item: str):
        """
        Fetch a frame by name.
        :param item: The name of the frame to fetch.
        :return:
        """
        if item not in Frame._FRAMES:
            raise KeyError(f'Frame {item} not found.')

        return Frame._FRAMES[item].__copy__()

    @staticmethod
    def has(item: str):
        """
        Check if a global frame with a given name exists.
        :param item:
        :return:
        """
        return item in Frame._FRAMES

    @staticmethod
    def store(item: Frame):
        """
        Store a frame as global knowledge.
        :param item: The frame to store.
        :return:
        """
        if item.name in Frame._FRAMES:
            raise KeyError(f'Duplicate frame {item.name}')
        Frame._FRAMES[item.name] = item

    """
    INSTANCE METHODS
    """

    def __init__(self, name: str):
        self.name = name
        self.fields = {}  # type: Dict[str, Frame.FieldFilter]
        self.bindings = {}  # type: Dict[str, str]

    def frame_iterator(self) -> Tuple[str, FieldFilter]:
        """
        Iterate over all the non-name fields of the frame.
        :return:
        """
        for key, value in self.fields.items():
            yield key, value

    def __copy__(self):
        """
        Create a deep copy of a frame.
        :return:
        """
        other = Frame(self.name)
        other.fields = {k: v for k, v in self.fields}
        other.bindings = {k: v for k, v in self.bindings}

        return other

    def __repr__(self):
        return f'Frame({self.name})'

    def __str__(self):
        return self.__repr__()

    def __hash__(self):
        return hash(self.name)


# Type Alias for the frame dictionary
FrameStorage = Dict[str, Frame]
