# general questions
- is there any particular reason we are not having __init__.py files in integration branch?


# workfile fixture in host
- activating `IWorkfileHost` so workio could be used
- so we know if `AVALON_LAST_WORKFILE` env var will be filled after host is activated in some context?
- I wish to implement `openpype\pipeline\workfile\workfile_template_builder.py:551` as fixture, would it be possible?
- here is perhaps how to create the last workfile path `openpype\lib\applications.py`:1800
- to be able to implement this workfile create test now I would need to rewrite `NukeHostFixtures.last_workfile_path` fixture so it would return generated workfile with workio.
- I will need to have:
  -  defined shot start/end with handles
  -  settings for bypassing workfile tool opening after launch. Here is perhaps how to do it `openpype\lib\applications.py`:1721
