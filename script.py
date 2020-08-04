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
import re

from os.path import isdir, isfile, join
from os import listdir
from utils import selective_iterator, compose
from nltk.corpus import wordnet as wd
from nltk.tokenize import word_tokenize


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
        Check whether a given answer satisfies the requirements of this response
        :param answer: A string answer provided by a user.
        :return: (satisfaction %, set of potentially incomplete frames)
        """
        frames = [Frame.get(fn).__copy__() for fn in self.to_realize]

        # Each frame is a set of fields with lexical and semantic restrictions.
        # For each word in the answer:
        #   If any of its senses match the lexical name of one of the fields:
        #       For each matching sense, check if it is expected semantically.
        #           If not, perform a hypernym search for a match.
        #   If not:
        #       Continue to next word.
        tokens = word_tokenize(answer)
        for word in tokens:
            senses = wd.synsets(word)  # Get a list of all the senses of the word.
            for sense in senses:
                # Check is the lexical name of this sense matches any frame fields:
                for f in frames:
                    for field, fltr in f.frame_iterator():
                        if sense.lexname() != fltr.lexical:
                            # This sense cannot be a match since the lexical name is wrong.
                            continue

                        search_res = None
                        if sense.name() != fltr.semantic:
                            # Lexical name is correct, but semantic is not. Search for a matching sense in hypernyms.
                            search_res = Response.hypernym_search(sense, fltr)  # TODO: Implement

                        if search_res or sense.name() == fltr.semantic \
                                or not isinstance(f.__getattribute__(field), Frame.FieldFilter):
                            setattr(f, field, word)

        # Examined all the words. Now, count up the number of unsatisfied fields.
        # TODO: Tally frameset completeness
        sat = 0.0

        return sat, set(frames)

    @staticmethod
    def hypernym_search(sense, fltr: Frame.FieldFilter) -> bool:
        """
        Search the hypernyms of this sense to determine if the required sense can be found somewhere in the tree above.
        :param sense:
        :param fltr:
        :return:
        """
        # TODO: Implement
        pass


class Line:
    """
    A representation of a dialogue line in a script.
    """

    def __init__(self):
        self.text = ''
        self.responses = []  # type: List[Response]

    def say(self):
        """
        Display the text of this line. Refer to the local knowledge base to fill any <f> fields.
        :return:
        """
        # Scan the string for occurrences of the <f>frame.field</f> pattern. Construct the sentence by looking up the
        # appropriate frames and plugging the value into the sentence.
        pattern = r'\s?\$[a-zA-Z\.\_]+'
        slots = [(m.start(), m.end()) for m in re.finditer(pattern, self.text)]

        if not slots:
            # If there were no patterns within the line, say it as-is.
            print(self.text)
            return

        refs = [self.text[start:end].strip('$ ').split('.') for (start, end) in slots]
        plugs = [Frame.get(name).__getattribute__(field) for (name, field) in refs]

        to_say = ''
        for i in range(len(slots)):
            to_say += self.text[:slots[i][0]] + plugs[i]

        print(to_say)


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
        self.local_frames = set()  #type: Set[Frame] # Local knowledge storage.

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

    def execute(self, tn: Set[Frame] = None):
        """
        Begin line-by-line execution of the script.
        :param tn: The set of transferred knowledge.
        :return:
        """
        # frame matching algorithm idea:
        # For each word in a sentence:
        #   Check if the lexical category of the word matches any of the fields in the frame.
        #   For each matching field:
        #       Recurse on the set of hypernyms of the word until a matching sense is found or the search fails.

        # Apply any transferred knowledge
        if tn is not None:
            self.local_frames.update(tn)

        # For every line of the script, say the line and process the response.
        for line in self._lines:
            line.say()
            response = input('> ')

            # Find which response option is satisfied the most.
            best_sat, best_frames, best_r = 0, set(), None
            for r in line.responses:
                sat, frames = r.satisfy(response)
                if sat > best_sat:
                    best_sat, best_frames, best_r = sat, frames, r

            if best_sat != 1:
                # There were unfilled fields in the required frames.
                # Extract the needed information from the user.
                # TODO: Handle the case where the bot needs to ask questions.
                pass
            else:
                # The user's reply satisfied all the frames. Save them to local knowledge.
                self.local_frames.update(best_frames)

                # Execute the action associated with selected response.
                if best_r.action != 'continue':
                    # Expected form: defer:<script>
                    res = best_r.action.split(':')
                    if len(res) != 2 or res[0] != 'defer':
                        raise ValueError(f'Invalid action: {best_r.action}')

                    # Execute the script pointed to by the action.
                    Script.get(res[1]).execute(self.local_frames if best_r.transfer else None)
                    return  # Do not continue execution of this script.

                # Implicitly move on to next line on act == 'continue'


