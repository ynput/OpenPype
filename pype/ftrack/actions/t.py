 import model
# model

name = model.data(index, "name")

# Get the action
Action = next((a for a in self._registered_actions if a.name == name),
              None)
assert Action, "No action found"
action = Action()

# Run the action within current session
self.log("Running action: %s" % name, level=INFO)
popen = action.process(api.Session.copy())
# Action might return popen that pipes stdout
# in which case we listen for it.
process = {}
if popen and hasattr(popen, "stdout") and popen.stdout is not None:

    class Thread(QtCore.QThread):
        messaged = Signal(str)

        def run(self):
            for line in lib.stream(process["popen"].stdout):
                self.messaged.emit(line.rstrip())
            self.messaged.emit("%s killed." % process["name"])

    thread = Thread()
    thread.messaged.connect(
        lambda line: terminal.log(line, terminal.INFO)
    )

    process.update({
        "name": name,
        "action": action,
        "thread": thread,
        "popen": popen
    })

    self._processes.append(process)

    thread.start()

# return process
