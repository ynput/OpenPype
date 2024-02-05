"""Simplified wrapper for 'click' python module.

Module 'click' is used as main cli handler in AYON/OpenPype. Addons can
register their own subcommands with options. This wrapper allows to define
commands and options as with 'click', but without any dependency.

Why not to use 'click' directly? Version of 'click' used in AYON/OpenPype
is not compatible with 'click' version used in some DCCs (e.g. Houdini 20+).
And updating 'click' would break other DCCs.

How to use it? If you already have cli commands defined in addon, just replace
'click' with 'click_wrap' and it should work and modify your addon's cli
method to convert 'click_wrap' object to 'click' object.

Before
```python
import click
from openpype.modules import OpenPypeModule


class ExampleAddon(OpenPypeModule):
    name = "example"

    def cli(self, click_group):
        click_group.add_command(cli_main)


@click.group(ExampleAddon.name, help="Example addon")
def cli_main():
    pass


@cli_main.command(help="Example command")
@click.option("--arg1", help="Example argument 1", default="default1")
@click.option("--arg2", help="Example argument 2", is_flag=True)
def mycommand(arg1, arg2):
    print(arg1, arg2)
```

Now
```
from openpype import click_wrap
from openpype.modules import OpenPypeModule


class ExampleAddon(OpenPypeModule):
    name = "example"

    def cli(self, click_group):
        click_group.add_command(cli_main.to_click_obj())


@click_wrap.group(ExampleAddon.name, help="Example addon")
def cli_main():
    pass


@cli_main.command(help="Example command")
@click_wrap.option("--arg1", help="Example argument 1", default="default1")
@click_wrap.option("--arg2", help="Example argument 2", is_flag=True)
def mycommand(arg1, arg2):
    print(arg1, arg2)
```


Added small enhancements:
- most of the methods can be used as chained calls
- functions/methods 'command' and 'group' can be used in a way that
    first argument is callback function and the rest are arguments
    for click

Example:
    ```python
    from openpype import click_wrap
    from openpype.modules import OpenPypeModule


    class ExampleAddon(OpenPypeModule):
        name = "example"

        def cli(self, click_group):
            # Define main command (name 'example')
            main = click_wrap.group(
                self._cli_main, name=self.name, help="Example addon"
            )
            # Add subcommand (name 'mycommand')
            (
                main.command(
                    self._cli_command, name="mycommand", help="Example command"
                )
                .option(
                    "--arg1", help="Example argument 1", default="default1"
                )
                .option(
                    "--arg2", help="Example argument 2", is_flag=True,
                )
            )
            # Convert main command to click object and add it to parent group
            click_group.add_command(main.to_click_obj())

        def _cli_main(self):
            pass

        def _cli_command(self, arg1, arg2):
            print(arg1, arg2)
    ```

    ```shell
    openpype_console addon example mycommand --arg1 value1 --arg2
    ```
"""

import collections

FUNC_ATTR_NAME = "__ayon_cli_options__"


class Command(object):
    def __init__(self, func, *args, **kwargs):
        # Command function
        self._func = func
        # Command definition arguments
        self._args = args
        # Command definition kwargs
        self._kwargs = kwargs
        # Both 'options' and 'arguments' are stored to the same variable
        #   - keep order of options and arguments
        self._options = getattr(func, FUNC_ATTR_NAME, [])

    def to_click_obj(self):
        """Converts this object to click object.

        Returns:
            click.Command: Click command object.
        """
        return convert_to_click(self)

    # --- Methods for 'convert_to_click' function ---
    def get_args(self):
        """
        Returns:
            tuple: Command definition arguments.
        """
        return self._args

    def get_kwargs(self):
        """
        Returns:
            dict[str, Any]: Command definition kwargs.
        """
        return self._kwargs

    def get_func(self):
        """
        Returns:
            Function: Function to invoke on command trigger.
        """
        return self._func

    def iter_options(self):
        """
        Yields:
            tuple[str, tuple, dict]: Option type name with args and kwargs.
        """
        for item in self._options:
            yield item
    # -----------------------------------------------

    def add_option(self, *args, **kwargs):
        return self.add_option_by_type("option", *args, **kwargs)

    def add_argument(self, *args, **kwargs):
        return self.add_option_by_type("argument", *args, **kwargs)

    option = add_option
    argument = add_argument

    def add_option_by_type(self, option_name, *args, **kwargs):
        self._options.append((option_name, args, kwargs))
        return self


class Group(Command):
    def __init__(self, func, *args, **kwargs):
        super(Group, self).__init__(func, *args, **kwargs)
        # Store sub-groupd and sub-commands to the same variable
        self._commands = []

    # --- Methods for 'convert_to_click' function ---
    def iter_commands(self):
        for command in self._commands:
            yield command
    # -----------------------------------------------

    def add_command(self, command):
        """Add prepared command object as child.

        Args:
            command (Command): Prepared command object.
        """
        if command not in self._commands:
            self._commands.append(command)

    def add_group(self, group):
        """Add prepared group object as child.

        Args:
            group (Group): Prepared group object.
        """
        if group not in self._commands:
            self._commands.append(group)

    def command(self, *args, **kwargs):
        """Add child command.

        Returns:
            Union[Command, Function]: New command object, or wrapper function.
        """
        return self._add_new(Command, *args, **kwargs)

    def group(self, *args, **kwargs):
        """Add child group.

        Returns:
            Union[Group, Function]: New group object, or wrapper function.
        """
        return self._add_new(Group, *args, **kwargs)

    def _add_new(self, target_cls, *args, **kwargs):
        func = None
        if args and callable(args[0]):
            args = list(args)
            func = args.pop(0)
            args = tuple(args)

        def decorator(_func):
            out = target_cls(_func, *args, **kwargs)
            self._commands.append(out)
            return out

        if func is not None:
            return decorator(func)
        return decorator


def convert_to_click(obj_to_convert):
    """Convert wrapped object to click object.

    Args:
        obj_to_convert (Command): Object to convert to click object.

    Returns:
        click.Command: Click command object.
    """
    import click

    commands_queue = collections.deque()
    commands_queue.append((obj_to_convert, None))
    top_obj = None
    while commands_queue:
        item = commands_queue.popleft()
        command_obj, parent_obj = item
        if not isinstance(command_obj, Command):
            raise TypeError(
                "Invalid type '{}' expected 'Command'".format(
                    type(command_obj)
                )
            )

        if isinstance(command_obj, Group):
            click_obj = (
                click.group(
                    *command_obj.get_args(),
                    **command_obj.get_kwargs()
                )(command_obj.get_func())
            )

        else:
            click_obj = (
                click.command(
                    *command_obj.get_args(),
                    **command_obj.get_kwargs()
                )(command_obj.get_func())
            )

        for item in command_obj.iter_options():
            option_name, args, kwargs = item
            if option_name == "option":
                click.option(*args, **kwargs)(click_obj)
            elif option_name == "argument":
                click.argument(*args, **kwargs)(click_obj)
            else:
                raise ValueError(
                    "Invalid option name '{}'".format(option_name)
                )

        if top_obj is None:
            top_obj = click_obj

        if parent_obj is not None:
            parent_obj.add_command(click_obj)

        if isinstance(command_obj, Group):
            for command in command_obj.iter_commands():
                commands_queue.append((command, click_obj))

    return top_obj


def group(*args, **kwargs):
    func = None
    if args and callable(args[0]):
        args = list(args)
        func = args.pop(0)
        args = tuple(args)

    def decorator(_func):
        return Group(_func, *args, **kwargs)

    if func is not None:
        return decorator(func)
    return decorator


def command(*args, **kwargs):
    func = None
    if args and callable(args[0]):
        args = list(args)
        func = args.pop(0)
        args = tuple(args)

    def decorator(_func):
        return Command(_func, *args, **kwargs)

    if func is not None:
        return decorator(func)
    return decorator


def argument(*args, **kwargs):
    def decorator(func):
        return _add_option_to_func(
            func, "argument", *args, **kwargs
        )
    return decorator


def option(*args, **kwargs):
    def decorator(func):
        return _add_option_to_func(
            func, "option", *args, **kwargs
        )
    return decorator


def _add_option_to_func(func, option_name, *args, **kwargs):
    if isinstance(func, Command):
        func.add_option_by_type(option_name, *args, **kwargs)
        return func

    if not hasattr(func, FUNC_ATTR_NAME):
        setattr(func, FUNC_ATTR_NAME, [])
    cli_options = getattr(func, FUNC_ATTR_NAME)
    cli_options.append((option_name, args, kwargs))
    return func
