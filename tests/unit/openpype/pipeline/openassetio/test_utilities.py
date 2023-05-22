import pytest
from openpype.pipeline.openassetio import utilities

# list of tuples of entity references and if they are valid
test_data = [
    # valid - main
    ("op://projectX/assets/chars/Bob/modelMain?version=1#abc", True),
    # valid with flat hierarchy
    ("op://projectX/Bob/modelMain?version=1#abc", True),
    # invalid schema
    ("xx://projectX/assets/chars/Bob/modelMain?version=1#abc", False),
    # invalid - version not integer
    ("op://projectX/assets/chars/Bob/modelMain?version=v01#abc", False),
    # invalid - version is missing
    ("op://projectX/assets/chars/Bob/modelMain?#abc", False),
    # invalid - representation name is missing
    ("op://projectX/assets/chars/Bob/modelMain?version=1", False),
    # invalid - no asset
    ("op://projectX/modelMain?version=1#abc", False),
    # invalid - port part specified
    ("op://projectX:80/assets/chars/Bob/modelMain?version=1#abc", False),
    # invalid - user part specified
    ("op://user@projectX/assets/chars/Bob/modelMain?version=1#abc", False),
    # invalid - user and password specified
    ("op://user:pwd@projectX/assets/chars/Bob/modelMain?version=1#abc", False),
    # invalid - empty string
    ("", False),
    # invalid - None type
    (None, False),
]

def test_parse_reference(printer):

    for entity_ref in test_data:
        result = utilities.ManagerBase.parse_reference(entity_ref[0])
        assert False
