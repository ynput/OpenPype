import os

from .vendor.Qt import QtWidgets


class Action(QtWidgets.QAction):
    """Custom Action widget"""

    def __init__(self, parent=None):

        QtWidgets.QAction.__init__(self, parent)

        self._root = None
        self._tags = list()
        self._command = None
        self._sourcetype = None
        self._iconfile = None
        self._label = None

        self._COMMAND = """import imp
f, filepath, descr = imp.find_module('{module_name}', ['{dirname}'])
module = imp.load_module('{module_name}', f, filepath, descr)
module.{module_name}()"""

    @property
    def root(self):
        return self._root

    @root.setter
    def root(self, value):
        self._root = value

    @property
    def tags(self):
        return self._tags

    @tags.setter
    def tags(self, value):
        self._tags = value

    @property
    def command(self):
        return self._command

    @command.setter
    def command(self, value):
        """
        Store the command in the QAction 

        Args:
            value (str): the full command which will be executed when clicked
        
        Return:
             None
        """
        self._command = value

    @property
    def sourcetype(self):
        return self._sourcetype

    @sourcetype.setter
    def sourcetype(self, value):
        """
        Set the command type to get the correct execution of the command given

        Args:
            value (str): the name of the command type
        
        Returns:
            None

        """
        self._sourcetype = value

    @property
    def iconfile(self):
        return self._iconfile

    @iconfile.setter
    def iconfile(self, value):
        """Store the path to the image file which needs to be displayed

        Args:
            value (str): the path to the image

        Returns:
            None
        """
        self._iconfile = value

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        """
        Set the abbreviation which will be used as overlay text in the shelf

        Args:
            value (str): an abbreviation of the name
        
        Returns:
            None

        """
        self._label = value

    def run_command(self):
        """
        Run the command of the instance or copy the command to the active shelf
        based on the current modifiers.

        If callbacks have been registered with fouind modifier integer the
        function will trigger all callbacks. When a callback function returns a
        non zero integer it will not execute the action's command

        """

        # get the current application and its linked keyboard modifiers
        app = QtWidgets.QApplication.instance()
        modifiers = app.keyboardModifiers()

        # If the menu has a callback registered for the current modifier
        # we run the callback instead of the action itself.
        registered = self._root.registered_callbacks
        callbacks = registered.get(int(modifiers), [])
        for callback in callbacks:
            signal = callback(self)
            if signal != 0:
                # Exit function on non-zero return code
                return

        exec(self.process_command())

    def process_command(self):
        """
        Check if the command is a file which needs to be launched and if it 
        has a relative path, if so return the full path by expanding 
        environment variables. Wrap any mel command in a executable string 
        for Python and return the string if the source type is  
        
        Add your own source type and required process to ensure callback
        is stored correctly.
        
        An example of a process is the sourcetype is MEL 
        (Maya Embedded Language) as Python cannot run it on its own so it 
        needs to be wrapped in a string in which we explicitly import mel and 
        run it as a mel.eval. The string is then parsed to python as 
        exec("command"). 

        Returns:
            str: a clean command which can be used

        """
        if self._sourcetype == "python":
            return self._command

        if self._sourcetype == "mel":
            # Escape single quotes
            conversion = self._command.replace("'", "\\'")
            return "import maya; maya.mel.eval('{}')".format(conversion)

        if self._sourcetype == "file":
            if os.path.isabs(self._command):
                filepath = self._command
            else:
                filepath = os.path.normpath(os.path.expandvars(self._command))

            return self._wrap_filepath(filepath)

    def has_tag(self, tag):
        """Check whether the tag matches with the action's tags.
        
        A partial match will also return True, for example tag `a` will match
        correctly with the `ape` tag on the Action.

        Args:
            tag (str): The tag
        
        Returns
            bool: Whether the action is tagged with given tag
        
        """

        for tagitem in self.tags:
            if tag not in tagitem:
                continue
            return True

        return False

    def _wrap_filepath(self, file_path):
        """Create a wrapped string for the python command

        Args:
            file_path (str): the filepath of a script

        Returns:
            str: the wrapped command
        """

        dirname = os.path.dirname(r"{}".format(file_path))
        dirpath = dirname.replace("\\", "/")
        module_name = os.path.splitext(os.path.basename(file_path))[0]

        return self._COMMAND.format(module_name=module_name, dirname=dirpath)
