import json

from typing import List


def parse_concatenated_json(json_str: str) -> List:
    """Parse a string with several concatenated JSON objects

    JSON is a nasty format.  It's neither optimized for
    human-readability, nor for machine processing.  The only benefit
    is how widely it is available.

    - Can't incrementally parse.  The entire object is either valid or
      invalid.  Cannot access the first element of a list.

    - No trailing commas.  Just my pet peeve.  If I have a list and I
      append a single item to it, that should be a single insertion in
      the diff.

    - Can't concatenate files without parsing.  If I have collected
      data from multiple different sources (e.g. benchmarking under
      several different environments), and I want to make a single
      dataset with all elements, I cannot just concatenate the files.
      Instead, I need to parse each one, concatenate the resulting
      objects, then serialize the results.

    Using `*.jsonl` is a bit better, as it can be parsed line-by-line,
    can be concatenated, and allows data files to be concatenated
    together.  However, it adds a

    - Can't pretty-print, as new-line characters inside an object
      would mean that "split at new-lines" and "split between objects"
      are different operations.  What's the point of having a
      human-readable text format if it can't be made easy to read?

    A better option altogether is to parse a string up through the end
    of the first valid JSON object, then continue parsing for the next
    JSON object.



    """

    index = 0
    decoder = json.JSONDecoder()

    output = []
    while True:
        index = json.decoder.WHITESPACE.match(json_str, index).end()

        if index >= len(json_str):
            break

        obj, index = decoder.raw_decode(json_str, idx=index)

        output.append(obj)

    return output
