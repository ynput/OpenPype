# **Process Monitor**

## **Description**

Module to manage the timers.

When an application is started, an entry is added to the Process Monitor, which will keep the timer running until the application closes.

If another application is started, its timer will become the active one, and the previously running timer will be stopped.

When closing an application, if its timer is the currently running one, it will be stopped, and another timer will resume if possible:
* If only 1 other application is running, its timer will become active.
* If more than 1 applications are running, the module will ask the user to select the current application to determine which timer to resume.
    * In the specific case where all the running applications are tied to the same context (project+asset+task), any timer will be automatically resumed, as the timers don't specify which application they are attached to, making them all "equal".

The list of running processes is visible in the "Process Monitor" window, accessible via the OpenPype tray.

In the Process Monitor window, it is possible to stop the current running timer, or to resume a timer for any of the currently running applications:
* Right-click on the process enbtry opens a contextual menu with the options to start/stop the process timer.
* Double-click on the process entry will resume the time (if not already currently running).


**TODO:** Add details about the implementation!


## **Application Processes**

In most cases, a single process is spawned for an application, and terminated when closing the application. Watching for the application termination is thus straightforward by keeping track of the process idemtifier.

However, some applications spawn children processes, and either keep running or terminates.

Because of this, watching for the spawned process termination is not enough to accurately track running processes, and special management is required.

Following is a list of behaviours for different applications.

**NOTE:** All the following tests have been made in Windows. The processes spawned by each application might differ on Linux.

**TODO:** Testing is required in Linux!


### **Single Process**

Simple case, single process.

The following applications are a single process:
* Blender
* Houdini
* Illustrator
* Painter
* Unreal Engine (*)
* ZBrush
* (more to test)

(*) - A different behaviour can occur if opening Unreal Engine without a project (see below). This should however not happen in normal situations.


### **Multiple Processes**

The following applications spawn more than 1 process when started.

* **Maya**
    * When closing, Maya's main process may or may not spawn background daemon processes.
        * The behaviour is not always the same.
        * An example of spawned process is "ADPClientService".
    * Hence, the children process should not replace the running process, as they will continue to live after the application has been closed (keeping the timer running - which is not desired).

* **3DSMAX**
    * 3DSMAX being an Autodesk software, as the same behaviour as Maya.

* **Premiere**
    * When closing, Premiere can also spawn background daemon processes.
        * The behaviour is not always the same.
        * An example of spawned process is "dynamiclinkmanager".
    * Hence, the children process should not replace the running process.
        * However, the children processes terminate shortly after closing the application, so it would not be an issue to watch them instead of the main process.
        * For consistency and easier management, the same behaviour as for the Autodesk processes is used.

* **Media Encoder**
    * Same as premiere.

* **Unreal Engine**
    * Tested with UE5.
    * When starting Unreal Engine with a project, a single process is spawned, which will be the main process.
    * However, a different behaviour can occur if opening Unreal Engine without a project. This should not happen in normal situations, it is however mentionned here for completeness.
        * The "Unreal Project Browser" opens. This is an instance of the main "UnrealEditor" process.
        * When opening a project, the process spawns a child process then terminates.
        * The spawned process is a new instance of the same process ("UnrealEditor"), with passed parameters (the project file).
        * In this case, the child process must replace its terminated parent, as it needs to keep the timer running.

* **Photoshop**
    * The original process is a Python script launching the application (started by "openpype_gui").
    * The process continues running until its children terminate.
    * There is thus no need to replace the running process by its child, as they will both terminate together.

* **Nuke** (as well as **NukeX** and **NukeStudio**)
    * The main process spawns a few children processes, but they all terminate when closing the main process.
    * Additionally, the main process seems to be the last process to terminate.
    * There is thus no need to replace the running process by its child, as they will both terminate together.
