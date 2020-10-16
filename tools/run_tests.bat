set PYTHONPATH=".;%PYTHONPATH%"
pytest -x --capture=sys --print -W ignore::DeprecationWarning ./tests
