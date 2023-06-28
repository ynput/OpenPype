# Widgets

## Splash Screen

This widget is used for executing a monitoring progress of a process which has been executed on a different thread.

To properly use this widget certain preparation has to be done in order to correctly execute the process and show the
splash screen.

### Prerequisites

In order to run a function or an operation on another thread, a `QtCore.QObject` class needs to be created with the
desired code. The class has to have a method as an entry point for the thread to execute the code.

For utilizing the functionalities of the splash screen, certain signals need to be declared to let it know what is
happening in the thread and how is it progressing. It is also recommended to have a function to set up certain variables
which are needed in the worker's code

For example:
```python
from qtpy import QtCore

class ExampleWorker(QtCore.QObject):
    
    finished = QtCore.Signal()
    failed = QtCore.Signal(str)
    progress = QtCore.Signal(int)
    log = QtCore.Signal(str)
    stage_begin = QtCore.Signal(str)
    
    foo = None
    bar = None
    
    def run(self):
        # The code goes here
        print("Hello world!")
        self.finished.emit()
        
    def setup(self,
              foo: str,
              bar: str,):
        self.foo = foo
        self.bar = bar
```

### Creating the splash screen

```python
import os
from qtpy import QtCore
from pathlib import Path
from openpype.widgets.splash_screen import SplashScreen
from openpype import resources


def exec_plugin_install( engine_path: Path, env: dict = None):
    env = env or os.environ
    q_thread = QtCore.QThread()
    example_worker = ExampleWorker()

    q_thread.started.connect(example_worker.run)
    example_worker.setup(engine_path, env)
    example_worker.moveToThread(q_thread)

    splash_screen = SplashScreen("Executing process ...",
                                 resources.get_openpype_icon_filepath())

    # set up the splash screen with necessary events
    example_worker.installing.connect(splash_screen.update_top_label_text)
    example_worker.progress.connect(splash_screen.update_progress)
    example_worker.log.connect(splash_screen.append_log)
    example_worker.finished.connect(splash_screen.quit_and_close)
    example_worker.failed.connect(splash_screen.fail)

    splash_screen.start_thread(q_thread)
    splash_screen.show_ui()
```

In this example code, before executing the process the worker needs to be instantiated and moved onto a newly created
`QtCore.QThread` object. After this, needed signals have to be connected to the desired slots to make full use of
the splash screen. Finally, the `start_thread` and `show_ui` is called.

**Note that when the `show_ui` function is called the thread is blocked until the splash screen quits automatically, or 
it is closed by the user in case the process fails! The `start_thread` method in that case must be called before
showing the UI!**

The most important signals are
```python
q_thread.started.connect(example_worker.run)
```
 and
```python
example_worker.finished.connect(splash_screen.quit_and_close)
```

These ensure that when the `start_thread` method is called (which takes as a parameter the `QtCore.QThread` object and
saves it as a reference), the `QThread` object starts and signals the worker to
start executing its own code. Once the worker is done and emits a signal that it has finished with the `quit_and_close`
slot, the splash screen quits the `QtCore.QThread` and closes itself.

It is highly recommended to also use the `fail` slot in case an exception or other error occurs during the execution of
the worker's code (You would use in this case the `failed` signal in the `ExampleWorker`).
