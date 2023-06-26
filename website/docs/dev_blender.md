---
id: dev_blender
title: Blender integration
sidebar_label: Blender integration
toc_max_heading_level: 4
---

## Run python script at launch
In case you need to execute a python script when Blender is started (aka [`-P`](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html#python-options)), for example to programmatically modify a blender file for conformation, you can create an OpenPype hook as follows:

```python
from openpype.hosts.blender.hooks import pre_add_run_python_script_arg
from openpype.lib import PreLaunchHook


class MyHook(PreLaunchHook):
    """Add python script to be executed before Blender launch."""

    order = pre_add_run_python_script_arg.AddPythonScriptToLaunchArgs.order - 1
    app_groups = [
        "blender",
    ]

    def execute(self):
        self.launch_context.data.setdefault("python_scripts", []).append(
            "/path/to/my_script.py"
        )
```

You can write a bare python script, as you could run into the [Text Editor](https://docs.blender.org/manual/en/latest/editors/text_editor.html).

### Python script with arguments
#### Adding arguments
In case you need to pass arguments to your script, you can append them to `self.launch_context.data["script_args"]`:

```python
self.launch_context.data.setdefault("script_args", []).append(
        "--my-arg",
        "value",
    )
```

#### Parsing arguments
You can parse arguments in your script using [argparse](https://docs.python.org/3/library/argparse.html) as follows:

```python
import argparse

parser = argparse.ArgumentParser(
    description="Parsing arguments for my_script.py"
)
parser.add_argument(
    "--my-arg",
    nargs="?",
    help="My argument",
)
args, unknown = arg_parser.parse_known_args(
    sys.argv[sys.argv.index("--") + 1 :]
)
print(args.my_arg)
```
