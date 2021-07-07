Automatic tests for OpenPype
============================
Structure:
- integration - end to end tests, slow
    - openpype/modules/MODULE_NAME - structure follow directory structure in code base
        - fixture - sample data `(MongoDB dumps, test files etc.)`
        - `tests.py` - single or more pytest files for MODULE_NAME
- unit - quick unit test 
    - MODULE_NAME   
        - fixture
        - `tests.py`
    
