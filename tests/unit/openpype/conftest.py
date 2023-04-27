"""Dummy environment that allows importing Openpype modules and run
tests in parent folder and all subfolders manually from IDE.

This should not get triggered if the tests are running from `runtests` as it
is expected there that environment is handled by OP itself.

This environment should be enough to run simple `BaseTest` where no
external preparation is necessary (eg. no prepared DB, no source files).
These tests might be enough to import and run simple pyblish plugins to
validate logic.

Please be aware that these tests might use values in real databases, so use
`BaseTest` only for logic without side effects or special configuration. For
these there is `tests.lib.testing_classes.ModuleUnitTest` which would setup
proper test DB (but it requires `mongorestore` on the sys.path)

If pyblish plugins require any host dependent communication, it would need
 to be mocked.

This setting of env vars is necessary to run before any imports of OP code!
(This is why it is in `conftest.py` file.)
If your test requires any additional env var, copy this file to folder of your
test, it should only that folder.
"""

import os


if not os.environ.get("IS_TEST"):  # running tests from cmd or CI
    os.environ["OPENPYPE_MONGO"] = "mongodb://localhost:27017"
    os.environ["AVALON_DB"] = "avalon"
    os.environ["OPENPYPE_DATABASE_NAME"] = "openpype"
    os.environ["AVALON_TIMEOUT"] = '3000'
    os.environ["OPENPYPE_DEBUG"] = "1"
    os.environ["AVALON_ASSET"] = "test_asset"
    os.environ["AVALON_PROJECT"] = "test_project"
