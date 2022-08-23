Integration test for OpenPype
=============================
Contains end-to-end tests for automatic testing of OP.

Should run headless publish on all hosts to check basic publish use cases automatically
to limit regression issues.

Uses env var `HEADLESS_PUBLISH` (set in test data zip files) to differentiate between regular publish
and "automated" one.

How to run
----------
- activate `{OPENPYPE_ROOT}/.venv`
- run in cmd
`{OPENPYPE_ROOT}/.venv/Scripts/python.exe {OPENPYPE_ROOT}/start.py runtests {OPENPYPE_ROOT}/tests/integration`
  - add `hosts/APP_NAME` after integration part to limit only on specific app (eg. `{OPENPYPE_ROOT}/tests/integration/hosts/maya`)
  
OR can use built executables 
`openpype_console runtests {ABS_PATH}/tests/integration`

How to check logs/errors from app
--------------------------------
Keep PERSIST to True in the class and check `test_openpype.logs` collection. 

How to create test for publishing from host
------------------------------------------
- Extend PublishTest in `tests/lib/testing_classes.py`
- Use `resources\test_data.zip` skeleton file as a template for testing input data
- Put workfile into `test_data.zip/input/workfile`
- If you require other than base DB dumps provide them to `test_data.zip/input/dumps`
-- (Check commented code in `db_handler.py` how to dump specific DB. Currently all collections will be dumped.)
- Implement `last_workfile_path` 
- `startup_scripts` - must contain pointing host to startup script saved into `test_data.zip/input/startup`
  -- Script must contain something like (pseudocode)
```
import openpype
from avalon import api, HOST

from openpype.api import Logger

log = Logger().get_logger(__name__)
  
api.install(HOST)
log_lines = []
for result in pyblish.util.publish_iter():
    for record in result["records"]:  # for logging to test_openpype DB
        log_lines.append("{}: {}".format(
            result["plugin"].label, record.msg))

    if result["error"]:
        err_fmt = "Failed {plugin.__name__}: {error} -- {error.traceback}"
        log.error(err_fmt.format(**result))

EXIT_APP (command to exit host)
```
(Install and publish methods must be triggered only AFTER host app is fully initialized!)
- If you would like add any command line arguments for your host app add it to `test_data.zip/input/app_args/app_args.json` (as a json list)
- Provide any required environment variables to `test_data.zip/input/env_vars/env_vars.json` (as a json dictionary)
- Zip `test_data.zip`, named it with descriptive name, upload it to Google Drive, right click - `Get link`, copy hash id (file must be accessible to anyone with a link!)
- Put this hash id and zip file name into TEST_FILES [(HASH_ID, FILE_NAME, MD5_OPTIONAL)]. If you want to check MD5 of downloaded 
file, provide md5 value of zipped file.
- Implement any assert checks you need in extended class
- Run test class manually (via Pycharm or pytest runner (TODO))
- If you want test to visually compare expected files to published one, set PERSIST to True, run test manually
  -- Locate temporary `publish` subfolder of temporary folder (found in debugging console log)
  -- Copy whole folder content into .zip file into `expected` subfolder 
  -- By default tests are comparing only structure of `expected` and published format (eg. if you want to save space, replace published files with empty files, but with expected names!)
  -- Zip and upload again, change PERSIST to False
  
- Use `TEST_DATA_FOLDER` variable in your class to reuse existing downloaded and unzipped test data (for faster creation of tests)
- Keep `APP_VARIANT` empty if you want to trigger test on latest version of app, or provide explicit value (as '2022' for Photoshop for example)