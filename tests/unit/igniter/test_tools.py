# -*- coding: utf-8 -*-
from uuid import uuid4
from igniter.tools import validate_path_string


def test_validate_path_string(tmp_path):
    # test path
    status1, _ = validate_path_string(tmp_path.as_posix())
    assert status1 is True
    status2, _ = validate_path_string("booo" + str(uuid4()))
    assert status2 is False

