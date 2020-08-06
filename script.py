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
from frame import Frame, FrameStorage
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

    def satisfy(self, answer: str, local: FrameStorage) -> Tuple[float, FrameStorage]:
        """
        Check whether a given answer satisfies the requirements of this response
        :param answer: A string answer provided by a user.
        :param local: A set of frames representing local knowledge.
        :return: (satisfaction %, set of potentially incomplete frames)
        """
        # Bring in any
        frames = []
        for f in self.to_realize:
            if Frame.has(f):
                frames.append(Frame.get(f))
            if f in local:
                frames.append(local[f])

        # Each frame is a set of fields with lexical and semantic restrictions.
        # For each word in the answer:
        #   If any of its senses match the lexical name of one of the fields:
        #       For each matching sense, check if it is expected semantically.
        #           If not, perform a hypernym search for a match.
        #   If not:
        #       Continue to next word.
        # TODO: Rewrite the description
        tokens = word_tokenize(answer)
        for word in tokens:
            # For every frame, check if this word satisfies literal restrictions
            for f in frames:
                for field, fltr in f.frame_iterator():
                    if not fltr.word_match(word):
                        # The word is incompatible with this field of this frame.
                        continue

                    # The word is literally compatible. Now, check all of its senses.
                    senses = wd.synsets(word)
                    any_match = False

                    # If there are no sense restrictions, it's a match.
                    if not fltr.lexical and not fltr.semantic:
                        any_match = True
                    # If there are sense restrictions, but the word has no senses, no match.
                    elif not senses:
                        any_match = False
                    # Otherwise, check all senses for a potential match.
                    else:
                        for sense in senses:
                            if fltr.sense_match(sense):
                                any_match = True
                                break
                            else:
                                # If the sense did not match, conduct a recursive hypernym search
                                if self.hypernym_search(sense, fltr):
                                    any_match = True
                                    break

                    # All senses' ontologies explored. If there was a match, bind this words as the field value
                    if any_match:
                        f.bindings[field] = word

        # Examined all the words. Now, count up the number of unsatisfied fields.
        sat = 0.0
        total = sum([len(f.fields) for f in frames])
        for f in frames:
            sat += sum([1 for v in f.bindings.values() if v is not None])
        sat /= total

        return sat, {f.name: f for f in frames}

    @staticmethod
    def hypernym_search(sense, fltr: Frame.FieldFilter) -> bool:
        """
        Search the hypernyms of this sense to determine if the required sense can be found somewhere in the tree above.
        :param sense:
        :param fltr:
        :return:
        """
        if fltr.sense_match(sense):
            # Success: target sense present in the ontology.
            return True

        match = False
        for hp in sense.hypernyms():
            match = match or Response.hypernym_search(hp, fltr)

        return match

    def __repr__(self):
        return f'Realize {self.to_realize} -> {self.action}'

    def __str__(self):
        return self.__repr__()


class Line:
    """
    A representation of a dialogue line in a script.
    """

    def __init__(self):
        self.text = ''
        self.responses = []  # type: List[Response]

    def say(self, local: FrameStorage = None):
        """
        Display the text of this line. Refer to the local knowledge base to fill any <f> fields.
        :local: Optional local context frames.
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

        refs = [list(filter(lambda x: x != '', self.text[start:end].strip('$ ').split('.'))) for (start, end) in slots]
        plugs = []
        for name, field in refs:
            if local and name in local:
                plugs.append(local[name].bindings[field])
            elif Frame.has(name):
                plugs.append(Frame.get(name).bindings[field])
            else:
                raise ValueError(f'Required frame {name} has not been learned!')

        to_say = ''
        cursor = 0
        for i in range(len(slots)):
            before = self.text[cursor:slots[i][0]+1]
            to_say += before + plugs[i]
            cursor = slots[i][1]+1
        to_say += self.text[slots[-1][1]:]

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
            raise KeyError(f'Script "{item}" not found.')

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
        self.name = ''
        self.local_frames = {}  # type: FrameStorage # Local knowledge storage.

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
            self.local_frames[f.name] = f  # Add the frame to the set of local frames.

        # All lines and frames processed,
        # TODO: Any post-processing necessary?

    def execute(self, tn: FrameStorage = None):
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
            line.say(local=self.local_frames)

            if not line.responses:
                # Do not offer an input prompt if there are no response options.
                continue

            # Find which response option is satisfied the most.
            best_sat, best_frames, best_r = 0, {}, None
            while best_r is None:
                response = input('> ')
                for r in line.responses:
                    sat, frames = r.satisfy(response, self.local_frames)
                    if sat > best_sat:
                        best_sat, best_frames, best_r = sat, frames, r

                if best_r is None:
                    print('I did not understand what you were talking about.')
                else:
                    break

            if best_sat != 1:
                # There were unfilled fields in the required frames.
                # Extract the needed information from the user.
                for f in best_frames.values():
                    print(f'I believe you are talking about {f.desc}, but I need some more information.')
                    for field, val in f.fields.items():
                        # While any field remains unfilled, ask the user pointed questions to extract the information.
                        if field in f.bindings:
                            # If the field has been filled, do not ask about it.
                            continue
                        while True:
                            print(f'What {field} were you referring to?')
                            response = input('> ')

                            # Try to satisfy just this field of the whole frame:
                            _, frame_d = best_r.satisfy(response, {f.name: f})
                            if field in frame_d[f.name].bindings:
                                f.bindings[field] = frame_d[f.name].bindings[field]  # Apply the acquired info.
                                print(f'Got it! Your {field} is {f.bindings[field]}.')
                                break
                            else:
                                # Keep asking until a satisfying answer is given.
                                print("I still do not understand.")

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


