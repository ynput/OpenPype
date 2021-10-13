Integration test for OpenPype
=============================
Contains end-to-end tests for automatic testing of OP.

Should run headless publish on all hosts to check basic publish use cases automatically
to limit regression issues.

How to create test for publishing from host
------------------------------------------
- Extend PublishTest
- Use `resources\test_data.zip` skeleton file as a template for testing input data
- Put workfile into `test_data.zip/input/workfile`
- If you require other than base DB dumps provide them to `test_data.zip/input/dumps`
-- (Check commented code in `db_handler.py` how to dump specific DB. Currently all collections will be dumped.)
- Implement `last_workfile_path` 
- `startup_scripts` - must contain pointing host to startup script saved into `test_data.zip/input/startup`
  -- Script must contain something like 
```
import openpype
from avalon import api, HOST
  
api.install(HOST)
pyblish.util.publish()

EXIT_APP (command to exit host)
```
(Install and publish methods must be triggered only AFTER host app is fully initialized!)
- Zip `test_data.zip`, named it with descriptive name, upload it to Google Drive, right click - `Get link`, copy hash id
- Put this hash id and zip file name into TEST_FILES [(HASH_ID, FILE_NAME, MD5_OPTIONAL)]. If you want to check MD5 of downloaded 
file, provide md5 value of zipped file.
- Implement any assert checks you need in extended class
- Run test class manually (via Pycharm or pytest runner (TODO))
- If you want test to compare expected files to published one, set PERSIST to True, run test manually
  -- Locate temporary `publish` subfolder of temporary folder (found in debugging console log)
  -- Copy whole folder content into .zip file into `expected` subfolder 
  -- By default tests are comparing only structure of `expected` and published format (eg. if you want to save space, replace published files with empty files, but with expected names!)
  -- Zip and upload again, change PERSIST to False