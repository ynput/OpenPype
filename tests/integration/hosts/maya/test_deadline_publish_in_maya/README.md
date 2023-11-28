Test data
---------
Each class implementing `TestCase` can provide test file(s) by adding them to
TEST_FILES ('GDRIVE_FILE_ID', 'ACTUAL_FILE_NAME', 'MD5HASH')

GDRIVE_FILE_ID can be pulled from shareable link from Google Drive app.

Currently it is expected that test file will be zip file with structure:
- expected - expected files (not implemented yet)
- input
    - data - test data (workfiles, images etc)
    - dumps - folder for BSOn dumps from (`mongodump`)
    - env_vars
        env_vars.json - dictionary with environment variables {key:value}

    - sql - sql files to load with `mongoimport` (human readable)
    - startup - scripts that should run in the host on its startup
