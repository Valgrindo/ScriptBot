"""
A collection of useful utilities.

CS 799.06 Independent Study in NLP
Rochester Institute of Technology
:author: Sergey Goldobin
:date: 08/03/2020 13:17
"""


from bs4 import Tag
from typing import *


def selective_iterator(tag_collection, target_tag, exception_type=None):
    """
    Iterate over a collection of BeautifulSoup tags skipping over all comments, strings, and whitespace.
    Only yield the expected tag and raise an exception if any other tags are encountered.
    :param tag_collection: A bs4 tag collection.
    :param target_tag: The tag to yield.
    :param exception_type: The kind of exception to throw if an illegal tag is encountered.
    :return:
    """
    for elem in tag_collection:
        if not isinstance(elem, Tag):
            # Skip comments, whitespace, etc.
            continue
        if elem.name != target_tag:
            if exception_type is not None:
                raise exception_type(f"Unexpected tag {elem.name}")
            else:
                continue

        yield elem


def compose(f1: Callable[..., Any], f2: Callable[..., Any]) -> Callable:
    """
    Perform a functional composition of two functions.
    :param f1: Any pure unction.
    :param f2: Any pure function.
    :return: A composed pure function.
    """
    return lambda x: f1(f2(x))
