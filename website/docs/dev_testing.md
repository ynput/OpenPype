---
id: dev_testing
title: Testing in OpenPype
sidebar_label: Testing
---

## Introduction
As OpenPype is growing there also grows need for automatic testing. There are already bunch of tests present in root folder of OpenPype directory.
But many tests should be yet created!

### How to run tests

If you would like to experiment with provided tests, and have particular DCC installed on your machine, you could run test for this DCC by:

- From source:
```
- use Openpype command 'runtests' from command line (`.venv` in ${OPENPYPE_ROOT} must be activated to use configured Python!)
- `python ${OPENPYPE_ROOT}/start.py runtests ../tests/integration/hosts/nuke`
```
- From build:
```
- ${OPENPYPE_BUILD}/openpype_console run {ABSOLUT_PATH_OPENPYPE_ROOT}/tests/integration/hosts/nuke`
```


### Content of tests folder

Main tests folder contains hierarchy of folders with tests and supporting lib files. It is intended that tests should be run separately in each folder in the hierarchy.

Main folders in the structure:
- integration - end to end tests in applications, mimicking regular publishing process 
- lib - helper classes
- resources - test data skeletons etc.
- unit - unit test covering methods and functions in OP


### lib folder

This location should contain library of helpers and miscellaneous classes used for integration or unit tests.

Content:
- `assert_classes.py` - helpers for easier use of assert expressions
- `db_handler.py` - class for creation of DB dumps/restore/purge
- `file_hanlder.py` - class for preparation/cleanup of test data
- `testing_classes.py` - base classes for testing of publish in various DCCs

### integration folder

Contains end to end testing in DCC. Currently it is setup to start DCC application with prepared worfkile, run publish process and compare results in DB and file system automatically.
This approach is implemented as it should work in any DCC application and should cover most common use cases.

There will be also possibility to build workfile and publish it programmatically, this would work only in DCCs that support it (Maya, Nuke).

It is expected that each test class should work with single worfkile with supporting resources (as a dump of project DB, all necessary environment variables, expected published files etc.)

There are currently implemented basic publish tests for `Maya`, `Nuke`, `AfterEffects` and `Photoshop`. Additional hosts will be added.

Each `test_` class should contain single test class based on `tests.lib.testing_classes.PublishTest`. This base class handles all necessary 
functionality for testing in a host application.

#### Steps of publish test

Each publish test is consisted of areas: 
- preparation
- launch of host application
- publish 
- comparison of results in DB and file system
- cleanup

##### Preparation

For each test publish case is expected zip file with this structure:
- expected - published files after workfile is published (in same structure as in regular manual publish)
- input
    - dumps - database dumps (check `tests.lib.db_handler` for implemented functionality)
        - openpype - settings 
        - test_db - skeleton of test project (contains project document, asset document etc.)
    - env_vars - `env_var.json` file with a dictionary of all required environment variables
    - json - json files with human readable content of databases
    - startup - any required initialization scripts (for example Nuke requires one `init.py` file)
    - workfile - contains single workfile
    
These folders needs to be zipped (in zip's root must be this structure directly!), currently zip files for all prepared tests are stored in OpenPype GDrive folder.

##### Launch of application and publish

Integration tests are using same approach as OpenPype process regarding launching of host applications (eg. `ApplicationManager().launch`).
Each host application is in charge of triggering of publish process and closing itself. Different hosts handle this differently, Adobe products are handling this via injected "HEADLESS_PUBLISH" environment variable,
Maya and Nuke must contain this in their's startup files.

Base `PublishTest` class contains configurable timeout in case of publish process is not working, or taking too long.

##### Comparison of results

Each test class requires re-iplemented `PublishTest.test_db_asserts` fixture. This method is triggered after publish is finished and should
compare current results in DB (each test has its own database which gets filled with dump data first, cleaned up after test finishing) with expected results.

`tests.lib.assert_classes.py` contains prepared method `count_of_types` which makes easier to write assert expression.

Basic use case:
```DBAssert.count_of_types(dbcon, "version", 2)``` >> It is expected that DB contains only 2 documents of `type==version`

If zip file contains file structure in `expected` folder, `PublishTest.test_folder_structure_same` implements comparison of expected and published file structure,
eg. if test case published all expected files.

##### Cleanup

By default, each test case pulls data from GDrive, unzips them in temporary folder, runs publish, compares results and then
purges created temporary test database and temporary folder. This could be changed by setting of `PublishTest.PERSIST`.

In case you want to modify test data, use `PublishTest.TEST_DATA_FOLDER` to point test to specific location.

Both options are mostly useful for debugging during implementation of new test cases.

#### Test configuration

Each test case could be configured from command line with:
- test_data_folder - use specific folder with extracted test zip file 
- persist - keep content of temporary folder and database after test finishes
- app_variant - run test for specific version of host app, matches app variants in Settings, eg. `2021` for Photoshop, `12-2` for Nuke
- timeout - override default time (in seconds)

### unit folder

Here should be located unit tests for classes, methods etc. As most classes expect to be triggered in OpenPype context, best option is to
start these test in similar fashion as `integration` tests (eg. via `runtests`).