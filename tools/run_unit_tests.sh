export OPENPYPE_DATABASE_NAME=test;
export PYTHONPATH="./;./repos/avalon-core;$PYTHONPATH";
pytest openpype/modules/shotgrid --capture=sys --print -W ignore::DeprecationWarning
