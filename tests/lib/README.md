Automatic testing
-----------------
Folder for libs and tooling for automatic testing.

- db_handler.py - class for preparation of test DB
    - dumps DB(s) to BSON (mongodump)
    - loads dump(s) to new DB (mongorestore)
    - loads sql file(s) to DB (mongoimport)
    - deletes test DB
  
- file_handler.py - class to download test data from GDrive
    - downloads data from (list) of files from GDrive
    - check file integrity with MD5 hash
    - unzips if zip
    
- testing_wrapper.py - base class to use for testing
    - all env var necessary for running (OPENPYPE_MONGO ...)
    - implements reusable fixtures to:
        - load test data (uses `file_handler`)
        - prepare DB (uses `db_handler`)
        - modify temporarily env vars for testing
        
    Should be used as a skeleton to create new test cases.


Test data
---------
Each class implementing `TestCase` can provide test file(s) by adding them to
TEST_FILES ('GDRIVE_FILE_ID', 'ACTUAL_FILE_NAME', 'MD5HASH')

GDRIVE_FILE_ID can be pulled from shareable link from Google Drive app.

Currently it is expected that test file will be zip file with structure:
- expected - expected files (not implemented yet)
- input
    - data - test data (workfiles, images etc)
    - dumps - folder for BSON dumps from (`mongodump`)
    - env_vars 
        env_vars.json - dictionary with environment variables {key:value}
        
    - json - json files to load with `mongoimport` (human readable)
    

Example
-------
See `tests\unit\openpype\modules\sync_server\test_site_operations.py` for example usage of implemented classes.