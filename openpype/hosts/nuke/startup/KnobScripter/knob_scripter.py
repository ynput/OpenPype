# -------------------------------------------------
# KnobScripter by Adrian Pueyo
# Complete python script editor for Nuke
# adrianpueyo.com, 2016-2019
import string
import traceback
from webbrowser import open as openUrl
from threading import Event, Thread
import platform
import subprocess
from functools import partial
import re
import sys
from nukescripts import panels
import json
import os
import nuke
version = "2.3 wip"
date = "Aug 12 2019"
# -------------------------------------------------


# Symlinks on windows...
if os.name == "nt":
    def symlink_ms(source, link_name):
        import ctypes
        csl = ctypes.windll.kernel32.CreateSymbolicLinkW
        csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        csl.restype = ctypes.c_ubyte
        flags = 1 if os.path.isdir(source) else 0
        try:
            if csl(link_name, source.replace('/', '\\'), flags) == 0:
                raise ctypes.WinError()
        except:
            pass
    os.symlink = symlink_ms

try:
    if nuke.NUKE_VERSION_MAJOR < 11:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt
    else:
        from PySide2 import QtWidgets, QtGui, QtCore
        from PySide2.QtCore import Qt
except ImportError:
    from Qt import QtCore, QtGui, QtWidgets

KS_DIR = os.path.dirname(__file__)
icons_path = KS_DIR + "/icons/"
DebugMode = False
AllKnobScripters = []  # All open instances at a given time

PrefsPanel = ""
SnippetEditPanel = ""

nuke.tprint('KnobScripter v{}, built {}.\nCopyright (c) 2016-2019 Adrian Pueyo. All Rights Reserved.'.format(version, date))


class KnobScripter(QtWidgets.QWidget):

    def __init__(self, node="", knob="knobChanged"):
        super(KnobScripter, self).__init__()

        # Autosave the other knobscripters and add this one
        for ks in AllKnobScripters:
            try:
                ks.autosave()
            except:
                pass
        if self not in AllKnobScripters:
            AllKnobScripters.append(self)

        self.nodeMode = (node != "")
        if node == "":
            self.node = nuke.toNode("root")
        else:
            self.node = node

        self.isPane = False
        self.knob = knob
        # For the option to also display the knob labels on the knob dropdown
        self.show_labels = False
        self.unsavedKnobs = {}
        self.modifiedKnobs = set()
        self.scrollPos = {}
        self.cursorPos = {}
        self.fontSize = 10
        self.font = "Monospace"
        self.tabSpaces = 4
        self.windowDefaultSize = [500, 300]
        self.color_scheme = "sublime"  # Can be nuke or sublime
        self.pinned = 1
        self.toLoadKnob = True
        self.frw_open = False  # Find replace widget closed by default
        self.icon_size = 17
        self.btn_size = 24
        self.qt_icon_size = QtCore.QSize(self.icon_size, self.icon_size)
        self.qt_btn_size = QtCore.QSize(self.btn_size, self.btn_size)
        self.origConsoleText = ""
        self.nukeSE = self.findSE()
        self.nukeSEOutput = self.findSEOutput(self.nukeSE)
        self.nukeSEInput = self.findSEInput(self.nukeSE)
        self.nukeSERunBtn = self.findSERunBtn(self.nukeSE)

        self.scripts_dir = os.path.expandvars(
            os.path.expanduser("~/.nuke/KnobScripter_Scripts"))
        self.current_folder = "scripts"
        self.folder_index = 0
        self.current_script = "Untitled.py"
        self.current_script_modified = False
        self.script_index = 0
        self.toAutosave = False

        # Load prefs
        self.prefs_txt = os.path.expandvars(
            os.path.expanduser("~/.nuke/KnobScripter_Prefs.txt"))
        self.loadedPrefs = self.loadPrefs()
        if self.loadedPrefs != []:
            try:
                if "font_size" in self.loadedPrefs:
                    self.fontSize = self.loadedPrefs['font_size']
                self.windowDefaultSize = [
                    self.loadedPrefs['window_default_w'], self.loadedPrefs['window_default_h']]
                self.tabSpaces = self.loadedPrefs['tab_spaces']
                self.pinned = self.loadedPrefs['pin_default']
                if "font" in self.loadedPrefs:
                    self.font = self.loadedPrefs['font']
                if "color_scheme" in self.loadedPrefs:
                    self.color_scheme = self.loadedPrefs['color_scheme']
                if "show_labels" in self.loadedPrefs:
                    self.show_labels = self.loadedPrefs['show_labels']
            except TypeError:
                log("KnobScripter: Failed to load preferences.")

        # Load snippets
        self.snippets_txt_path = os.path.expandvars(
            os.path.expanduser("~/.nuke/KnobScripter_Snippets.txt"))
        self.snippets = self.loadSnippets(maxDepth=5)

        # Current state of script (loaded when exiting node mode)
        self.state_txt_path = os.path.expandvars(
            os.path.expanduser("~/.nuke/KnobScripter_State.txt"))

        # Init UI
        self.initUI()

        # Talk to Nuke's Script Editor
        self.setSEOutputEvent()  # Make the output windowS listen!
        self.clearConsole()

    def initUI(self):
        ''' Initializes the tool UI'''
        # -------------------
        # 1. MAIN WINDOW
        # -------------------
        self.resize(self.windowDefaultSize[0], self.windowDefaultSize[1])
        self.setWindowTitle("KnobScripter - %s %s" %
                            (self.node.fullName(), self.knob))
        self.setObjectName("com.adrianpueyo.knobscripter")
        self.move(QtGui.QCursor().pos() - QtCore.QPoint(32, 74))

        # ---------------------
        # 2. TOP BAR
        # ---------------------
        # ---
        # 2.1. Left buttons
        self.change_btn = QtWidgets.QToolButton()
        # self.exit_node_btn.setIcon(QtGui.QIcon(KS_DIR+"/KnobScripter/icons/icons8-delete-26.png"))
        self.change_btn.setIcon(QtGui.QIcon(icons_path + "icon_pick.png"))
        self.change_btn.setIconSize(self.qt_icon_size)
        self.change_btn.setFixedSize(self.qt_btn_size)
        self.change_btn.setToolTip(
            "Change to node if selected. Otherwise, change to Script Mode.")
        self.change_btn.clicked.connect(self.changeClicked)

        # ---
        # 2.2.A. Node mode UI
        self.exit_node_btn = QtWidgets.QToolButton()
        self.exit_node_btn.setIcon(QtGui.QIcon(
            icons_path + "icon_exitnode.png"))
        self.exit_node_btn.setIconSize(self.qt_icon_size)
        self.exit_node_btn.setFixedSize(self.qt_btn_size)
        self.exit_node_btn.setToolTip(
            "Exit the node, and change to Script Mode.")
        self.exit_node_btn.clicked.connect(self.exitNodeMode)
        self.current_node_label_node = QtWidgets.QLabel(" Node:")
        self.current_node_label_name = QtWidgets.QLabel(self.node.fullName())
        self.current_node_label_name.setStyleSheet("font-weight:bold;")
        self.current_knob_label = QtWidgets.QLabel("Knob: ")
        self.current_knob_dropdown = QtWidgets.QComboBox()
        self.current_knob_dropdown.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents)
        self.updateKnobDropdown()
        self.current_knob_dropdown.currentIndexChanged.connect(
            lambda: self.loadKnobValue(False, updateDict=True))

        # Layout
        self.node_mode_bar_layout = QtWidgets.QHBoxLayout()
        self.node_mode_bar_layout.addWidget(self.exit_node_btn)
        self.node_mode_bar_layout.addSpacing(2)
        self.node_mode_bar_layout.addWidget(self.current_node_label_node)
        self.node_mode_bar_layout.addWidget(self.current_node_label_name)
        self.node_mode_bar_layout.addSpacing(2)
        self.node_mode_bar_layout.addWidget(self.current_knob_dropdown)
        self.node_mode_bar = QtWidgets.QWidget()
        self.node_mode_bar.setLayout(self.node_mode_bar_layout)

        self.node_mode_bar_layout.setContentsMargins(0, 0, 0, 0)

        # ---
        # 2.2.B. Script mode UI
        self.script_label = QtWidgets.QLabel("Script: ")

        self.current_folder_dropdown = QtWidgets.QComboBox()
        self.current_folder_dropdown.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents)
        self.current_folder_dropdown.currentIndexChanged.connect(
            self.folderDropdownChanged)
        # self.current_folder_dropdown.setEditable(True)
        # self.current_folder_dropdown.lineEdit().setReadOnly(True)
        # self.current_folder_dropdown.lineEdit().setAlignment(Qt.AlignRight)

        self.current_script_dropdown = QtWidgets.QComboBox()
        self.current_script_dropdown.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents)
        self.updateFoldersDropdown()
        self.updateScriptsDropdown()
        self.current_script_dropdown.currentIndexChanged.connect(
            self.scriptDropdownChanged)

        # Layout
        self.script_mode_bar_layout = QtWidgets.QHBoxLayout()
        self.script_mode_bar_layout.addWidget(self.script_label)
        self.script_mode_bar_layout.addSpacing(2)
        self.script_mode_bar_layout.addWidget(self.current_folder_dropdown)
        self.script_mode_bar_layout.addWidget(self.current_script_dropdown)
        self.script_mode_bar = QtWidgets.QWidget()
        self.script_mode_bar.setLayout(self.script_mode_bar_layout)

        self.script_mode_bar_layout.setContentsMargins(0, 0, 0, 0)

        # ---
        # 2.3. File-system buttons
        # Refresh dropdowns
        self.refresh_btn = QtWidgets.QToolButton()
        self.refresh_btn.setIcon(QtGui.QIcon(icons_path + "icon_refresh.png"))
        self.refresh_btn.setIconSize(QtCore.QSize(50, 50))
        self.refresh_btn.setIconSize(self.qt_icon_size)
        self.refresh_btn.setFixedSize(self.qt_btn_size)
        self.refresh_btn.setToolTip("Refresh the dropdowns.\nShortcut: F5")
        self.refresh_btn.setShortcut('F5')
        self.refresh_btn.clicked.connect(self.refreshClicked)

        # Reload script
        self.reload_btn = QtWidgets.QToolButton()
        self.reload_btn.setIcon(QtGui.QIcon(icons_path + "icon_download.png"))
        self.reload_btn.setIconSize(QtCore.QSize(50, 50))
        self.reload_btn.setIconSize(self.qt_icon_size)
        self.reload_btn.setFixedSize(self.qt_btn_size)
        self.reload_btn.setToolTip(
            "Reload the current script. Will overwrite any changes made to it.\nShortcut: Ctrl+R")
        self.reload_btn.setShortcut('Ctrl+R')
        self.reload_btn.clicked.connect(self.reloadClicked)

        # Save script
        self.save_btn = QtWidgets.QToolButton()
        self.save_btn.setIcon(QtGui.QIcon(icons_path + "icon_save.png"))
        self.save_btn.setIconSize(QtCore.QSize(50, 50))
        self.save_btn.setIconSize(self.qt_icon_size)
        self.save_btn.setFixedSize(self.qt_btn_size)
        self.save_btn.setToolTip(
            "Save the script into the selected knob or python file.\nShortcut: Ctrl+S")
        self.save_btn.setShortcut('Ctrl+S')
        self.save_btn.clicked.connect(self.saveClicked)

        # Layout
        self.top_file_bar_layout = QtWidgets.QHBoxLayout()
        self.top_file_bar_layout.addWidget(self.refresh_btn)
        self.top_file_bar_layout.addWidget(self.reload_btn)
        self.top_file_bar_layout.addWidget(self.save_btn)

        # ---
        # 2.4. Right Side buttons

        # Run script
        self.run_script_button = QtWidgets.QToolButton()
        self.run_script_button.setIcon(
            QtGui.QIcon(icons_path + "icon_run.png"))
        self.run_script_button.setIconSize(self.qt_icon_size)
        # self.run_script_button.setIconSize(self.qt_icon_size)
        self.run_script_button.setFixedSize(self.qt_btn_size)
        self.run_script_button.setToolTip(
            "Execute the current selection on the KnobScripter, or the whole script if no selection.\nShortcut: Ctrl+Enter")
        self.run_script_button.clicked.connect(self.runScript)

        # Clear console
        self.clear_console_button = QtWidgets.QToolButton()
        self.clear_console_button.setIcon(
            QtGui.QIcon(icons_path + "icon_clearConsole.png"))
        self.clear_console_button.setIconSize(QtCore.QSize(50, 50))
        self.clear_console_button.setIconSize(self.qt_icon_size)
        self.clear_console_button.setFixedSize(self.qt_btn_size)
        self.clear_console_button.setToolTip(
            "Clear the text in the console window.\nShortcut: Click Backspace on the console.")
        self.clear_console_button.clicked.connect(self.clearConsole)

        # FindReplace button
        self.find_button = QtWidgets.QToolButton()
        self.find_button.setIcon(QtGui.QIcon(icons_path + "icon_search.png"))
        self.find_button.setIconSize(self.qt_icon_size)
        self.find_button.setFixedSize(self.qt_btn_size)
        self.find_button.setToolTip(
            "Call the snippets by writing the shortcut and pressing Tab.\nShortcut: Ctrl+F")
        self.find_button.setShortcut('Ctrl+F')
        #self.find_button.setMaximumWidth(self.find_button.fontMetrics().boundingRect("Find").width() + 20)
        self.find_button.setCheckable(True)
        self.find_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.find_button.clicked[bool].connect(self.toggleFRW)
        if self.frw_open:
            self.find_button.toggle()

        # Snippets
        self.snippets_button = QtWidgets.QToolButton()
        self.snippets_button.setIcon(
            QtGui.QIcon(icons_path + "icon_snippets.png"))
        self.snippets_button.setIconSize(QtCore.QSize(50, 50))
        self.snippets_button.setIconSize(self.qt_icon_size)
        self.snippets_button.setFixedSize(self.qt_btn_size)
        self.snippets_button.setToolTip(
            "Call the snippets by writing the shortcut and pressing Tab.")
        self.snippets_button.clicked.connect(self.openSnippets)

        # PIN
        '''
        self.pin_button = QtWidgets.QPushButton("P")
        self.pin_button.setCheckable(True)
        if self.pinned:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
            self.pin_button.toggle()
        self.pin_button.setToolTip("Toggle 'Always On Top'. Keeps the KnobScripter on top of all other windows.")
        self.pin_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.pin_button.setFixedSize(self.qt_btn_size)
        self.pin_button.clicked[bool].connect(self.pin)
        '''

        # Prefs
        self.createPrefsMenu()
        self.prefs_button = QtWidgets.QPushButton()
        self.prefs_button.setIcon(QtGui.QIcon(icons_path + "icon_prefs.png"))
        self.prefs_button.setIconSize(self.qt_icon_size)
        self.prefs_button.setFixedSize(
            QtCore.QSize(self.btn_size + 10, self.btn_size))
        # self.prefs_button.clicked.connect(self.openPrefs)
        self.prefs_button.setMenu(self.prefsMenu)
        self.prefs_button.setStyleSheet("text-align:left;padding-left:2px;")
        #self.prefs_button.setMaximumWidth(self.prefs_button.fontMetrics().boundingRect("Prefs").width() + 12)

        # Layout
        self.top_right_bar_layout = QtWidgets.QHBoxLayout()
        self.top_right_bar_layout.addWidget(self.run_script_button)
        self.top_right_bar_layout.addWidget(self.clear_console_button)
        self.top_right_bar_layout.addWidget(self.find_button)
        # self.top_right_bar_layout.addWidget(self.snippets_button)
        # self.top_right_bar_layout.addWidget(self.pin_button)
        # self.top_right_bar_layout.addSpacing(10)
        self.top_right_bar_layout.addWidget(self.prefs_button)

        # ---
        # Layout
        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        # self.top_layout.setSpacing(10)
        self.top_layout.addWidget(self.change_btn)
        self.top_layout.addWidget(self.node_mode_bar)
        self.top_layout.addWidget(self.script_mode_bar)
        self.node_mode_bar.setVisible(False)
        # self.top_layout.addSpacing(10)
        self.top_layout.addLayout(self.top_file_bar_layout)
        self.top_layout.addStretch()
        self.top_layout.addLayout(self.top_right_bar_layout)

        # ----------------------
        # 3. SCRIPTING SECTION
        # ----------------------
        # Splitter
        self.splitter = QtWidgets.QSplitter(Qt.Vertical)

        # Output widget
        self.script_output = ScriptOutputWidget(parent=self)
        self.script_output.setReadOnly(1)
        self.script_output.setAcceptRichText(0)
        self.script_output.setTabStopWidth(
            self.script_output.tabStopWidth() / 4)
        self.script_output.setFocusPolicy(Qt.ClickFocus)
        self.script_output.setAutoFillBackground(0)
        self.script_output.installEventFilter(self)

        # Script Editor
        self.script_editor = KnobScripterTextEditMain(self, self.script_output)
        self.script_editor.setMinimumHeight(30)
        self.script_editor.setStyleSheet(
            'background:#282828;color:#EEE;')  # Main Colors
        self.script_editor.textChanged.connect(self.setModified)
        self.highlighter = KSScriptEditorHighlighter(
            self.script_editor.document(), self)
        self.script_editor.cursorPositionChanged.connect(self.setTextSelection)
        self.script_editor_font = QtGui.QFont()
        self.script_editor_font.setFamily(self.font)
        self.script_editor_font.setStyleHint(QtGui.QFont.Monospace)
        self.script_editor_font.setFixedPitch(True)
        self.script_editor_font.setPointSize(self.fontSize)
        self.script_editor.setFont(self.script_editor_font)
        self.script_editor.setTabStopWidth(
            self.tabSpaces * QtGui.QFontMetrics(self.script_editor_font).width(' '))

        # Add input and output to splitter
        self.splitter.addWidget(self.script_output)
        self.splitter.addWidget(self.script_editor)
        self.splitter.setStretchFactor(0, 0)

        # FindReplace widget
        self.frw = FindReplaceWidget(self)
        self.frw.setVisible(self.frw_open)

        # ---
        # Layout
        self.scripting_layout = QtWidgets.QVBoxLayout()
        self.scripting_layout.setContentsMargins(0, 0, 0, 0)
        self.scripting_layout.setSpacing(0)
        self.scripting_layout.addWidget(self.splitter)
        self.scripting_layout.addWidget(self.frw)

        # ---------------
        # MASTER LAYOUT
        # ---------------
        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.setSpacing(5)
        self.master_layout.setContentsMargins(8, 8, 8, 8)
        self.master_layout.addLayout(self.top_layout)
        self.master_layout.addLayout(self.scripting_layout)
        # self.master_layout.addLayout(self.bottom_layout)
        self.setLayout(self.master_layout)

        # ----------------
        # MAIN WINDOW UI
        # ----------------
        size_policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.setSizePolicy(size_policy)
        self.setMinimumWidth(160)

        if self.pinned:
            self.setWindowFlags(self.windowFlags() |
                                QtCore.Qt.WindowStaysOnTopHint)

        # Set default values based on mode
        if self.nodeMode:
            self.current_knob_dropdown.blockSignals(True)
            self.node_mode_bar.setVisible(True)
            self.script_mode_bar.setVisible(False)
            self.setCurrentKnob(self.knob)
            self.loadKnobValue(check=False)
            self.setKnobModified(False)
            self.current_knob_dropdown.blockSignals(False)
            self.splitter.setSizes([0, 1])
        else:
            self.exitNodeMode()
        self.script_editor.setFocus()

    # Preferences submenus
    def createPrefsMenu(self):

        # Actions
        self.echoAct = QtWidgets.QAction("Echo python commands", self, checkable=True,
                                         statusTip="Toggle nuke's 'Echo all python commands to ScriptEditor'", triggered=self.toggleEcho)
        if nuke.toNode("preferences").knob("echoAllCommands").value():
            self.echoAct.toggle()
        self.pinAct = QtWidgets.QAction("Always on top", self, checkable=True,
                                        statusTip="Keeps the KnobScripter window always on top or not.", triggered=self.togglePin)
        if self.pinned:
            self.setWindowFlags(self.windowFlags() |
                                QtCore.Qt.WindowStaysOnTopHint)
            self.pinAct.toggle()
        self.helpAct = QtWidgets.QAction(
            "&Help", self, statusTip="Open the KnobScripter help in your browser.", shortcut="F1", triggered=self.showHelp)
        self.nukepediaAct = QtWidgets.QAction(
            "Show in Nukepedia", self, statusTip="Open the KnobScripter download page on Nukepedia.", triggered=self.showInNukepedia)
        self.githubAct = QtWidgets.QAction(
            "Show in GitHub", self, statusTip="Open the KnobScripter repo on GitHub.", triggered=self.showInGithub)
        self.snippetsAct = QtWidgets.QAction(
            "Snippets", self, statusTip="Open the Snippets editor.", triggered=self.openSnippets)
        self.snippetsAct.setIcon(QtGui.QIcon(icons_path + "icon_snippets.png"))
        # self.snippetsAct = QtWidgets.QAction("Keywords", self, statusTip="Add custom keywords.", triggered=self.openSnippets) #TODO THIS
        self.prefsAct = QtWidgets.QAction(
            "Preferences", self, statusTip="Open the Preferences panel.", triggered=self.openPrefs)
        self.prefsAct.setIcon(QtGui.QIcon(icons_path + "icon_prefs.png"))

        # Menus
        self.prefsMenu = QtWidgets.QMenu("Preferences")
        self.prefsMenu.addAction(self.echoAct)
        self.prefsMenu.addAction(self.pinAct)
        self.prefsMenu.addSeparator()
        self.prefsMenu.addAction(self.nukepediaAct)
        self.prefsMenu.addAction(self.githubAct)
        self.prefsMenu.addSeparator()
        self.prefsMenu.addAction(self.helpAct)
        self.prefsMenu.addSeparator()
        self.prefsMenu.addAction(self.snippetsAct)
        self.prefsMenu.addAction(self.prefsAct)

    def initEcho(self):
        ''' Initializes the echo chechable QAction based on nuke's state '''
        echo_knob = nuke.toNode("preferences").knob("echoAllCommands")
        self.echoAct.setChecked(echo_knob.value())

    def toggleEcho(self):
        ''' Toggle the "Echo python commands" from Nuke '''
        echo_knob = nuke.toNode("preferences").knob("echoAllCommands")
        echo_knob.setValue(self.echoAct.isChecked())

    def togglePin(self):
        ''' Toggle "always on top" based on the submenu button '''
        self.pin(self.pinAct.isChecked())

    def showInNukepedia(self):
        openUrl("http://www.nukepedia.com/python/ui/knobscripter")

    def showInGithub(self):
        openUrl("https://github.com/adrianpueyo/KnobScripter")

    def showHelp(self):
        openUrl("https://vimeo.com/adrianpueyo/knobscripter2")

    # Node Mode

    def updateKnobDropdown(self):
        ''' Populate knob dropdown list '''
        self.current_knob_dropdown.clear()  # First remove all items
        defaultKnobs = ["knobChanged", "onCreate", "onScriptLoad", "onScriptSave", "onScriptClose", "onDestroy",
                        "updateUI", "autolabel", "beforeRender", "beforeFrameRender", "afterFrameRender", "afterRender"]
        permittedKnobClasses = ["PyScript_Knob", "PythonCustomKnob"]
        counter = 0
        for i in self.node.knobs():
            if i not in defaultKnobs and self.node.knob(i).Class() in permittedKnobClasses:
                if self.show_labels:
                    i_full = "{} ({})".format(self.node.knob(i).label(), i)
                else:
                    i_full = i

                if i in self.unsavedKnobs.keys():
                    self.current_knob_dropdown.addItem(i_full + "(*)", i)
                else:
                    self.current_knob_dropdown.addItem(i_full, i)

                counter += 1
        if counter > 0:
            self.current_knob_dropdown.insertSeparator(counter)
            counter += 1
            self.current_knob_dropdown.insertSeparator(counter)
            counter += 1
        for i in self.node.knobs():
            if i in defaultKnobs:
                if i in self.unsavedKnobs.keys():
                    self.current_knob_dropdown.addItem(i + "(*)", i)
                else:
                    self.current_knob_dropdown.addItem(i, i)
                counter += 1
        return

    def loadKnobValue(self, check=True, updateDict=False):
        ''' Get the content of the knob value and populate the editor '''
        if self.toLoadKnob == False:
            return
        dropdown_value = self.current_knob_dropdown.itemData(
            self.current_knob_dropdown.currentIndex())  # knobChanged...
        try:
            obtained_knobValue = str(self.node[dropdown_value].value())
            obtained_scrollValue = 0
            edited_knobValue = self.script_editor.toPlainText()
        except:
            error_message = QtWidgets.QMessageBox.information(
                None, "", "Unable to find %s.%s" % (self.node.name(), dropdown_value))
            error_message.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            error_message.exec_()
            return
        # If there were changes to the previous knob, update the dictionary
        if updateDict == True:
            self.unsavedKnobs[self.knob] = edited_knobValue
            self.scrollPos[self.knob] = self.script_editor.verticalScrollBar(
            ).value()
        prev_knob = self.knob  # knobChanged...

        self.knob = self.current_knob_dropdown.itemData(
            self.current_knob_dropdown.currentIndex())  # knobChanged...

        if check and obtained_knobValue != edited_knobValue:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("The Script Editor has been modified.")
            msgBox.setInformativeText(
                "Do you want to overwrite the current code on this editor?")
            msgBox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                self.setCurrentKnob(prev_knob)
                return
        # If order comes from a dropdown update, update value from dictionary if possible, otherwise update normally
        self.setWindowTitle("KnobScripter - %s %s" %
                            (self.node.name(), self.knob))
        if updateDict:
            if self.knob in self.unsavedKnobs:
                if self.unsavedKnobs[self.knob] == obtained_knobValue:
                    self.script_editor.setPlainText(obtained_knobValue)
                    self.setKnobModified(False)
                else:
                    obtained_knobValue = self.unsavedKnobs[self.knob]
                    self.script_editor.setPlainText(obtained_knobValue)
                    self.setKnobModified(True)
            else:
                self.script_editor.setPlainText(obtained_knobValue)
                self.setKnobModified(False)

            if self.knob in self.scrollPos:
                obtained_scrollValue = self.scrollPos[self.knob]
        else:
            self.script_editor.setPlainText(obtained_knobValue)

        cursor = self.script_editor.textCursor()
        self.script_editor.setTextCursor(cursor)
        self.script_editor.verticalScrollBar().setValue(obtained_scrollValue)
        return

    def loadAllKnobValues(self):
        ''' Load all knobs button's function '''
        if len(self.unsavedKnobs) >= 1:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText(
                "Do you want to reload all python and callback knobs?")
            msgBox.setInformativeText(
                "Unsaved changes on this editor will be lost.")
            msgBox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return
        self.unsavedKnobs = {}
        return

    def saveKnobValue(self, check=True):
        ''' Save the text from the editor to the node's knobChanged knob '''
        dropdown_value = self.current_knob_dropdown.itemData(
            self.current_knob_dropdown.currentIndex())
        try:
            obtained_knobValue = str(self.node[dropdown_value].value())
            self.knob = dropdown_value
        except:
            error_message = QtWidgets.QMessageBox.information(
                None, "", "Unable to find %s.%s" % (self.node.name(), dropdown_value))
            error_message.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            error_message.exec_()
            return
        edited_knobValue = self.script_editor.toPlainText()
        if check and obtained_knobValue != edited_knobValue:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Do you want to overwrite %s.%s?" %
                           (self.node.name(), dropdown_value))
            msgBox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return
        self.node[dropdown_value].setValue(edited_knobValue)
        self.setKnobModified(
            modified=False, knob=dropdown_value, changeTitle=True)
        nuke.tcl("modified 1")
        if self.knob in self.unsavedKnobs:
            del self.unsavedKnobs[self.knob]
        return

    def saveAllKnobValues(self, check=True):
        ''' Save all knobs button's function '''
        if self.updateUnsavedKnobs() > 0 and check:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText(
                "Do you want to save all modified python and callback knobs?")
            msgBox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return
        saveErrors = 0
        savedCount = 0
        for k in self.unsavedKnobs.copy():
            try:
                self.node.knob(k).setValue(self.unsavedKnobs[k])
                del self.unsavedKnobs[k]
                savedCount += 1
                nuke.tcl("modified 1")
            except:
                saveErrors += 1
        if saveErrors > 0:
            errorBox = QtWidgets.QMessageBox()
            errorBox.setText("Error saving %s knob%s." %
                             (str(saveErrors), int(saveErrors > 1) * "s"))
            errorBox.setIcon(QtWidgets.QMessageBox.Warning)
            errorBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            errorBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = errorBox.exec_()
        else:
            log("KnobScripter: %s knobs saved" % str(savedCount))
        return

    def setCurrentKnob(self, knobToSet):
        ''' Set current knob '''
        KnobDropdownItems = []
        for i in range(self.current_knob_dropdown.count()):
            if self.current_knob_dropdown.itemData(i) is not None:
                KnobDropdownItems.append(
                    self.current_knob_dropdown.itemData(i))
            else:
                KnobDropdownItems.append("---")
        if knobToSet in KnobDropdownItems:
            index = KnobDropdownItems.index(knobToSet)
            self.current_knob_dropdown.setCurrentIndex(index)
        return

    def updateUnsavedKnobs(self, first_time=False):
        ''' Clear unchanged knobs from the dict and return the number of unsaved knobs '''
        if not self.node:
            # Node has been deleted, so simply return 0. Who cares.
            return 0
        edited_knobValue = self.script_editor.toPlainText()
        self.unsavedKnobs[self.knob] = edited_knobValue
        if len(self.unsavedKnobs) > 0:
            for k in self.unsavedKnobs.copy():
                if self.node.knob(k):
                    if str(self.node.knob(k).value()) == str(self.unsavedKnobs[k]):
                        del self.unsavedKnobs[k]
                else:
                    del self.unsavedKnobs[k]
        # Set appropriate knobs modified...
        knobs_dropdown = self.current_knob_dropdown
        all_knobs = [knobs_dropdown.itemData(i)
                     for i in range(knobs_dropdown.count())]
        for key in all_knobs:
            if key in self.unsavedKnobs.keys():
                self.setKnobModified(
                    modified=True, knob=key, changeTitle=False)
            else:
                self.setKnobModified(
                    modified=False, knob=key, changeTitle=False)

        return len(self.unsavedKnobs)

    def setKnobModified(self, modified=True, knob="", changeTitle=True):
        ''' Sets the current knob modified, title and whatever else we need '''
        if knob == "":
            knob = self.knob
        if modified:
            self.modifiedKnobs.add(knob)
        else:
            self.modifiedKnobs.discard(knob)

        if changeTitle:
            title_modified_string = " [modified]"
            windowTitle = self.windowTitle().split(title_modified_string)[0]
            if modified == True:
                windowTitle += title_modified_string
            self.setWindowTitle(windowTitle)

        try:
            knobs_dropdown = self.current_knob_dropdown
            kd_index = knobs_dropdown.currentIndex()
            kd_data = knobs_dropdown.itemData(kd_index)
            if self.show_labels and i not in defaultKnobs:
                kd_data = "{} ({})".format(
                    self.node.knob(kd_data).label(), kd_data)
            if modified == False:
                knobs_dropdown.setItemText(kd_index, kd_data)
            else:
                knobs_dropdown.setItemText(kd_index, kd_data + "(*)")
        except:
            pass

    # Script Mode
    def updateFoldersDropdown(self):
        ''' Populate folders dropdown list '''
        self.current_folder_dropdown.blockSignals(True)
        self.current_folder_dropdown.clear()  # First remove all items
        defaultFolders = ["scripts"]
        scriptFolders = []
        counter = 0
        for f in defaultFolders:
            self.makeScriptFolder(f)
            self.current_folder_dropdown.addItem(f + "/", f)
            counter += 1

        try:
            scriptFolders = sorted([f for f in os.listdir(self.scripts_dir) if os.path.isdir(
                os.path.join(self.scripts_dir, f))])  # Accepts symlinks!!!
        except:
            log("Couldn't read any script folders.")

        for f in scriptFolders:
            fname = f.split("/")[-1]
            if fname in defaultFolders:
                continue
            self.current_folder_dropdown.addItem(fname + "/", fname)
            counter += 1

        # print scriptFolders
        if counter > 0:
            self.current_folder_dropdown.insertSeparator(counter)
            counter += 1
            # self.current_folder_dropdown.insertSeparator(counter)
            #counter += 1
        self.current_folder_dropdown.addItem("New", "create new")
        self.current_folder_dropdown.addItem("Open...", "open in browser")
        self.current_folder_dropdown.addItem("Add custom", "add custom path")
        self.folder_index = self.current_folder_dropdown.currentIndex()
        self.current_folder = self.current_folder_dropdown.itemData(
            self.folder_index)
        self.current_folder_dropdown.blockSignals(False)
        return

    def updateScriptsDropdown(self):
        ''' Populate py scripts dropdown list '''
        self.current_script_dropdown.blockSignals(True)
        self.current_script_dropdown.clear()  # First remove all items
        QtWidgets.QApplication.processEvents()
        log("# Updating scripts dropdown...")
        log("scripts dir:" + self.scripts_dir)
        log("current folder:" + self.current_folder)
        log("previous current script:" + self.current_script)
        #current_folder = self.current_folder_dropdown.itemData(self.current_folder_dropdown.currentIndex())
        current_folder_path = os.path.join(
            self.scripts_dir, self.current_folder)
        defaultScripts = ["Untitled.py"]
        found_scripts = []
        counter = 0
        # All files and folders inside of the folder
        dir_list = os.listdir(current_folder_path)
        try:
            found_scripts = sorted([f for f in dir_list if f.endswith(".py")])
            found_temp_scripts = [
                f for f in dir_list if f.endswith(".py.autosave")]
        except:
            log("Couldn't find any scripts in the selected folder.")
        if not len(found_scripts):
            for s in defaultScripts:
                if s + ".autosave" in found_temp_scripts:
                    self.current_script_dropdown.addItem(s + "(*)", s)
                else:
                    self.current_script_dropdown.addItem(s, s)
                counter += 1
        else:
            for s in defaultScripts:
                if s + ".autosave" in found_temp_scripts:
                    self.current_script_dropdown.addItem(s + "(*)", s)
                elif s in found_scripts:
                    self.current_script_dropdown.addItem(s, s)
            for s in found_scripts:
                if s in defaultScripts:
                    continue
                sname = s.split("/")[-1]
                if s + ".autosave" in found_temp_scripts:
                    self.current_script_dropdown.addItem(sname + "(*)", sname)
                else:
                    self.current_script_dropdown.addItem(sname, sname)
                counter += 1
        # else: #Add the found scripts to the dropdown
        if counter > 0:
            counter += 1
            self.current_script_dropdown.insertSeparator(counter)
            counter += 1
            self.current_script_dropdown.insertSeparator(counter)
        self.current_script_dropdown.addItem("New", "create new")
        self.current_script_dropdown.addItem("Duplicate", "create duplicate")
        self.current_script_dropdown.addItem("Delete", "delete script")
        self.current_script_dropdown.addItem("Open", "open in browser")
        #self.script_index = self.current_script_dropdown.currentIndex()
        self.script_index = 0
        self.current_script = self.current_script_dropdown.itemData(
            self.script_index)
        log("Finished updating scripts dropdown.")
        log("current_script:" + self.current_script)
        self.current_script_dropdown.blockSignals(False)
        return

    def makeScriptFolder(self, name="scripts"):
        folder_path = os.path.join(self.scripts_dir, name)
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                return True
            except:
                print "Couldn't create the scripting folders.\nPlease check your OS write permissions."
                return False

    def makeScriptFile(self, name="Untitled.py", folder="scripts", empty=True):
        script_path = os.path.join(self.scripts_dir, self.current_folder, name)
        if not os.path.isfile(script_path):
            try:
                self.current_script_file = open(script_path, 'w')
                return True
            except:
                print "Couldn't create the scripting folders.\nPlease check your OS write permissions."
                return False

    def setCurrentFolder(self, folderName):
        ''' Set current folder ON THE DROPDOWN ONLY'''
        folderList = [self.current_folder_dropdown.itemData(
            i) for i in range(self.current_folder_dropdown.count())]
        if folderName in folderList:
            index = folderList.index(folderName)
            self.current_folder_dropdown.setCurrentIndex(index)
            self.current_folder = folderName
        self.folder_index = self.current_folder_dropdown.currentIndex()
        self.current_folder = self.current_folder_dropdown.itemData(
            self.folder_index)
        return

    def setCurrentScript(self, scriptName):
        ''' Set current script ON THE DROPDOWN ONLY '''
        scriptList = [self.current_script_dropdown.itemData(
            i) for i in range(self.current_script_dropdown.count())]
        if scriptName in scriptList:
            index = scriptList.index(scriptName)
            self.current_script_dropdown.setCurrentIndex(index)
            self.current_script = scriptName
        self.script_index = self.current_script_dropdown.currentIndex()
        self.current_script = self.current_script_dropdown.itemData(
            self.script_index)
        return

    def loadScriptContents(self, check=False, pyOnly=False, folder=""):
        ''' Get the contents of the selected script and populate the editor '''
        log("# About to load script contents now.")
        obtained_scrollValue = 0
        obtained_cursorPosValue = [0, 0]  # Position, anchor
        if folder == "":
            folder = self.current_folder
        script_path = os.path.join(
            self.scripts_dir, folder, self.current_script)
        script_path_temp = script_path + ".autosave"
        if (self.current_folder + "/" + self.current_script) in self.scrollPos:
            obtained_scrollValue = self.scrollPos[self.current_folder +
                                                  "/" + self.current_script]
        if (self.current_folder + "/" + self.current_script) in self.cursorPos:
            obtained_cursorPosValue = self.cursorPos[self.current_folder +
                                                     "/" + self.current_script]

        # 1: If autosave exists and pyOnly is false, load it
        if os.path.isfile(script_path_temp) and not pyOnly:
            log("Loading .py.autosave file\n---")
            with open(script_path_temp, 'r') as script:
                content = script.read()
            self.script_editor.setPlainText(content)
            self.setScriptModified(True)
            self.script_editor.verticalScrollBar().setValue(obtained_scrollValue)

        # 2: Try to load the .py as first priority, if it exists
        elif os.path.isfile(script_path):
            log("Loading .py file\n---")
            with open(script_path, 'r') as script:
                content = script.read()
            current_text = self.script_editor.toPlainText().encode("utf8")
            if check and current_text != content and current_text.strip() != "":
                msgBox = QtWidgets.QMessageBox()
                msgBox.setText("The script has been modified.")
                msgBox.setInformativeText(
                    "Do you want to overwrite the current code on this editor?")
                msgBox.setStandardButtons(
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                msgBox.setIcon(QtWidgets.QMessageBox.Question)
                msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
                msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
                reply = msgBox.exec_()
                if reply == QtWidgets.QMessageBox.No:
                    return
            # Clear trash
            if os.path.isfile(script_path_temp):
                os.remove(script_path_temp)
                log("Removed " + script_path_temp)
            self.setScriptModified(False)
            self.script_editor.setPlainText(content)
            self.script_editor.verticalScrollBar().setValue(obtained_scrollValue)
            self.setScriptModified(False)
            self.loadScriptState()
            self.setScriptState()

        # 3: If .py doesn't exist... only then stick to the autosave
        elif os.path.isfile(script_path_temp):
            with open(script_path_temp, 'r') as script:
                content = script.read()

            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("The .py file hasn't been found.")
            msgBox.setInformativeText(
                "Do you want to clear the current code on this editor?")
            msgBox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return

            # Clear trash
            os.remove(script_path_temp)
            log("Removed " + script_path_temp)
            self.script_editor.setPlainText("")
            self.updateScriptsDropdown()
            self.loadScriptContents(check=False)
            self.loadScriptState()
            self.setScriptState()

        else:
            content = ""
            self.script_editor.setPlainText(content)
            self.setScriptModified(False)
            if self.current_folder + "/" + self.current_script in self.scrollPos:
                del self.scrollPos[self.current_folder +
                                   "/" + self.current_script]
            if self.current_folder + "/" + self.current_script in self.cursorPos:
                del self.cursorPos[self.current_folder +
                                   "/" + self.current_script]

        self.setWindowTitle("KnobScripter - %s/%s" %
                            (self.current_folder, self.current_script))
        return

    def saveScriptContents(self, temp=True):
        ''' Save the current contents of the editor into the python file. If temp == True, saves a .py.autosave file '''
        log("\n# About to save script contents now.")
        log("Temp mode is: " + str(temp))
        log("self.current_folder: " + self.current_folder)
        log("self.current_script: " + self.current_script)
        script_path = os.path.join(
            self.scripts_dir, self.current_folder, self.current_script)
        script_path_temp = script_path + ".autosave"
        orig_content = ""
        content = self.script_editor.toPlainText().encode('utf8')

        if temp == True:
            if os.path.isfile(script_path):
                with open(script_path, 'r') as script:
                    orig_content = script.read()
            # If script path doesn't exist and autosave does but the script is empty...
            elif content == "" and os.path.isfile(script_path_temp):
                os.remove(script_path_temp)
                return
            if content != orig_content:
                with open(script_path_temp, 'w') as script:
                    script.write(content)
            else:
                if os.path.isfile(script_path_temp):
                    os.remove(script_path_temp)
                log("Nothing to save")
                return
        else:
            with open(script_path, 'w') as script:
                script.write(self.script_editor.toPlainText().encode('utf8'))
            # Clear trash
            if os.path.isfile(script_path_temp):
                os.remove(script_path_temp)
                log("Removed " + script_path_temp)
            self.setScriptModified(False)
        self.saveScrollValue()
        self.saveCursorPosValue()
        log("Saved " + script_path + "\n---")
        return

    def deleteScript(self, check=True, folder=""):
        ''' Get the contents of the selected script and populate the editor '''
        log("# About to delete the .py and/or autosave script now.")
        if folder == "":
            folder = self.current_folder
        script_path = os.path.join(
            self.scripts_dir, folder, self.current_script)
        script_path_temp = script_path + ".autosave"
        if check:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("You're about to delete this script.")
            msgBox.setInformativeText(
                "Are you sure you want to delete {}?".format(self.current_script))
            msgBox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            msgBox.setIcon(QtWidgets.QMessageBox.Question)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.No)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.No:
                return False

        if os.path.isfile(script_path_temp):
            os.remove(script_path_temp)
            log("Removed " + script_path_temp)

        if os.path.isfile(script_path):
            os.remove(script_path)
            log("Removed " + script_path)

        return True

    def folderDropdownChanged(self):
        '''Executed when the current folder dropdown is changed'''
        self.saveScriptState()
        log("# folder dropdown changed")
        folders_dropdown = self.current_folder_dropdown
        fd_value = folders_dropdown.currentText()
        fd_index = folders_dropdown.currentIndex()
        fd_data = folders_dropdown.itemData(fd_index)
        if fd_data == "create new":
            panel = FileNameDialog(self, mode="folder")
            # panel.setWidth(260)
            # panel.addSingleLineInput("Name:","")
            if panel.exec_():
                # Accepted
                folder_name = panel.text
                if os.path.isdir(os.path.join(self.scripts_dir, folder_name)):
                    self.messageBox("Folder already exists.")
                    self.setCurrentFolder(self.current_folder)
                if self.makeScriptFolder(name=folder_name):
                    self.saveScriptContents(temp=True)
                    # Success creating the folder
                    self.current_folder = folder_name
                    self.updateFoldersDropdown()
                    self.setCurrentFolder(folder_name)
                    self.updateScriptsDropdown()
                    self.loadScriptContents(check=False)
                else:
                    self.messageBox("There was a problem creating the folder.")
                    self.current_folder_dropdown.blockSignals(True)
                    self.current_folder_dropdown.setCurrentIndex(
                        self.folder_index)
                    self.current_folder_dropdown.blockSignals(False)
            else:
                # Canceled/rejected
                self.current_folder_dropdown.blockSignals(True)
                self.current_folder_dropdown.setCurrentIndex(self.folder_index)
                self.current_folder_dropdown.blockSignals(False)
                return

        elif fd_data == "open in browser":
            current_folder_path = os.path.join(
                self.scripts_dir, self.current_folder)
            self.openInFileBrowser(current_folder_path)
            self.current_folder_dropdown.blockSignals(True)
            self.current_folder_dropdown.setCurrentIndex(self.folder_index)
            self.current_folder_dropdown.blockSignals(False)
            return

        elif fd_data == "add custom path":
            folder_path = nuke.getFilename('Select custom folder.')
            if folder_path is not None:
                if folder_path.endswith("/"):
                    aliasName = folder_path.split("/")[-2]
                else:
                    aliasName = folder_path.split("/")[-1]
                if not os.path.isdir(folder_path):
                    self.messageBox(
                        "Folder not found. Please try again with the full path to a folder.")
                elif not len(aliasName):
                    self.messageBox(
                        "Folder with the same name already exists. Please delete or rename it first.")
                else:
                    # All good
                    os.symlink(folder_path, os.path.join(
                        self.scripts_dir, aliasName))
                    self.saveScriptContents(temp=True)
                    self.current_folder = aliasName
                    self.updateFoldersDropdown()
                    self.setCurrentFolder(aliasName)
                    self.updateScriptsDropdown()
                    self.loadScriptContents(check=False)
                    self.script_editor.setFocus()
                    return
            self.current_folder_dropdown.blockSignals(True)
            self.current_folder_dropdown.setCurrentIndex(self.folder_index)
            self.current_folder_dropdown.blockSignals(False)
        else:
            # 1: Save current script as temp if needed
            self.saveScriptContents(temp=True)
            # 2: Set the new folder in the variables
            self.current_folder = fd_data
            self.folder_index = fd_index
            # 3: Update the scripts dropdown
            self.updateScriptsDropdown()
            # 4: Load the current script!
            self.loadScriptContents()
            self.script_editor.setFocus()

            self.loadScriptState()
            self.setScriptState()

        return

    def scriptDropdownChanged(self):
        '''Executed when the current script dropdown is changed. Should only be called by the manual dropdown change. Not by other functions.'''
        self.saveScriptState()
        scripts_dropdown = self.current_script_dropdown
        sd_value = scripts_dropdown.currentText()
        sd_index = scripts_dropdown.currentIndex()
        sd_data = scripts_dropdown.itemData(sd_index)
        if sd_data == "create new":
            self.current_script_dropdown.blockSignals(True)
            panel = FileNameDialog(self, mode="script")
            if panel.exec_():
                # Accepted
                script_name = panel.text + ".py"
                script_path = os.path.join(
                    self.scripts_dir, self.current_folder, script_name)
                log(script_name)
                log(script_path)
                if os.path.isfile(script_path):
                    self.messageBox("Script already exists.")
                    self.current_script_dropdown.setCurrentIndex(
                        self.script_index)
                if self.makeScriptFile(name=script_name, folder=self.current_folder):
                    # Success creating the folder
                    self.saveScriptContents(temp=True)
                    self.updateScriptsDropdown()
                    if self.current_script != "Untitled.py":
                        self.script_editor.setPlainText("")
                    self.current_script = script_name
                    self.setCurrentScript(script_name)
                    self.saveScriptContents(temp=False)
                    # self.loadScriptContents()
                else:
                    self.messageBox("There was a problem creating the script.")
                    self.current_script_dropdown.setCurrentIndex(
                        self.script_index)
            else:
                # Canceled/rejected
                self.current_script_dropdown.setCurrentIndex(self.script_index)
                return
            self.current_script_dropdown.blockSignals(False)

        elif sd_data == "create duplicate":
            self.current_script_dropdown.blockSignals(True)
            current_folder_path = os.path.join(
                self.scripts_dir, self.current_folder, self.current_script)
            current_script_path = os.path.join(
                self.scripts_dir, self.current_folder, self.current_script)

            current_name = self.current_script
            if self.current_script.endswith(".py"):
                current_name = current_name[:-3]

            test_name = current_name
            while True:
                test_name += "_copy"
                new_script_path = os.path.join(
                    self.scripts_dir, self.current_folder, test_name + ".py")
                if not os.path.isfile(new_script_path):
                    break

            script_name = test_name + ".py"

            if self.makeScriptFile(name=script_name, folder=self.current_folder):
                # Success creating the folder
                self.saveScriptContents(temp=True)
                self.updateScriptsDropdown()
                # self.script_editor.setPlainText("")
                self.current_script = script_name
                self.setCurrentScript(script_name)
                self.script_editor.setFocus()
            else:
                self.messageBox("There was a problem duplicating the script.")
                self.current_script_dropdown.setCurrentIndex(self.script_index)

            self.current_script_dropdown.blockSignals(False)

        elif sd_data == "open in browser":
            current_script_path = os.path.join(
                self.scripts_dir, self.current_folder, self.current_script)
            self.openInFileBrowser(current_script_path)
            self.current_script_dropdown.blockSignals(True)
            self.current_script_dropdown.setCurrentIndex(self.script_index)
            self.current_script_dropdown.blockSignals(False)
            return

        elif sd_data == "delete script":
            if self.deleteScript():
                self.updateScriptsDropdown()
                self.loadScriptContents()
            else:
                self.current_script_dropdown.blockSignals(True)
                self.current_script_dropdown.setCurrentIndex(self.script_index)
                self.current_script_dropdown.blockSignals(False)

        else:
            self.saveScriptContents()
            self.current_script = sd_data
            self.script_index = sd_index
            self.setCurrentScript(self.current_script)
            self.loadScriptContents()
            self.script_editor.setFocus()
            self.loadScriptState()
            self.setScriptState()
        return

    def setScriptModified(self, modified=True):
        ''' Sets self.current_script_modified, title and whatever else we need '''
        self.current_script_modified = modified
        title_modified_string = " [modified]"
        windowTitle = self.windowTitle().split(title_modified_string)[0]
        if modified == True:
            windowTitle += title_modified_string
        self.setWindowTitle(windowTitle)
        try:
            scripts_dropdown = self.current_script_dropdown
            sd_index = scripts_dropdown.currentIndex()
            sd_data = scripts_dropdown.itemData(sd_index)
            if modified == False:
                scripts_dropdown.setItemText(sd_index, sd_data)
            else:
                scripts_dropdown.setItemText(sd_index, sd_data + "(*)")
        except:
            pass

    def openInFileBrowser(self, path=""):
        OS = platform.system()
        if not os.path.exists(path):
            path = KS_DIR
        if OS == "Windows":
            os.startfile(path)
        elif OS == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def loadScriptState(self):
        '''
        Loads the last state of the script from a file inside the SE directory's root.
        SAVES self.scroll_pos, self.cursor_pos, self.last_open_script
        '''
        self.state_dict = {}
        if not os.path.isfile(self.state_txt_path):
            return False
        else:
            with open(self.state_txt_path, "r") as f:
                self.state_dict = json.load(f)

        log("Loading script state into self.state_dict, self.scrollPos, self.cursorPos")
        log(self.state_dict)

        if "scroll_pos" in self.state_dict:
            self.scrollPos = self.state_dict["scroll_pos"]
        if "cursor_pos" in self.state_dict:
            self.cursorPos = self.state_dict["cursor_pos"]

    def setScriptState(self):
        '''
        Sets the already script state from self.state_dict into the current script if applicable
        '''
        script_fullname = self.current_folder + "/" + self.current_script

        if "scroll_pos" in self.state_dict:
            if script_fullname in self.state_dict["scroll_pos"]:
                self.script_editor.verticalScrollBar().setValue(
                    int(self.state_dict["scroll_pos"][script_fullname]))

        if "cursor_pos" in self.state_dict:
            if script_fullname in self.state_dict["cursor_pos"]:
                cursor = self.script_editor.textCursor()
                cursor.setPosition(int(
                    self.state_dict["cursor_pos"][script_fullname][1]), QtGui.QTextCursor.MoveAnchor)
                cursor.setPosition(int(
                    self.state_dict["cursor_pos"][script_fullname][0]), QtGui.QTextCursor.KeepAnchor)
                self.script_editor.setTextCursor(cursor)

        if 'splitter_sizes' in self.state_dict:
            self.splitter.setSizes(self.state_dict['splitter_sizes'])

    def setLastScript(self):
        if 'last_folder' in self.state_dict and 'last_script' in self.state_dict:
            self.updateFoldersDropdown()
            self.setCurrentFolder(self.state_dict['last_folder'])
            self.updateScriptsDropdown()
            self.setCurrentScript(self.state_dict['last_script'])
            self.loadScriptContents()
            self.script_editor.setFocus()

    def saveScriptState(self):
        ''' Stores the current state of the script into a file inside the SE directory's root '''
        log("About to save script state...")
        '''
        # self.state_dict = {}
        if os.path.isfile(self.state_txt_path):
            with open(self.state_txt_path, "r") as f:
                self.state_dict = json.load(f)

        if "scroll_pos" in self.state_dict:
            self.scrollPos = self.state_dict["scroll_pos"]
        if "cursor_pos" in self.state_dict:
            self.cursorPos = self.state_dict["cursor_pos"]

        '''
        self.loadScriptState()

        # Overwrite current values into the scriptState
        self.saveScrollValue()
        self.saveCursorPosValue()

        self.state_dict['scroll_pos'] = self.scrollPos
        self.state_dict['cursor_pos'] = self.cursorPos
        self.state_dict['last_folder'] = self.current_folder
        self.state_dict['last_script'] = self.current_script
        self.state_dict['splitter_sizes'] = self.splitter.sizes()

        with open(self.state_txt_path, "w") as f:
            state = json.dump(self.state_dict, f, sort_keys=True, indent=4)
        return state

    # Autosave background loop
    def autosave(self):
        if self.toAutosave:
            # Save the script...
            self.saveScriptContents()
            self.toAutosave = False
            self.saveScriptState()
            log("autosaving...")
            return

    # Global stuff
    def setTextSelection(self):
        self.highlighter.selected_text = self.script_editor.textCursor().selection().toPlainText()
        return

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.KeyPress:
            return QtWidgets.QWidget.eventFilter(self, object, event)
        else:
            return QtWidgets.QWidget.eventFilter(self, object, event)

    def resizeEvent(self, res_event):
        w = self.frameGeometry().width()
        self.current_node_label_node.setVisible(w > 460)
        self.script_label.setVisible(w > 460)
        return super(KnobScripter, self).resizeEvent(res_event)

    def changeClicked(self, newNode=""):
        ''' Change node '''
        try:
            print "Changing from " + self.node.name()
        except:
            self.node = None
            if not len(nuke.selectedNodes()):
                self.exitNodeMode()
                return
        nuke.menu("Nuke").findItem(
            "Edit/Node/Update KnobScripter Context").invoke()
        selection = knobScripterSelectedNodes
        if self.nodeMode:  # Only update the number of unsaved knobs if we were already in node mode
            if self.node is not None:
                updatedCount = self.updateUnsavedKnobs()
            else:
                updatedCount = 0
        else:
            updatedCount = 0
            self.autosave()
        if newNode != "" and nuke.exists(newNode):
            selection = [newNode]
        elif not len(selection):
            node_dialog = ChooseNodeDialog(self)
            if node_dialog.exec_():
                # Accepted
                selection = [nuke.toNode(node_dialog.name)]
            else:
                return

        # Change to node mode...
        self.node_mode_bar.setVisible(True)
        self.script_mode_bar.setVisible(False)
        if not self.nodeMode:
            self.saveScriptContents()
            self.toAutosave = False
            self.saveScriptState()
            self.splitter.setSizes([0, 1])
        self.nodeMode = True

        # If already selected, pass
        if self.node is not None and selection[0].fullName() == self.node.fullName():
            self.messageBox("Please select a different node first!")
            return
        elif updatedCount > 0:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText(
                "Save changes to %s knob%s before changing the node?" % (str(updatedCount), int(updatedCount > 1) * "s"))
            msgBox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
            msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            reply = msgBox.exec_()
            if reply == QtWidgets.QMessageBox.Yes:
                self.saveAllKnobValues(check=False)
            elif reply == QtWidgets.QMessageBox.Cancel:
                return
        if len(selection) > 1:
            self.messageBox(
                "More than one node selected.\nChanging knobChanged editor to %s" % selection[0].fullName())
        # Reinitialise everything, wooo!
        self.current_knob_dropdown.blockSignals(True)
        self.node = selection[0]

        self.script_editor.setPlainText("")
        self.unsavedKnobs = {}
        self.scrollPos = {}
        self.setWindowTitle("KnobScripter - %s %s" %
                            (self.node.fullName(), self.knob))
        self.current_node_label_name.setText(self.node.fullName())

        self.toLoadKnob = False
        self.updateKnobDropdown()  # onee
        # self.current_knob_dropdown.repaint()
        # self.current_knob_dropdown.setMinimumWidth(self.current_knob_dropdown.minimumSizeHint().width())
        self.toLoadKnob = True
        self.setCurrentKnob(self.knob)
        self.loadKnobValue(False)
        self.script_editor.setFocus()
        self.setKnobModified(False)
        self.current_knob_dropdown.blockSignals(False)
        # self.current_knob_dropdown.setMinimumContentsLength(80)
        return

    def exitNodeMode(self):
        self.nodeMode = False
        self.setWindowTitle("KnobScripter - Script Mode")
        self.node_mode_bar.setVisible(False)
        self.script_mode_bar.setVisible(True)
        self.node = nuke.toNode("root")
        # self.updateFoldersDropdown()
        # self.updateScriptsDropdown()
        self.splitter.setSizes([1, 1])
        self.loadScriptState()
        self.setLastScript()

        self.loadScriptContents(check=False)
        self.setScriptState()

    def clearConsole(self):
        self.origConsoleText = self.nukeSEOutput.document().toPlainText().encode("utf8")
        self.script_output.setPlainText("")

    def toggleFRW(self, frw_pressed):
        self.frw_open = frw_pressed
        self.frw.setVisible(self.frw_open)
        if self.frw_open:
            self.frw.find_lineEdit.setFocus()
            self.frw.find_lineEdit.selectAll()
        else:
            self.script_editor.setFocus()
        return

    def openSnippets(self):
        ''' Whenever the 'snippets' button is pressed... open the panel '''
        global SnippetEditPanel
        if SnippetEditPanel == "":
            SnippetEditPanel = SnippetsPanel(self)

        if not SnippetEditPanel.isVisible():
            SnippetEditPanel.reload()

        if SnippetEditPanel.show():
            self.snippets = self.loadSnippets(maxDepth=5)
            SnippetEditPanel = ""

    def loadSnippets(self, path="", maxDepth=5, depth=0):
        '''
        Load prefs recursive. When maximum recursion depth, ignores paths.
        '''
        max_depth = maxDepth
        cur_depth = depth
        if path == "":
            path = self.snippets_txt_path
        if not os.path.isfile(path):
            return {}
        else:
            loaded_snippets = {}
            with open(path, "r") as f:
                file = json.load(f)
                for i, (key, val) in enumerate(file.items()):
                    if re.match(r"\[custom-path-[0-9]+\]$", key):
                        if cur_depth < max_depth:
                            new_dict = self.loadSnippets(
                                path=val, maxDepth=max_depth, depth=cur_depth + 1)
                            loaded_snippets.update(new_dict)
                    else:
                        loaded_snippets[key] = val
                return loaded_snippets

    def messageBox(self, the_text=""):
        ''' Just a simple message box '''
        if self.isPane:
            msgBox = QtWidgets.QMessageBox()
        else:
            msgBox = QtWidgets.QMessageBox(self)
        msgBox.setText(the_text)
        msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        msgBox.exec_()

    def openPrefs(self):
        ''' Open the preferences panel '''
        global PrefsPanel
        if PrefsPanel == "":
            PrefsPanel = KnobScripterPrefs(self)

        if PrefsPanel.show():
            PrefsPanel = ""

    def loadPrefs(self):
        ''' Load prefs '''
        if not os.path.isfile(self.prefs_txt):
            return []
        else:
            with open(self.prefs_txt, "r") as f:
                prefs = json.load(f)
                return prefs

    def runScript(self):
        ''' Run the current script... '''
        self.script_editor.runScript()

    def saveScrollValue(self):
        ''' Save scroll values '''
        if self.nodeMode:
            self.scrollPos[self.knob] = self.script_editor.verticalScrollBar(
            ).value()
        else:
            self.scrollPos[self.current_folder + "/" +
                           self.current_script] = self.script_editor.verticalScrollBar().value()

    def saveCursorPosValue(self):
        ''' Save cursor pos and anchor values '''
        self.cursorPos[self.current_folder + "/" + self.current_script] = [
            self.script_editor.textCursor().position(), self.script_editor.textCursor().anchor()]

    def closeEvent(self, close_event):
        if self.nodeMode:
            updatedCount = self.updateUnsavedKnobs()
            if updatedCount > 0:
                msgBox = QtWidgets.QMessageBox()
                msgBox.setText("Save changes to %s knob%s before closing?" % (
                    str(updatedCount), int(updatedCount > 1) * "s"))
                msgBox.setStandardButtons(
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
                msgBox.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
                msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
                reply = msgBox.exec_()
                if reply == QtWidgets.QMessageBox.Yes:
                    self.saveAllKnobValues(check=False)
                    close_event.accept()
                    return
                elif reply == QtWidgets.QMessageBox.Cancel:
                    close_event.ignore()
                    return
            else:
                close_event.accept()
        else:
            self.autosave()
            if self in AllKnobScripters:
                AllKnobScripters.remove(self)
            close_event.accept()

    # Landing functions

    def refreshClicked(self):
        ''' Function to refresh the dropdowns '''
        if self.nodeMode:
            knob = self.current_knob_dropdown.itemData(
                self.current_knob_dropdown.currentIndex()).encode('UTF8')
            self.current_knob_dropdown.blockSignals(True)
            self.current_knob_dropdown.clear()  # First remove all items
            self.updateKnobDropdown()
            availableKnobs = []
            for i in range(self.current_knob_dropdown.count()):
                if self.current_knob_dropdown.itemData(i) is not None:
                    availableKnobs.append(
                        self.current_knob_dropdown.itemData(i).encode('UTF8'))
            if knob in availableKnobs:
                self.setCurrentKnob(knob)
            self.current_knob_dropdown.blockSignals(False)
        else:
            folder = self.current_folder
            script = self.current_script
            self.autosave()
            self.updateFoldersDropdown()
            self.setCurrentFolder(folder)
            self.updateScriptsDropdown()
            self.setCurrentScript(script)
            self.script_editor.setFocus()

    def reloadClicked(self):
        if self.nodeMode:
            self.loadKnobValue()
        else:
            log("Node mode is off")
            self.loadScriptContents(check=True, pyOnly=True)

    def saveClicked(self):
        if self.nodeMode:
            self.saveKnobValue(False)
        else:
            self.saveScriptContents(temp=False)

    def setModified(self):
        if self.nodeMode:
            self.setKnobModified(True)
        elif not self.current_script_modified:
            self.setScriptModified(True)
        if not self.nodeMode:
            self.toAutosave = True

    def pin(self, pressed):
        if pressed:
            self.setWindowFlags(self.windowFlags() |
                                QtCore.Qt.WindowStaysOnTopHint)
            self.pinned = True
            self.show()
        else:
            self.setWindowFlags(self.windowFlags() & ~
                                QtCore.Qt.WindowStaysOnTopHint)
            self.pinned = False
            self.show()

    def findSE(self):
        for widget in QtWidgets.QApplication.allWidgets():
            if "Script Editor" in widget.windowTitle():
                return widget

    # FunctiosaveScrollValuens for Nuke's Script Editor
    def findScriptEditors(self):
        script_editors = []
        for widget in QtWidgets.QApplication.allWidgets():
            if "Script Editor" in widget.windowTitle() and len(widget.children()) > 5:
                script_editors.append(widget)
        return script_editors

    def findSEInput(self, se):
        return se.children()[-1].children()[0]

    def findSEOutput(self, se):
        return se.children()[-1].children()[1]

    def findSERunBtn(self, se):
        for btn in se.children():
            try:
                if "Run the current script" in btn.toolTip():
                    return btn
            except:
                pass
        return False

    def setSEOutputEvent(self):
        nukeScriptEditors = self.findScriptEditors()
        # Take the console from the first script editor found...
        self.origConsoleText = self.nukeSEOutput.document().toPlainText().encode("utf8")
        for se in nukeScriptEditors:
            se_output = self.findSEOutput(se)
            se_output.textChanged.connect(
                partial(consoleChanged, se_output, self))
            consoleChanged(se_output, self)  # Initialise.


class KnobScripterPane(KnobScripter):
    def __init__(self, node="", knob="knobChanged"):
        super(KnobScripterPane, self).__init__()
        self.isPane = True

    def showEvent(self, the_event):
        try:
            killPaneMargins(self)
        except:
            pass
        return KnobScripter.showEvent(self, the_event)

    def hideEvent(self, the_event):
        self.autosave()
        return KnobScripter.hideEvent(self, the_event)


def consoleChanged(self, ks):
    ''' This will be called every time the ScriptEditor Output text is changed '''
    try:
        if ks:  # KS exists
            ksOutput = ks.script_output  # The console TextEdit widget
            ksText = self.document().toPlainText().encode("utf8")
            # The text from the console that will be omitted
            origConsoleText = ks.origConsoleText
            if ksText.startswith(origConsoleText):
                ksText = ksText[len(origConsoleText):]
            else:
                ks.origConsoleText = ""
            ksOutput.setPlainText(ksText)
            ksOutput.verticalScrollBar().setValue(ksOutput.verticalScrollBar().maximum())
    except:
        pass


def killPaneMargins(widget_object):
    if widget_object:
        target_widgets = set()
        target_widgets.add(widget_object.parentWidget().parentWidget())
        target_widgets.add(widget_object.parentWidget(
        ).parentWidget().parentWidget().parentWidget())

        for widget_layout in target_widgets:
            try:
                widget_layout.layout().setContentsMargins(0, 0, 0, 0)
            except:
                pass


def debug(lev=0):
    ''' Convenience function to set the KnobScripter on debug mode'''
    # levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
    # for handler in logging.root.handlers[:]:
    #     logging.root.removeHandler(handler)
    # logging.basicConfig(level=levels[lev])
    # Changed to a shitty way for now
    global DebugMode
    DebugMode = True


def log(text):
    ''' Display a debug info message. Yes, in a stupid way. I know.'''
    global DebugMode
    if DebugMode:
        print(text)


# ---------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------
class FileNameDialog(QtWidgets.QDialog):
    '''
    Dialog for creating new... (mode = "folder", "script" or "knob").
    '''

    def __init__(self, parent=None, mode="folder", text=""):
        if parent.isPane:
            super(FileNameDialog, self).__init__()
        else:
            super(FileNameDialog, self).__init__(parent)
            #self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.mode = mode
        self.text = text

        title = "Create new {}.".format(self.mode)
        self.setWindowTitle(title)

        self.initUI()

    def initUI(self):
        # Widgets
        self.name_label = QtWidgets.QLabel("Name: ")
        self.name_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.name_lineEdit = QtWidgets.QLineEdit()
        self.name_lineEdit.setText(self.text)
        self.name_lineEdit.textChanged.connect(self.nameChanged)

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.button(
            QtWidgets.QDialogButtonBox.Ok).setEnabled(self.text != "")
        self.button_box.accepted.connect(self.clickedOk)
        self.button_box.rejected.connect(self.clickedCancel)

        # Layout
        self.master_layout = QtWidgets.QVBoxLayout()
        self.name_layout = QtWidgets.QHBoxLayout()
        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.name_lineEdit)
        self.master_layout.addLayout(self.name_layout)
        self.master_layout.addWidget(self.button_box)
        self.setLayout(self.master_layout)

        self.name_lineEdit.setFocus()
        self.setMinimumWidth(250)

    def nameChanged(self):
        txt = self.name_lineEdit.text()
        m = r"[\w]*$"
        if self.mode == "knob":  # Knobs can't start with a number...
            m = r"[a-zA-Z_]+" + m

        if re.match(m, txt) or txt == "":
            self.text = txt
        else:
            self.name_lineEdit.setText(self.text)

        self.button_box.button(
            QtWidgets.QDialogButtonBox.Ok).setEnabled(self.text != "")
        return

    def clickedOk(self):
        self.accept()
        return

    def clickedCancel(self):
        self.reject()
        return


class TextInputDialog(QtWidgets.QDialog):
    '''
    Simple dialog for a text input.
    '''

    def __init__(self, parent=None, name="", text="", title=""):
        if parent.isPane:
            super(TextInputDialog, self).__init__()
        else:
            super(TextInputDialog, self).__init__(parent)
            #self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        self.name = name  # title of textinput
        self.text = text  # default content of textinput

        self.setWindowTitle(title)

        self.initUI()

    def initUI(self):
        # Widgets
        self.name_label = QtWidgets.QLabel(self.name + ": ")
        self.name_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.name_lineEdit = QtWidgets.QLineEdit()
        self.name_lineEdit.setText(self.text)
        self.name_lineEdit.textChanged.connect(self.nameChanged)

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        #self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(self.text != "")
        self.button_box.accepted.connect(self.clickedOk)
        self.button_box.rejected.connect(self.clickedCancel)

        # Layout
        self.master_layout = QtWidgets.QVBoxLayout()
        self.name_layout = QtWidgets.QHBoxLayout()
        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.name_lineEdit)
        self.master_layout.addLayout(self.name_layout)
        self.master_layout.addWidget(self.button_box)
        self.setLayout(self.master_layout)

        self.name_lineEdit.setFocus()
        self.setMinimumWidth(250)

    def nameChanged(self):
        self.text = self.name_lineEdit.text()

    def clickedOk(self):
        self.accept()
        return

    def clickedCancel(self):
        self.reject()
        return


class ChooseNodeDialog(QtWidgets.QDialog):
    '''
    Dialog for selecting a node by its name. Only admits nodes that exist (including root, preferences...)
    '''

    def __init__(self, parent=None, name=""):
        if parent.isPane:
            super(ChooseNodeDialog, self).__init__()
        else:
            super(ChooseNodeDialog, self).__init__(parent)

        self.name = name  # Name of node (will be "" by default)
        self.allNodes = []

        self.setWindowTitle("Enter the node's name...")

        self.initUI()

    def initUI(self):
        # Widgets
        self.name_label = QtWidgets.QLabel("Name: ")
        self.name_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.name_lineEdit = QtWidgets.QLineEdit()
        self.name_lineEdit.setText(self.name)
        self.name_lineEdit.textChanged.connect(self.nameChanged)

        self.allNodes = self.getAllNodes()
        completer = QtWidgets.QCompleter(self.allNodes, self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.name_lineEdit.setCompleter(completer)

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(
            nuke.exists(self.name))
        self.button_box.accepted.connect(self.clickedOk)
        self.button_box.rejected.connect(self.clickedCancel)

        # Layout
        self.master_layout = QtWidgets.QVBoxLayout()
        self.name_layout = QtWidgets.QHBoxLayout()
        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.name_lineEdit)
        self.master_layout.addLayout(self.name_layout)
        self.master_layout.addWidget(self.button_box)
        self.setLayout(self.master_layout)

        self.name_lineEdit.setFocus()
        self.setMinimumWidth(250)

    def getAllNodes(self):
        self.allNodes = [n.fullName() for n in nuke.allNodes(
            recurseGroups=True)]  # if parent is in current context??
        self.allNodes.extend(["root", "preferences"])
        return self.allNodes

    def nameChanged(self):
        self.name = self.name_lineEdit.text()
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(
            self.name in self.allNodes)

    def clickedOk(self):
        self.accept()
        return

    def clickedCancel(self):
        self.reject()
        return


# ------------------------------------------------------------------------------------------------------
# Script Editor Widget
# Wouter Gilsing built an incredibly useful python script editor for his Hotbox Manager, so I had it
# really easy for this part!
# Starting from his script editor, I changed the style and added the sublime-like functionality.
# I think this bit of code has the potential to get used in many nuke tools.
# Credit to him: http://www.woutergilsing.com/
# Originally used on W_Hotbox v1.5: http://www.nukepedia.com/python/ui/w_hotbox
# ------------------------------------------------------------------------------------------------------
class KnobScripterTextEdit(QtWidgets.QPlainTextEdit):
    # Signal that will be emitted when the user has changed the text
    userChangedEvent = QtCore.Signal()

    def __init__(self, knobScripter=""):
        super(KnobScripterTextEdit, self).__init__()

        self.knobScripter = knobScripter
        self.selected_text = ""

        # Setup line numbers
        if self.knobScripter != "":
            self.tabSpaces = self.knobScripter.tabSpaces
        else:
            self.tabSpaces = 4
        self.lineNumberArea = KSLineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.updateLineNumberAreaWidth()

        # Highlight line
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

    # --------------------------------------------------------------------------------------------------
    # This is adapted from an original version by Wouter Gilsing.
    # Extract from his original comments:
    # While researching the implementation of line number, I had a look at Nuke's Blinkscript node. [..]
    # thefoundry.co.uk/products/nuke/developers/100/pythonreference/nukescripts.blinkscripteditor-pysrc.html
    # I stripped and modified the useful bits of the line number related parts of the code [..]
    # Credits to theFoundry for writing the blinkscripteditor, best example code I could wish for.
    # --------------------------------------------------------------------------------------------------

    def lineNumberAreaWidth(self):
        digits = 1
        maxNum = max(1, self.blockCount())
        while (maxNum >= 10):
            maxNum /= 10
            digits += 1

        space = 7 + self.fontMetrics().width('9') * digits
        return space

    def updateLineNumberAreaWidth(self):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):

        if (dy):
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(
                0, rect.y(), self.lineNumberArea.width(), rect.height())

        if (rect.contains(self.viewport().rect())):
            self.updateLineNumberAreaWidth()

    def resizeEvent(self, event):
        QtWidgets.QPlainTextEdit.resizeEvent(self, event)

        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QtCore.QRect(
            cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):

        if self.isReadOnly():
            return

        painter = QtGui.QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QtGui.QColor(36, 36, 36))  # Number bg

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(
            block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        currentLine = self.document().findBlock(
            self.textCursor().position()).blockNumber()

        painter.setPen(self.palette().color(QtGui.QPalette.Text))

        painterFont = QtGui.QFont()
        painterFont.setFamily("Courier")
        painterFont.setStyleHint(QtGui.QFont.Monospace)
        painterFont.setFixedPitch(True)
        if self.knobScripter != "":
            painterFont.setPointSize(self.knobScripter.fontSize)
            painter.setFont(self.knobScripter.script_editor_font)

        while (block.isValid() and top <= event.rect().bottom()):

            textColor = QtGui.QColor(110, 110, 110)  # Numbers

            if blockNumber == currentLine and self.hasFocus():
                textColor = QtGui.QColor(255, 170, 0)  # Number highlighted

            painter.setPen(textColor)

            number = "%s" % str(blockNumber + 1)
            painter.drawText(-3, top, self.lineNumberArea.width(),
                             self.fontMetrics().height(), QtCore.Qt.AlignRight, number)

            # Move to the next block
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    def keyPressEvent(self, event):
        '''
        Custom actions for specific keystrokes
        '''
        key = event.key()
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        alt = bool(event.modifiers() & Qt.AltModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        pre_scroll = self.verticalScrollBar().value()
        #modifiers = QtWidgets.QApplication.keyboardModifiers()
        #ctrl = (modifiers == Qt.ControlModifier)
        #shift = (modifiers == Qt.ShiftModifier)

        up_arrow = 16777235
        down_arrow = 16777237

        # if Tab convert to Space
        if key == 16777217:
            self.indentation('indent')

        # if Shift+Tab remove indent
        elif key == 16777218:
            self.indentation('unindent')

        # if BackSpace try to snap to previous indent level
        elif key == 16777219:
            if not self.unindentBackspace():
                QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
        else:
            # COOL BEHAVIORS SIMILAR TO SUBLIME GO NEXT!
            cursor = self.textCursor()
            cpos = cursor.position()
            apos = cursor.anchor()
            text_before_cursor = self.toPlainText()[:min(cpos, apos)]
            text_after_cursor = self.toPlainText()[max(cpos, apos):]
            text_all = self.toPlainText()
            to_line_start = text_before_cursor[::-1].find("\n")
            if to_line_start == -1:
                # Position of the start of the line that includes the cursor selection start
                linestart_pos = 0
            else:
                linestart_pos = len(text_before_cursor) - to_line_start

            to_line_end = text_after_cursor.find("\n")
            if to_line_end == -1:
                # Position of the end of the line that includes the cursor selection end
                lineend_pos = len(text_all)
            else:
                lineend_pos = max(cpos, apos) + to_line_end

            text_before_lines = text_all[:linestart_pos]
            text_after_lines = text_all[lineend_pos:]
            if len(text_after_lines) and text_after_lines.startswith("\n"):
                text_after_lines = text_after_lines[1:]
            text_lines = text_all[linestart_pos:lineend_pos]

            if cursor.hasSelection():
                selection = cursor.selection().toPlainText()
            else:
                selection = ""
            if key == Qt.Key_ParenLeft and (len(selection) > 0 or re.match(r"[\s)}\];]+", text_after_cursor) or not len(text_after_cursor)):  # (
                cursor.insertText("(" + selection + ")")
                cursor.setPosition(apos + 1, QtGui.QTextCursor.MoveAnchor)
                cursor.setPosition(cpos + 1, QtGui.QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
            # )
            elif key == Qt.Key_ParenRight and text_after_cursor.startswith(")"):
                cursor.movePosition(QtGui.QTextCursor.NextCharacter)
                self.setTextCursor(cursor)
            elif key == Qt.Key_BracketLeft and (len(selection) > 0 or re.match(r"[\s)}\];]+", text_after_cursor) or not len(text_after_cursor)):  # [
                cursor.insertText("[" + selection + "]")
                cursor.setPosition(apos + 1, QtGui.QTextCursor.MoveAnchor)
                cursor.setPosition(cpos + 1, QtGui.QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
            # ]
            elif key in [Qt.Key_BracketRight, 43] and text_after_cursor.startswith("]"):
                cursor.movePosition(QtGui.QTextCursor.NextCharacter)
                self.setTextCursor(cursor)
            elif key == Qt.Key_BraceLeft and (len(selection) > 0 or re.match(r"[\s)}\];]+", text_after_cursor) or not len(text_after_cursor)):  # {
                cursor.insertText("{" + selection + "}")
                cursor.setPosition(apos + 1, QtGui.QTextCursor.MoveAnchor)
                cursor.setPosition(cpos + 1, QtGui.QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
            # }
            elif key in [199, Qt.Key_BraceRight] and text_after_cursor.startswith("}"):
                cursor.movePosition(QtGui.QTextCursor.NextCharacter)
                self.setTextCursor(cursor)
            elif key == 34:  # "
                if len(selection) > 0:
                    cursor.insertText('"' + selection + '"')
                    cursor.setPosition(apos + 1, QtGui.QTextCursor.MoveAnchor)
                    cursor.setPosition(cpos + 1, QtGui.QTextCursor.KeepAnchor)
                # and not re.search(r"(?:[\s)\]]+|$)",text_before_cursor):
                elif text_after_cursor.startswith('"') and '"' in text_before_cursor.split("\n")[-1]:
                    cursor.movePosition(QtGui.QTextCursor.NextCharacter)
                # If chars after cursor, act normal
                elif not re.match(r"(?:[\s)\]]+|$)", text_after_cursor):
                    QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
                # If chars before cursor, act normal
                elif not re.search(r"[\s.({\[,]$", text_before_cursor) and text_before_cursor != "":
                    QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
                else:
                    cursor.insertText('"' + selection + '"')
                    cursor.setPosition(apos + 1, QtGui.QTextCursor.MoveAnchor)
                    cursor.setPosition(cpos + 1, QtGui.QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
            elif key == 39:  # '
                if len(selection) > 0:
                    cursor.insertText("'" + selection + "'")
                    cursor.setPosition(apos + 1, QtGui.QTextCursor.MoveAnchor)
                    cursor.setPosition(cpos + 1, QtGui.QTextCursor.KeepAnchor)
                # and not re.search(r"(?:[\s)\]]+|$)",text_before_cursor):
                elif text_after_cursor.startswith("'") and "'" in text_before_cursor.split("\n")[-1]:
                    cursor.movePosition(QtGui.QTextCursor.NextCharacter)
                # If chars after cursor, act normal
                elif not re.match(r"(?:[\s)\]]+|$)", text_after_cursor):
                    QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
                # If chars before cursor, act normal
                elif not re.search(r"[\s.({\[,]$", text_before_cursor) and text_before_cursor != "":
                    QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
                else:
                    cursor.insertText("'" + selection + "'")
                    cursor.setPosition(apos + 1, QtGui.QTextCursor.MoveAnchor)
                    cursor.setPosition(cpos + 1, QtGui.QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
            elif key == 35 and len(selection):  # (yes, a hash)
                # If there's a selection, insert a hash at the start of each line.. how the fuck?
                if selection != "":
                    selection_split = selection.split("\n")
                    if all(i.startswith("#") for i in selection_split):
                        selection_commented = "\n".join(
                            [s[1:] for s in selection_split])  # Uncommented
                    else:
                        selection_commented = "#" + "\n#".join(selection_split)
                    cursor.insertText(selection_commented)
                    if apos > cpos:
                        cursor.setPosition(
                            apos + len(selection_commented) - len(selection), QtGui.QTextCursor.MoveAnchor)
                        cursor.setPosition(cpos, QtGui.QTextCursor.KeepAnchor)
                    else:
                        cursor.setPosition(apos, QtGui.QTextCursor.MoveAnchor)
                        cursor.setPosition(
                            cpos + len(selection_commented) - len(selection), QtGui.QTextCursor.KeepAnchor)
                    self.setTextCursor(cursor)

            elif key == 68 and ctrl and shift:  # Ctrl+Shift+D, to duplicate text or line/s

                if not len(selection):
                    self.setPlainText(
                        text_before_lines + text_lines + "\n" + text_lines + "\n" + text_after_lines)
                    cursor.setPosition(
                        apos + len(text_lines) + 1, QtGui.QTextCursor.MoveAnchor)
                    cursor.setPosition(
                        cpos + len(text_lines) + 1, QtGui.QTextCursor.KeepAnchor)
                    self.setTextCursor(cursor)
                    self.verticalScrollBar().setValue(pre_scroll)
                    self.scrollToCursor()
                else:
                    if text_before_cursor.endswith("\n") and not selection.startswith("\n"):
                        cursor.insertText(selection + "\n" + selection)
                        cursor.setPosition(
                            apos + len(selection) + 1, QtGui.QTextCursor.MoveAnchor)
                        cursor.setPosition(
                            cpos + len(selection) + 1, QtGui.QTextCursor.KeepAnchor)
                    else:
                        cursor.insertText(selection + selection)
                        cursor.setPosition(
                            apos + len(selection), QtGui.QTextCursor.MoveAnchor)
                        cursor.setPosition(
                            cpos + len(selection), QtGui.QTextCursor.KeepAnchor)
                    self.setTextCursor(cursor)

            # Ctrl+Shift+Up, to move the selected line/s up
            elif key == up_arrow and ctrl and shift and len(text_before_lines):
                prev_line_start_distance = text_before_lines[:-1][::-1].find(
                    "\n")
                if prev_line_start_distance == -1:
                    prev_line_start_pos = 0  # Position of the start of the previous line
                else:
                    prev_line_start_pos = len(
                        text_before_lines) - 1 - prev_line_start_distance
                prev_line = text_before_lines[prev_line_start_pos:]

                text_before_prev_line = text_before_lines[:prev_line_start_pos]

                if prev_line.endswith("\n"):
                    prev_line = prev_line[:-1]

                if len(text_after_lines):
                    text_after_lines = "\n" + text_after_lines

                self.setPlainText(
                    text_before_prev_line + text_lines + "\n" + prev_line + text_after_lines)
                cursor.setPosition(apos - len(prev_line) - 1,
                                   QtGui.QTextCursor.MoveAnchor)
                cursor.setPosition(cpos - len(prev_line) - 1,
                                   QtGui.QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
                self.verticalScrollBar().setValue(pre_scroll)
                self.scrollToCursor()
                return

            elif key == down_arrow and ctrl and shift:  # Ctrl+Shift+Up, to move the selected line/s up
                if not len(text_after_lines):
                    text_after_lines = ""
                next_line_end_distance = text_after_lines.find("\n")
                if next_line_end_distance == -1:
                    next_line_end_pos = len(text_all)
                else:
                    next_line_end_pos = next_line_end_distance
                next_line = text_after_lines[:next_line_end_pos]
                text_after_next_line = text_after_lines[next_line_end_pos:]

                self.setPlainText(text_before_lines + next_line +
                                  "\n" + text_lines + text_after_next_line)
                cursor.setPosition(apos + len(next_line) + 1,
                                   QtGui.QTextCursor.MoveAnchor)
                cursor.setPosition(cpos + len(next_line) + 1,
                                   QtGui.QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
                self.verticalScrollBar().setValue(pre_scroll)
                self.scrollToCursor()
                return

            # If up key and nothing happens, go to start
            elif key == up_arrow and not len(text_before_lines):
                if not shift:
                    cursor.setPosition(0, QtGui.QTextCursor.MoveAnchor)
                    self.setTextCursor(cursor)
                else:
                    cursor.setPosition(0, QtGui.QTextCursor.KeepAnchor)
                    self.setTextCursor(cursor)

            # If up key and nothing happens, go to start
            elif key == down_arrow and not len(text_after_lines):
                if not shift:
                    cursor.setPosition(
                        len(text_all), QtGui.QTextCursor.MoveAnchor)
                    self.setTextCursor(cursor)
                else:
                    cursor.setPosition(
                        len(text_all), QtGui.QTextCursor.KeepAnchor)
                    self.setTextCursor(cursor)

            # if enter or return, match indent level
            elif key in [16777220, 16777221]:
                self.indentNewLine()
            else:
                QtWidgets.QPlainTextEdit.keyPressEvent(self, event)

        self.scrollToCursor()

    def scrollToCursor(self):
        self.cursor = self.textCursor()
        # Does nothing, but makes the scroll go to the right place...
        self.cursor.movePosition(QtGui.QTextCursor.NoMove)
        self.setTextCursor(self.cursor)

    def getCursorInfo(self):

        self.cursor = self.textCursor()

        self.firstChar = self.cursor.selectionStart()
        self.lastChar = self.cursor.selectionEnd()

        self.noSelection = False
        if self.firstChar == self.lastChar:
            self.noSelection = True

        self.originalPosition = self.cursor.position()
        self.cursorBlockPos = self.cursor.positionInBlock()

    def unindentBackspace(self):
        '''
        #snap to previous indent level
        '''
        self.getCursorInfo()

        if not self.noSelection or self.cursorBlockPos == 0:
            return False

        # check text in front of cursor
        textInFront = self.document().findBlock(
            self.firstChar).text()[:self.cursorBlockPos]

        # check whether solely spaces
        if textInFront != ' ' * self.cursorBlockPos:
            return False

        # snap to previous indent level
        spaces = len(textInFront)
        for space in range(spaces - ((spaces - 1) / self.tabSpaces) * self.tabSpaces - 1):
            self.cursor.deletePreviousChar()

    def indentNewLine(self):

        # in case selection covers multiple line, make it one line first
        self.insertPlainText('')

        self.getCursorInfo()

        # check how many spaces after cursor
        text = self.document().findBlock(self.firstChar).text()

        textInFront = text[:self.cursorBlockPos]

        if len(textInFront) == 0:
            self.insertPlainText('\n')
            return

        indentLevel = 0
        for i in textInFront:
            if i == ' ':
                indentLevel += 1
            else:
                break

        indentLevel /= self.tabSpaces

        # find out whether textInFront's last character was a ':'
        # if that's the case add another indent.
        # ignore any spaces at the end, however also
        # make sure textInFront is not just an indent
        if textInFront.count(' ') != len(textInFront):
            while textInFront[-1] == ' ':
                textInFront = textInFront[:-1]

        if textInFront[-1] == ':':
            indentLevel += 1

        # new line
        self.insertPlainText('\n')
        # match indent
        self.insertPlainText(' ' * (self.tabSpaces * indentLevel))

    def indentation(self, mode):

        pre_scroll = self.verticalScrollBar().value()
        self.getCursorInfo()

        # if nothing is selected and mode is set to indent, simply insert as many
        # space as needed to reach the next indentation level.
        if self.noSelection and mode == 'indent':

            remainingSpaces = self.tabSpaces - \
                (self.cursorBlockPos % self.tabSpaces)
            self.insertPlainText(' ' * remainingSpaces)
            return

        selectedBlocks = self.findBlocks(self.firstChar, self.lastChar)
        beforeBlocks = self.findBlocks(
            last=self.firstChar - 1, exclude=selectedBlocks)
        afterBlocks = self.findBlocks(
            first=self.lastChar + 1, exclude=selectedBlocks)

        beforeBlocksText = self.blocks2list(beforeBlocks)
        selectedBlocksText = self.blocks2list(selectedBlocks, mode)
        afterBlocksText = self.blocks2list(afterBlocks)

        combinedText = '\n'.join(
            beforeBlocksText + selectedBlocksText + afterBlocksText)

        # make sure the line count stays the same
        originalBlockCount = len(self.toPlainText().split('\n'))
        combinedText = '\n'.join(combinedText.split('\n')[:originalBlockCount])

        self.clear()
        self.setPlainText(combinedText)

        if self.noSelection:
            self.cursor.setPosition(self.lastChar)

        # check whether the the original selection was from top to bottom or vice versa
        else:
            if self.originalPosition == self.firstChar:
                first = self.lastChar
                last = self.firstChar
                firstBlockSnap = QtGui.QTextCursor.EndOfBlock
                lastBlockSnap = QtGui.QTextCursor.StartOfBlock
            else:
                first = self.firstChar
                last = self.lastChar
                firstBlockSnap = QtGui.QTextCursor.StartOfBlock
                lastBlockSnap = QtGui.QTextCursor.EndOfBlock

            self.cursor.setPosition(first)
            self.cursor.movePosition(
                firstBlockSnap, QtGui.QTextCursor.MoveAnchor)
            self.cursor.setPosition(last, QtGui.QTextCursor.KeepAnchor)
            self.cursor.movePosition(
                lastBlockSnap, QtGui.QTextCursor.KeepAnchor)

        self.setTextCursor(self.cursor)
        self.verticalScrollBar().setValue(pre_scroll)

    def findBlocks(self, first=0, last=None, exclude=[]):
        blocks = []
        if last == None:
            last = self.document().characterCount()
        for pos in range(first, last + 1):
            block = self.document().findBlock(pos)
            if block not in blocks and block not in exclude:
                blocks.append(block)
        return blocks

    def blocks2list(self, blocks, mode=None):
        text = []
        for block in blocks:
            blockText = block.text()
            if mode == 'unindent':
                if blockText.startswith(' ' * self.tabSpaces):
                    blockText = blockText[self.tabSpaces:]
                    self.lastChar -= self.tabSpaces
                elif blockText.startswith('\t'):
                    blockText = blockText[1:]
                    self.lastChar -= 1

            elif mode == 'indent':
                blockText = ' ' * self.tabSpaces + blockText
                self.lastChar += self.tabSpaces

            text.append(blockText)

        return text

    def highlightCurrentLine(self):
        '''
        Highlight currently selected line
        '''
        extraSelections = []

        selection = QtWidgets.QTextEdit.ExtraSelection()

        lineColor = QtGui.QColor(62, 62, 62, 255)

        selection.format.setBackground(lineColor)
        selection.format.setProperty(
            QtGui.QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()

        extraSelections.append(selection)

        self.setExtraSelections(extraSelections)
        self.scrollToCursor()

    def format(self, rgb, style=''):
        '''
        Return a QtWidgets.QTextCharFormat with the given attributes.
        '''
        color = QtGui.QColor(*rgb)
        textFormat = QtGui.QTextCharFormat()
        textFormat.setForeground(color)

        if 'bold' in style:
            textFormat.setFontWeight(QtGui.QFont.Bold)
        if 'italic' in style:
            textFormat.setFontItalic(True)
        if 'underline' in style:
            textFormat.setUnderlineStyle(QtGui.QTextCharFormat.SingleUnderline)

        return textFormat


class KSLineNumberArea(QtWidgets.QWidget):
    def __init__(self, scriptEditor):
        super(KSLineNumberArea, self).__init__(scriptEditor)

        self.scriptEditor = scriptEditor
        self.setStyleSheet("text-align: center;")

    def paintEvent(self, event):
        self.scriptEditor.lineNumberAreaPaintEvent(event)
        return


class KSScriptEditorHighlighter(QtGui.QSyntaxHighlighter):
    '''
    This is also adapted from an original version by Wouter Gilsing. His comments:

    Modified, simplified version of some code found I found when researching:
    wiki.python.org/moin/PyQt/Python%20syntax%20highlighting
    They did an awesome job, so credits to them. I only needed to make some
    modifications to make it fit my needs.
    '''

    def __init__(self, document, parent=None):

        super(KSScriptEditorHighlighter, self).__init__(document)
        self.knobScripter = parent
        self.script_editor = self.knobScripter.script_editor
        self.selected_text = ""
        self.selected_text_prev = ""
        self.rules_sublime = ""

        self.styles = {
            'keyword': self.format([238, 117, 181], 'bold'),
            'string': self.format([242, 136, 135]),
            'comment': self.format([143, 221, 144]),
            'numbers': self.format([174, 129, 255]),
            'custom': self.format([255, 170, 0], 'italic'),
            'selected': self.format([255, 255, 255], 'bold underline'),
            'underline': self.format([240, 240, 240], 'underline'),
        }

        self.keywords = [
            'and', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'exec', 'finally',
            'for', 'from', 'global', 'if', 'import', 'in',
            'is', 'lambda', 'not', 'or', 'pass', 'print',
            'raise', 'return', 'try', 'while', 'yield', 'with', 'as'
        ]

        self.operatorKeywords = [
            '=', '==', '!=', '<', '<=', '>', '>=',
            '\+', '-', '\*', '/', '//', '\%', '\*\*',
            '\+=', '-=', '\*=', '/=', '\%=',
            '\^', '\|', '\&', '\~', '>>', '<<'
        ]

        self.variableKeywords = ['int', 'str',
                                 'float', 'bool', 'list', 'dict', 'set']

        self.numbers = ['True', 'False', 'None']
        self.loadAltStyles()

        self.tri_single = (QtCore.QRegExp("'''"), 1, self.styles['comment'])
        self.tri_double = (QtCore.QRegExp('"""'), 2, self.styles['comment'])

        # rules
        rules = []

        rules += [(r'\b%s\b' % i, 0, self.styles['keyword'])
                  for i in self.keywords]
        rules += [(i, 0, self.styles['keyword'])
                  for i in self.operatorKeywords]
        rules += [(r'\b%s\b' % i, 0, self.styles['numbers'])
                  for i in self.numbers]

        rules += [

            # integers
            (r'\b[0-9]+\b', 0, self.styles['numbers']),
            # Double-quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, self.styles['string']),
            # Single-quoted string, possibly containing escape sequences
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, self.styles['string']),
            # From '#' until a newline
            (r'#[^\n]*', 0, self.styles['comment']),
        ]

        # Build a QRegExp for each pattern
        self.rules_nuke = [(QtCore.QRegExp(pat), index, fmt)
                           for (pat, index, fmt) in rules]
        self.rules = self.rules_nuke

    def loadAltStyles(self):
        ''' Loads other color styles apart from Nuke's default. '''
        self.styles_sublime = {
            'base': self.format([255, 255, 255]),
            'keyword': self.format([237, 36, 110]),
            'string': self.format([237, 229, 122]),
            'comment': self.format([125, 125, 125]),
            'numbers': self.format([165, 120, 255]),
            'functions': self.format([184, 237, 54]),
            'blue': self.format([130, 226, 255], 'italic'),
            'arguments': self.format([255, 170, 10], 'italic'),
            'custom': self.format([200, 200, 200], 'italic'),
            'underline': self.format([240, 240, 240], 'underline'),
            'selected': self.format([255, 255, 255], 'bold underline'),
        }

        self.keywords_sublime = [
            'and', 'assert', 'break', 'continue',
            'del', 'elif', 'else', 'except', 'exec', 'finally',
            'for', 'from', 'global', 'if', 'import', 'in',
            'is', 'lambda', 'not', 'or', 'pass', 'print',
            'raise', 'return', 'try', 'while', 'yield', 'with', 'as'
        ]
        self.operatorKeywords_sublime = [
            '=', '==', '!=', '<', '<=', '>', '>=',
            '\+', '-', '\*', '/', '//', '\%', '\*\*',
            '\+=', '-=', '\*=', '/=', '\%=',
            '\^', '\|', '\&', '\~', '>>', '<<'
        ]

        self.baseKeywords_sublime = [
            ',',
        ]

        self.customKeywords_sublime = [
            'nuke',
        ]

        self.blueKeywords_sublime = [
            'def', 'class', 'int', 'str', 'float', 'bool', 'list', 'dict', 'set'
        ]

        self.argKeywords_sublime = [
            'self',
        ]

        self.tri_single_sublime = (QtCore.QRegExp(
            "'''"), 1, self.styles_sublime['comment'])
        self.tri_double_sublime = (QtCore.QRegExp(
            '"""'), 2, self.styles_sublime['comment'])
        self.numbers_sublime = ['True', 'False', 'None']

        # rules

        rules = []
        # First turn everything inside parentheses orange
        rules += [(r"def [\w]+[\s]*\((.*)\)", 1,
                   self.styles_sublime['arguments'])]
        # Now restore unwanted stuff...
        rules += [(i, 0, self.styles_sublime['base'])
                  for i in self.baseKeywords_sublime]
        rules += [(r"[^\(\w),.][\s]*[\w]+", 0, self.styles_sublime['base'])]

        # Everything else
        rules += [(r'\b%s\b' % i, 0, self.styles_sublime['keyword'])
                  for i in self.keywords_sublime]
        rules += [(i, 0, self.styles_sublime['keyword'])
                  for i in self.operatorKeywords_sublime]
        rules += [(i, 0, self.styles_sublime['custom'])
                  for i in self.customKeywords_sublime]
        rules += [(r'\b%s\b' % i, 0, self.styles_sublime['blue'])
                  for i in self.blueKeywords_sublime]
        rules += [(i, 0, self.styles_sublime['arguments'])
                  for i in self.argKeywords_sublime]
        rules += [(r'\b%s\b' % i, 0, self.styles_sublime['numbers'])
                  for i in self.numbers_sublime]

        rules += [

            # integers
            (r'\b[0-9]+\b', 0, self.styles_sublime['numbers']),
            # Double-quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, self.styles_sublime['string']),
            # Single-quoted string, possibly containing escape sequences
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, self.styles_sublime['string']),
            # From '#' until a newline
            (r'#[^\n]*', 0, self.styles_sublime['comment']),
            # Function definitions
            (r"def[\s]+([\w\.]+)", 1, self.styles_sublime['functions']),
            # Class definitions
            (r"class[\s]+([\w\.]+)", 1, self.styles_sublime['functions']),
            # Class argument (which is also a class so must be green)
            (r"class[\s]+[\w\.]+[\s]*\((.*)\)",
             1, self.styles_sublime['functions']),
            # Function arguments also pick their style...
            (r"def[\s]+[\w]+[\s]*\(([\w]+)", 1,
             self.styles_sublime['arguments']),
        ]

        # Build a QRegExp for each pattern
        self.rules_sublime = [(QtCore.QRegExp(pat), index, fmt)
                              for (pat, index, fmt) in rules]

    def format(self, rgb, style=''):
        '''
        Return a QtWidgets.QTextCharFormat with the given attributes.
        '''

        color = QtGui.QColor(*rgb)
        textFormat = QtGui.QTextCharFormat()
        textFormat.setForeground(color)

        if 'bold' in style:
            textFormat.setFontWeight(QtGui.QFont.Bold)
        if 'italic' in style:
            textFormat.setFontItalic(True)
        if 'underline' in style:
            textFormat.setUnderlineStyle(QtGui.QTextCharFormat.SingleUnderline)

        return textFormat

    def highlightBlock(self, text):
        '''
        Apply syntax highlighting to the given block of text.
        '''
        # Do other syntax formatting

        if self.knobScripter.color_scheme:
            self.color_scheme = self.knobScripter.color_scheme
        else:
            self.color_scheme = "nuke"

        if self.color_scheme == "nuke":
            self.rules = self.rules_nuke
        elif self.color_scheme == "sublime":
            self.rules = self.rules_sublime

        for expression, nth, format in self.rules:
            index = expression.indexIn(text, 0)

            while index >= 0:
                # We actually want the index of the nth match
                index = expression.pos(nth)
                length = len(expression.cap(nth))
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

        # Multi-line strings etc. based on selected scheme
        if self.color_scheme == "nuke":
            in_multiline = self.match_multiline(text, *self.tri_single)
            if not in_multiline:
                in_multiline = self.match_multiline(text, *self.tri_double)
        elif self.color_scheme == "sublime":
            in_multiline = self.match_multiline(text, *self.tri_single_sublime)
            if not in_multiline:
                in_multiline = self.match_multiline(
                    text, *self.tri_double_sublime)

        # TODO if there's a selection, highlight same occurrences in the full document. If no selection but something highlighted, unhighlight full document. (do it thru regex or sth)

    def match_multiline(self, text, delimiter, in_state, style):
        '''
        Check whether highlighting requires multiple lines.
        '''
        # If inside triple-single quotes, start at 0
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        # Otherwise, look for the delimiter on this line
        else:
            start = delimiter.indexIn(text)
            # Move past this match
            add = delimiter.matchedLength()

        # As long as there's a delimiter match on this line...
        while start >= 0:
            # Look for the ending delimiter
            end = delimiter.indexIn(text, start + add)
            # Ending delimiter on this line?
            if end >= add:
                length = end - start + add + delimiter.matchedLength()
                self.setCurrentBlockState(0)
            # No; multi-line string
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            # Apply formatting
            self.setFormat(start, length, style)
            # Look for the next match
            start = delimiter.indexIn(text, start + length)

        # Return True if still inside a multi-line string, False otherwise
        if self.currentBlockState() == in_state:
            return True
        else:
            return False

# --------------------------------------------------------------------------------------
# Script Output Widget
# The output logger works the same way as Nuke's python script editor output window
# --------------------------------------------------------------------------------------


class ScriptOutputWidget(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super(ScriptOutputWidget, self).__init__(parent)
        self.knobScripter = parent
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        self.setMinimumHeight(20)

    def keyPressEvent(self, event):
        ctrl = ((event.modifiers() and (Qt.ControlModifier)) != 0)
        alt = ((event.modifiers() and (Qt.AltModifier)) != 0)
        shift = ((event.modifiers() and (Qt.ShiftModifier)) != 0)
        key = event.key()
        if type(event) == QtGui.QKeyEvent:
            # print event.key()
            if key in [32]:  # Space
                return KnobScripter.keyPressEvent(self.knobScripter, event)
            elif key in [Qt.Key_Backspace, Qt.Key_Delete]:
                self.knobScripter.clearConsole()
        return QtWidgets.QTextEdit.keyPressEvent(self, event)

    # def mousePressEvent(self, QMouseEvent):
    #    if QMouseEvent.button() == Qt.RightButton:
    #        self.knobScripter.clearConsole()
    #    QtWidgets.QTextEdit.mousePressEvent(self, QMouseEvent)

# ---------------------------------------------------------------------
# Modified KnobScripterTextEdit to include snippets etc.
# ---------------------------------------------------------------------


class KnobScripterTextEditMain(KnobScripterTextEdit):
    def __init__(self, knobScripter, output=None, parent=None):
        super(KnobScripterTextEditMain, self).__init__(knobScripter)
        self.knobScripter = knobScripter
        self.script_output = output
        self.nukeCompleter = None
        self.currentNukeCompletion = None

        ########
        # FROM NUKE's SCRIPT EDITOR START
        ########
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)

        # Setup completer
        self.nukeCompleter = QtWidgets.QCompleter(self)
        self.nukeCompleter.setWidget(self)
        self.nukeCompleter.setCompletionMode(
            QtWidgets.QCompleter.UnfilteredPopupCompletion)
        self.nukeCompleter.setCaseSensitivity(Qt.CaseSensitive)
        try:
            self.nukeCompleter.setModel(QtGui.QStringListModel())
        except:
            self.nukeCompleter.setModel(QtCore.QStringListModel())

        self.nukeCompleter.activated.connect(self.insertNukeCompletion)
        self.nukeCompleter.highlighted.connect(self.completerHighlightChanged)
        ########
        # FROM NUKE's SCRIPT EDITOR END
        ########

    def findLongestEndingMatch(self, text, dic):
        '''
        If the text ends with a key in the dictionary, it returns the key and value.
        If there are several matches, returns the longest one.
        False if no matches.
        '''
        longest = 0  # len of longest match
        match_key = None
        match_snippet = ""
        for key, val in dic.items():
            #match = re.search(r"[\s\.({\[,;=+-]"+key+r"(?:[\s)\]\"]+|$)",text)
            match = re.search(r"[\s\.({\[,;=+-]" + key + r"$", text)
            if match or text == key:
                if len(key) > longest:
                    longest = len(key)
                    match_key = key
                    match_snippet = val
        if match_key is None:
            return False
        return match_key, match_snippet

    def placeholderToEnd(self, text, placeholder):
        '''Returns distance (int) from the first occurrence of the placeholder, to the end of the string with placeholders removed'''
        search = re.search(placeholder, text)
        if not search:
            return -1
        from_start = search.start()
        total = len(re.sub(placeholder, "", text))
        to_end = total - from_start
        return to_end

    def addSnippetText(self, snippet_text):
        ''' Adds the selected text as a snippet (taking care of $$, $name$ etc) to the script editor '''
        cursor_placeholder_find = r"(?<!\\)(\$\$)"  # Matches $$
        # Matches $thing$
        variables_placeholder_find = r"(?:^|[^\\\$])(\$[\w]*[^\t\n\r\f\v\$\\]+\$)(?:$|[^\$])"
        text = snippet_text
        while True:
            placeholder_variable = re.search(variables_placeholder_find, text)
            if not placeholder_variable:
                break
            word = placeholder_variable.groups()[0]
            word_bare = word[1:-1]
            panel = TextInputDialog(
                self.knobScripter, name=word_bare, text="", title="Set text for " + word_bare)
            if panel.exec_():
                #    # Accepted
                text = text.replace(word, panel.text)
            else:
                text = text.replace(word, "")

        placeholder_to_end = self.placeholderToEnd(
            text, cursor_placeholder_find)

        cursors = re.finditer(r"(?<!\\)(\$\$)", text)
        positions = []
        cursor_len = 0
        for m in cursors:
            if len(positions) < 2:
                positions.append(m.start())
        if len(positions) > 1:
            cursor_len = positions[1] - positions[0] - 2

        text = re.sub(cursor_placeholder_find, "", text)
        self.cursor.insertText(text)
        if placeholder_to_end >= 0:
            for i in range(placeholder_to_end):
                self.cursor.movePosition(QtGui.QTextCursor.PreviousCharacter)
            for i in range(cursor_len):
                self.cursor.movePosition(
                    QtGui.QTextCursor.NextCharacter, QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(self.cursor)

    def keyPressEvent(self, event):

        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        alt = bool(event.modifiers() & Qt.AltModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        key = event.key()

        # ADAPTED FROM NUKE's SCRIPT EDITOR:
        # Get completer state
        self.nukeCompleterShowing = self.nukeCompleter.popup().isVisible()

        # BEFORE ANYTHING ELSE, IF SPECIAL MODIFIERS SIMPLY IGNORE THE REST
        if not self.nukeCompleterShowing and (ctrl or shift or alt):
            # Bypassed!
            if key not in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab]:
                KnobScripterTextEdit.keyPressEvent(self, event)
                return

        # If the completer is showing
        if self.nukeCompleterShowing:
            tc = self.textCursor()
            # If we're hitting enter, do completion
            if key in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab]:
                if not self.currentNukeCompletion:
                    self.nukeCompleter.setCurrentRow(0)
                    self.currentNukeCompletion = self.nukeCompleter.currentCompletion()
                # print str(self.nukeCompleter.completionModel[0])
                self.insertNukeCompletion(self.currentNukeCompletion)
                self.nukeCompleter.popup().hide()
                self.nukeCompleterShowing = False
            # If you're hitting right or escape, hide the popup
            elif key == Qt.Key_Right or key == Qt.Key_Escape:
                self.nukeCompleter.popup().hide()
                self.nukeCompleterShowing = False
            # If you hit tab, escape or ctrl-space, hide the completer
            elif key == Qt.Key_Tab or key == Qt.Key_Escape or (ctrl and key == Qt.Key_Space):
                self.currentNukeCompletion = ""
                self.nukeCompleter.popup().hide()
                self.nukeCompleterShowing = False
            # If none of the above, update the completion model
            else:
                QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
                # Edit completion model
                colNum = tc.columnNumber()
                posNum = tc.position()
                inputText = self.toPlainText()
                inputTextSplit = inputText.splitlines()
                runningLength = 0
                currentLine = None
                for line in inputTextSplit:
                    length = len(line)
                    runningLength += length
                    if runningLength >= posNum:
                        currentLine = line
                        break
                    runningLength += 1
                if currentLine:
                    completionPart = currentLine.split(" ")[-1]
                    if "(" in completionPart:
                        completionPart = completionPart.split("(")[-1]
                    self.completeNukePartUnderCursor(completionPart)
            return

        if type(event) == QtGui.QKeyEvent:
            if key == Qt.Key_Escape:  # Close the knobscripter...
                self.knobScripter.close()
            elif not ctrl and not alt and not shift and event.key() == Qt.Key_Tab:
                self.placeholder = "$$"
                # 1. Set the cursor
                self.cursor = self.textCursor()

                # 2. Save text before and after
                cpos = self.cursor.position()
                text_before_cursor = self.toPlainText()[:cpos]
                line_before_cursor = text_before_cursor.split('\n')[-1]
                text_after_cursor = self.toPlainText()[cpos:]

                # 3. Check coincidences in snippets dicts
                try:  # Meaning snippet found
                    match_key, match_snippet = self.findLongestEndingMatch(
                        line_before_cursor, self.knobScripter.snippets)
                    for i in range(len(match_key)):
                        self.cursor.deletePreviousChar()
                    # This function takes care of adding the appropriate snippet and moving the cursor...
                    self.addSnippetText(match_snippet)
                except:  # Meaning snippet not found...
                    # ADAPTED FROM NUKE's SCRIPT EDITOR:
                    tc = self.textCursor()
                    allCode = self.toPlainText()
                    colNum = tc.columnNumber()
                    posNum = tc.position()

                    # ...and if there's text in the editor
                    if len(allCode.split()) > 0:
                        # There is text in the editor
                        currentLine = tc.block().text()

                        # If you're not at the end of the line just add a tab
                        if colNum < len(currentLine):
                            # If there isn't a ')' directly to the right of the cursor add a tab
                            if currentLine[colNum:colNum + 1] != ')':
                                KnobScripterTextEdit.keyPressEvent(self, event)
                                return
                            # Else show the completer
                            else:
                                completionPart = currentLine[:colNum].split(
                                    " ")[-1]
                                if "(" in completionPart:
                                    completionPart = completionPart.split(
                                        "(")[-1]

                                self.completeNukePartUnderCursor(
                                    completionPart)

                                return

                        # If you are at the end of the line,
                        else:
                            # If there's nothing to the right of you add a tab
                            if currentLine[colNum - 1:] == "" or currentLine.endswith(" "):
                                KnobScripterTextEdit.keyPressEvent(self, event)
                                return
                            # Else update completionPart and show the completer
                            completionPart = currentLine.split(" ")[-1]
                            if "(" in completionPart:
                                completionPart = completionPart.split("(")[-1]

                            self.completeNukePartUnderCursor(completionPart)
                            return

                    KnobScripterTextEdit.keyPressEvent(self, event)
            elif event.key() in [Qt.Key_Enter, Qt.Key_Return]:
                modifiers = QtWidgets.QApplication.keyboardModifiers()
                if modifiers == QtCore.Qt.ControlModifier:
                    self.runScript()
                else:
                    KnobScripterTextEdit.keyPressEvent(self, event)
            else:
                KnobScripterTextEdit.keyPressEvent(self, event)

    def getPyObjects(self, text):
        ''' Returns a list containing all the functions, classes and variables found within the selected python text (code) '''
        matches = []
        # 1: Remove text inside triple quotes (leaving the quotes)
        text_clean = '""'.join(text.split('"""')[::2])
        text_clean = '""'.join(text_clean.split("'''")[::2])

        # 2: Remove text inside of quotes (leaving the quotes) except if \"
        lines = text_clean.split("\n")
        text_clean = ""
        for line in lines:
            line_clean = '""'.join(line.split('"')[::2])
            line_clean = '""'.join(line_clean.split("'")[::2])
            line_clean = line_clean.split("#")[0]
            text_clean += line_clean + "\n"

        # 3. Split into segments (lines plus ";")
        segments = re.findall(r"[^\n;]+", text_clean)

        # 4. Go case by case.
        for s in segments:
            # Declared vars
            matches += re.findall(r"([\w\.]+)(?=[,\s\w]*=[^=]+$)", s)
            # Def functions and arguments
            function = re.findall(r"[\s]*def[\s]+([\w\.]+)[\s]*\([\s]*", s)
            if len(function):
                matches += function
                args = re.split(r"[\s]*def[\s]+([\w\.]+)[\s]*\([\s]*", s)
                if len(args) > 1:
                    args = args[-1]
                    matches += re.findall(
                        r"(?<![=\"\'])[\s]*([\w\.]+)[\s]*(?==|,|\))", args)
            # Lambda
            matches += re.findall(r"^[^#]*lambda[\s]+([\w\.]+)[\s()\w,]+", s)
            # Classes
            matches += re.findall(r"^[^#]*class[\s]+([\w\.]+)[\s()\w,]+", s)
        return matches

    # Nuke script editor's modules completer
    def completionsForcompletionPart(self, completionPart):
        def findModules(searchString):
            sysModules = sys.modules
            globalModules = globals()
            allModules = dict(sysModules, **globalModules)
            allKeys = list(set(globals().keys() + sys.modules.keys()))
            allKeysSorted = [x for x in sorted(set(allKeys))]

            if searchString == '':
                matching = []
                for x in allModules:
                    if x.startswith(searchString):
                        matching.append(x)
                return matching
            else:
                try:
                    if sys.modules.has_key(searchString):
                        return dir(sys.modules['%s' % searchString])
                    elif globals().has_key(searchString):
                        return dir(globals()['%s' % searchString])
                    else:
                        return []
                except:
                    return None

        completerText = completionPart

        # Get text before last dot
        moduleSearchString = '.'.join(completerText.split('.')[:-1])

        # Get text after last dot
        fragmentSearchString = completerText.split(
            '.')[-1] if completerText.split('.')[-1] != moduleSearchString else ''

        # Get all the modules that match module search string
        allModules = findModules(moduleSearchString)

        # If no modules found, do a dir
        if not allModules:
            if len(moduleSearchString.split('.')) == 1:
                matchedModules = []
            else:
                try:
                    trimmedModuleSearchString = '.'.join(
                        moduleSearchString.split('.')[:-1])
                    matchedModules = [x for x in dir(getattr(sys.modules[trimmedModuleSearchString], moduleSearchString.split(
                        '.')[-1])) if '__' not in x and x.startswith(fragmentSearchString)]
                except:
                    matchedModules = []
        else:
            matchedModules = [
                x for x in allModules if '__' not in x and x.startswith(fragmentSearchString)]

        selfObjects = list(set(self.getPyObjects(self.toPlainText())))
        for i in selfObjects:
            if i.startswith(completionPart):
                matchedModules.append(i)

        return matchedModules

    def completeNukePartUnderCursor(self, completionPart):

        completionPart = completionPart.lstrip().rstrip()
        completionList = self.completionsForcompletionPart(completionPart)
        if len(completionList) == 0:
            return
        self.nukeCompleter.model().setStringList(completionList)
        self.nukeCompleter.setCompletionPrefix(completionPart)

        if self.nukeCompleter.popup().isVisible():
            rect = self.cursorRect()
            rect.setWidth(self.nukeCompleter.popup().sizeHintForColumn(
                0) + self.nukeCompleter.popup().verticalScrollBar().sizeHint().width())
            self.nukeCompleter.complete(rect)
            return

        # Make it visible
        if len(completionList) == 1:
            self.insertNukeCompletion(completionList[0])
        else:
            rect = self.cursorRect()
            rect.setWidth(self.nukeCompleter.popup().sizeHintForColumn(
                0) + self.nukeCompleter.popup().verticalScrollBar().sizeHint().width())
            self.nukeCompleter.complete(rect)

        return

    def insertNukeCompletion(self, completion):
        if completion:
            completionPart = self.nukeCompleter.completionPrefix()
            if len(completionPart.split('.')) == 0:
                completionPartFragment = completionPart
            else:
                completionPartFragment = completionPart.split('.')[-1]

            textToInsert = completion[len(completionPartFragment):]
            tc = self.textCursor()
            tc.insertText(textToInsert)
        return

    def completerHighlightChanged(self, highlighted):
        self.currentNukeCompletion = highlighted

    def runScript(self):
        cursor = self.textCursor()
        nukeSEInput = self.knobScripter.nukeSEInput
        if cursor.hasSelection():
            code = cursor.selection().toPlainText()
        else:
            code = self.toPlainText()

        if code == "":
            return

        # Store original ScriptEditor status
        nukeSECursor = nukeSEInput.textCursor()
        origSelection = nukeSECursor.selectedText()
        oldAnchor = nukeSECursor.anchor()
        oldPosition = nukeSECursor.position()

        # Add the code to be executed and select it
        nukeSEInput.insertPlainText(code)

        if oldAnchor < oldPosition:
            newAnchor = oldAnchor
            newPosition = nukeSECursor.position()
        else:
            newAnchor = nukeSECursor.position()
            newPosition = oldPosition

        nukeSECursor.setPosition(newAnchor, QtGui.QTextCursor.MoveAnchor)
        nukeSECursor.setPosition(newPosition, QtGui.QTextCursor.KeepAnchor)
        nukeSEInput.setTextCursor(nukeSECursor)

        # Run the code!
        self.knobScripter.nukeSERunBtn.click()

        # Revert ScriptEditor to original
        nukeSEInput.insertPlainText(origSelection)
        nukeSECursor.setPosition(oldAnchor, QtGui.QTextCursor.MoveAnchor)
        nukeSECursor.setPosition(oldPosition, QtGui.QTextCursor.KeepAnchor)
        nukeSEInput.setTextCursor(nukeSECursor)

# ---------------------------------------------------------------------
# Preferences Panel
# ---------------------------------------------------------------------


class KnobScripterPrefs(QtWidgets.QDialog):
    def __init__(self, knobScripter):
        super(KnobScripterPrefs, self).__init__(knobScripter)

        # Vars
        self.knobScripter = knobScripter
        self.prefs_txt = self.knobScripter.prefs_txt
        self.setWindowFlags(self.windowFlags() |
                            QtCore.Qt.WindowStaysOnTopHint)
        self.oldFontSize = self.knobScripter.script_editor_font.pointSize()
        self.oldFont = self.knobScripter.script_editor_font.family()
        self.oldScheme = self.knobScripter.color_scheme
        self.font = self.oldFont
        self.oldDefaultW = self.knobScripter.windowDefaultSize[0]
        self.oldDefaultH = self.knobScripter.windowDefaultSize[1]

        # Widgets
        kspTitle = QtWidgets.QLabel("KnobScripter v" + version)
        kspTitle.setStyleSheet(
            "font-weight:bold;color:#CCCCCC;font-size:24px;")
        kspSubtitle = QtWidgets.QLabel(
            "Script editor for python and callback knobs")
        kspSubtitle.setStyleSheet("color:#999")
        kspLine = QtWidgets.QFrame()
        kspLine.setFrameShape(QtWidgets.QFrame.HLine)
        kspLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        kspLine.setLineWidth(0)
        kspLine.setMidLineWidth(1)
        kspLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        kspLineBottom = QtWidgets.QFrame()
        kspLineBottom.setFrameShape(QtWidgets.QFrame.HLine)
        kspLineBottom.setFrameShadow(QtWidgets.QFrame.Sunken)
        kspLineBottom.setLineWidth(0)
        kspLineBottom.setMidLineWidth(1)
        kspLineBottom.setFrameShadow(QtWidgets.QFrame.Sunken)
        kspSignature = QtWidgets.QLabel(
            '<a href="http://www.adrianpueyo.com/" style="color:#888;text-decoration:none"><b>adrianpueyo.com</b></a>, 2016-2019')
        kspSignature.setOpenExternalLinks(True)
        kspSignature.setStyleSheet('''color:#555;font-size:9px;''')
        kspSignature.setAlignment(QtCore.Qt.AlignRight)

        fontLabel = QtWidgets.QLabel("Font:")
        self.fontBox = QtWidgets.QFontComboBox()
        self.fontBox.setCurrentFont(QtGui.QFont(self.font))
        self.fontBox.currentFontChanged.connect(self.fontChanged)

        fontSizeLabel = QtWidgets.QLabel("Font size:")
        self.fontSizeBox = QtWidgets.QSpinBox()
        self.fontSizeBox.setValue(self.oldFontSize)
        self.fontSizeBox.setMinimum(6)
        self.fontSizeBox.setMaximum(100)
        self.fontSizeBox.valueChanged.connect(self.fontSizeChanged)

        windowWLabel = QtWidgets.QLabel("Width (px):")
        windowWLabel.setToolTip("Default window width in pixels")
        self.windowWBox = QtWidgets.QSpinBox()
        self.windowWBox.setValue(self.knobScripter.windowDefaultSize[0])
        self.windowWBox.setMinimum(200)
        self.windowWBox.setMaximum(4000)
        self.windowWBox.setToolTip("Default window width in pixels")

        windowHLabel = QtWidgets.QLabel("Height (px):")
        windowHLabel.setToolTip("Default window height in pixels")
        self.windowHBox = QtWidgets.QSpinBox()
        self.windowHBox.setValue(self.knobScripter.windowDefaultSize[1])
        self.windowHBox.setMinimum(100)
        self.windowHBox.setMaximum(2000)
        self.windowHBox.setToolTip("Default window height in pixels")

        # TODO: "Grab current dimensions" button

        tabSpaceLabel = QtWidgets.QLabel("Tab spaces:")
        tabSpaceLabel.setToolTip("Number of spaces to add with the tab key.")
        self.tabSpace2 = QtWidgets.QRadioButton("2")
        self.tabSpace4 = QtWidgets.QRadioButton("4")
        tabSpaceButtonGroup = QtWidgets.QButtonGroup(self)
        tabSpaceButtonGroup.addButton(self.tabSpace2)
        tabSpaceButtonGroup.addButton(self.tabSpace4)
        self.tabSpace2.setChecked(self.knobScripter.tabSpaces == 2)
        self.tabSpace4.setChecked(self.knobScripter.tabSpaces == 4)

        pinDefaultLabel = QtWidgets.QLabel("Always on top:")
        pinDefaultLabel.setToolTip("Default mode of the PIN toggle.")
        self.pinDefaultOn = QtWidgets.QRadioButton("On")
        self.pinDefaultOff = QtWidgets.QRadioButton("Off")
        pinDefaultButtonGroup = QtWidgets.QButtonGroup(self)
        pinDefaultButtonGroup.addButton(self.pinDefaultOn)
        pinDefaultButtonGroup.addButton(self.pinDefaultOff)
        self.pinDefaultOn.setChecked(self.knobScripter.pinned == True)
        self.pinDefaultOff.setChecked(self.knobScripter.pinned == False)
        self.pinDefaultOn.clicked.connect(lambda: self.knobScripter.pin(True))
        self.pinDefaultOff.clicked.connect(
            lambda: self.knobScripter.pin(False))

        colorSchemeLabel = QtWidgets.QLabel("Color scheme:")
        colorSchemeLabel.setToolTip("Syntax highlighting text style.")
        self.colorSchemeSublime = QtWidgets.QRadioButton("subl")
        self.colorSchemeNuke = QtWidgets.QRadioButton("nuke")
        colorSchemeButtonGroup = QtWidgets.QButtonGroup(self)
        colorSchemeButtonGroup.addButton(self.colorSchemeSublime)
        colorSchemeButtonGroup.addButton(self.colorSchemeNuke)
        colorSchemeButtonGroup.buttonClicked.connect(self.colorSchemeChanged)
        self.colorSchemeSublime.setChecked(
            self.knobScripter.color_scheme == "sublime")
        self.colorSchemeNuke.setChecked(
            self.knobScripter.color_scheme == "nuke")

        showLabelsLabel = QtWidgets.QLabel("Show labels:")
        showLabelsLabel.setToolTip(
            "Display knob labels on the knob dropdown\nOtherwise, shows the internal name only.")
        self.showLabelsOn = QtWidgets.QRadioButton("On")
        self.showLabelsOff = QtWidgets.QRadioButton("Off")
        showLabelsButtonGroup = QtWidgets.QButtonGroup(self)
        showLabelsButtonGroup.addButton(self.showLabelsOn)
        showLabelsButtonGroup.addButton(self.showLabelsOff)
        self.showLabelsOn.setChecked(self.knobScripter.pinned == True)
        self.showLabelsOff.setChecked(self.knobScripter.pinned == False)
        self.showLabelsOn.clicked.connect(lambda: self.knobScripter.pin(True))
        self.showLabelsOff.clicked.connect(
            lambda: self.knobScripter.pin(False))

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.savePrefs)
        self.buttonBox.rejected.connect(self.cancelPrefs)

        # Loaded custom values
        self.ksPrefs = self.knobScripter.loadPrefs()
        if self.ksPrefs != []:
            try:
                self.fontSizeBox.setValue(self.ksPrefs['font_size'])
                self.windowWBox.setValue(self.ksPrefs['window_default_w'])
                self.windowHBox.setValue(self.ksPrefs['window_default_h'])
                self.tabSpace2.setChecked(self.ksPrefs['tab_spaces'] == 2)
                self.tabSpace4.setChecked(self.ksPrefs['tab_spaces'] == 4)
                self.pinDefaultOn.setChecked(self.ksPrefs['pin_default'] == 1)
                self.pinDefaultOff.setChecked(self.ksPrefs['pin_default'] == 0)
                self.showLabelsOn.setChecked(self.ksPrefs['show_labels'] == 1)
                self.showLabelsOff.setChecked(self.ksPrefs['show_labels'] == 0)
                self.colorSchemeSublime.setChecked(
                    self.ksPrefs['color_scheme'] == "sublime")
                self.colorSchemeNuke.setChecked(
                    self.ksPrefs['color_scheme'] == "nuke")
            except:
                pass

        # Layouts
        font_layout = QtWidgets.QHBoxLayout()
        font_layout.addWidget(fontLabel)
        font_layout.addWidget(self.fontBox)

        fontSize_layout = QtWidgets.QHBoxLayout()
        fontSize_layout.addWidget(fontSizeLabel)
        fontSize_layout.addWidget(self.fontSizeBox)

        windowW_layout = QtWidgets.QHBoxLayout()
        windowW_layout.addWidget(windowWLabel)
        windowW_layout.addWidget(self.windowWBox)

        windowH_layout = QtWidgets.QHBoxLayout()
        windowH_layout.addWidget(windowHLabel)
        windowH_layout.addWidget(self.windowHBox)

        tabSpacesButtons_layout = QtWidgets.QHBoxLayout()
        tabSpacesButtons_layout.addWidget(self.tabSpace2)
        tabSpacesButtons_layout.addWidget(self.tabSpace4)
        tabSpaces_layout = QtWidgets.QHBoxLayout()
        tabSpaces_layout.addWidget(tabSpaceLabel)
        tabSpaces_layout.addLayout(tabSpacesButtons_layout)

        pinDefaultButtons_layout = QtWidgets.QHBoxLayout()
        pinDefaultButtons_layout.addWidget(self.pinDefaultOn)
        pinDefaultButtons_layout.addWidget(self.pinDefaultOff)
        pinDefault_layout = QtWidgets.QHBoxLayout()
        pinDefault_layout.addWidget(pinDefaultLabel)
        pinDefault_layout.addLayout(pinDefaultButtons_layout)

        showLabelsButtons_layout = QtWidgets.QHBoxLayout()
        showLabelsButtons_layout.addWidget(self.showLabelsOn)
        showLabelsButtons_layout.addWidget(self.showLabelsOff)
        showLabels_layout = QtWidgets.QHBoxLayout()
        showLabels_layout.addWidget(showLabelsLabel)
        showLabels_layout.addLayout(showLabelsButtons_layout)

        colorSchemeButtons_layout = QtWidgets.QHBoxLayout()
        colorSchemeButtons_layout.addWidget(self.colorSchemeSublime)
        colorSchemeButtons_layout.addWidget(self.colorSchemeNuke)
        colorScheme_layout = QtWidgets.QHBoxLayout()
        colorScheme_layout.addWidget(colorSchemeLabel)
        colorScheme_layout.addLayout(colorSchemeButtons_layout)

        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.addWidget(kspTitle)
        self.master_layout.addWidget(kspSignature)
        self.master_layout.addWidget(kspLine)
        self.master_layout.addLayout(font_layout)
        self.master_layout.addLayout(fontSize_layout)
        self.master_layout.addLayout(windowW_layout)
        self.master_layout.addLayout(windowH_layout)
        self.master_layout.addLayout(tabSpaces_layout)
        self.master_layout.addLayout(pinDefault_layout)
        self.master_layout.addLayout(showLabels_layout)
        self.master_layout.addLayout(colorScheme_layout)
        self.master_layout.addWidget(self.buttonBox)
        self.setLayout(self.master_layout)
        self.setFixedSize(self.minimumSize())

    def savePrefs(self):
        self.font = self.fontBox.currentFont().family()
        ks_prefs = {
            'font_size': self.fontSizeBox.value(),
            'window_default_w': self.windowWBox.value(),
            'window_default_h': self.windowHBox.value(),
            'tab_spaces': self.tabSpaceValue(),
            'pin_default': self.pinDefaultValue(),
            'show_labels': self.showLabelsValue(),
            'font': self.font,
            'color_scheme': self.colorSchemeValue(),
        }
        self.knobScripter.script_editor_font.setFamily(self.font)
        self.knobScripter.script_editor.setFont(
            self.knobScripter.script_editor_font)
        self.knobScripter.font = self.font
        self.knobScripter.color_scheme = self.colorSchemeValue()
        self.knobScripter.tabSpaces = self.tabSpaceValue()
        self.knobScripter.script_editor.tabSpaces = self.tabSpaceValue()
        with open(self.prefs_txt, "w") as f:
            prefs = json.dump(ks_prefs, f, sort_keys=True, indent=4)
        self.accept()
        self.knobScripter.highlighter.rehighlight()
        self.knobScripter.show_labels = self.showLabelsValue()
        if self.knobScripter.nodeMode:
            self.knobScripter.refreshClicked()
        return prefs

    def cancelPrefs(self):
        self.knobScripter.script_editor_font.setPointSize(self.oldFontSize)
        self.knobScripter.script_editor.setFont(
            self.knobScripter.script_editor_font)
        self.knobScripter.color_scheme = self.oldScheme
        self.knobScripter.highlighter.rehighlight()
        self.reject()

    def fontSizeChanged(self):
        self.knobScripter.script_editor_font.setPointSize(
            self.fontSizeBox.value())
        self.knobScripter.script_editor.setFont(
            self.knobScripter.script_editor_font)
        return

    def fontChanged(self):
        self.font = self.fontBox.currentFont().family()
        self.knobScripter.script_editor_font.setFamily(self.font)
        self.knobScripter.script_editor.setFont(
            self.knobScripter.script_editor_font)
        return

    def colorSchemeChanged(self):
        self.knobScripter.color_scheme = self.colorSchemeValue()
        self.knobScripter.highlighter.rehighlight()
        return

    def tabSpaceValue(self):
        return 2 if self.tabSpace2.isChecked() else 4

    def pinDefaultValue(self):
        return 1 if self.pinDefaultOn.isChecked() else 0

    def showLabelsValue(self):
        return 1 if self.showLabelsOn.isChecked() else 0

    def colorSchemeValue(self):
        return "nuke" if self.colorSchemeNuke.isChecked() else "sublime"

    def closeEvent(self, event):
        self.cancelPrefs()
        self.close()


def updateContext():
    '''
    Get the current selection of nodes with their appropriate context
    Doing this outside the KnobScripter -> forces context update inside groups when needed
    '''
    global knobScripterSelectedNodes
    knobScripterSelectedNodes = nuke.selectedNodes()
    return

# --------------------------------
# FindReplace
# --------------------------------


class FindReplaceWidget(QtWidgets.QWidget):
    ''' SearchReplace Widget for the knobscripter. FindReplaceWidget(editor = QPlainTextEdit) '''

    def __init__(self, parent):
        super(FindReplaceWidget, self).__init__(parent)

        self.editor = parent.script_editor

        self.initUI()

    def initUI(self):

        # --------------
        # Find Row
        # --------------

        # Widgets
        self.find_label = QtWidgets.QLabel("Find:")
        # self.find_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)
        self.find_label.setFixedWidth(50)
        self.find_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.find_lineEdit = QtWidgets.QLineEdit()
        self.find_next_button = QtWidgets.QPushButton("Next")
        self.find_next_button.clicked.connect(self.find)
        self.find_prev_button = QtWidgets.QPushButton("Previous")
        self.find_prev_button.clicked.connect(self.findBack)
        self.find_lineEdit.returnPressed.connect(self.find_next_button.click)

        # Layout
        self.find_layout = QtWidgets.QHBoxLayout()
        self.find_layout.addWidget(self.find_label)
        self.find_layout.addWidget(self.find_lineEdit, stretch=1)
        self.find_layout.addWidget(self.find_next_button)
        self.find_layout.addWidget(self.find_prev_button)

        # --------------
        # Replace Row
        # --------------

        # Widgets
        self.replace_label = QtWidgets.QLabel("Replace:")
        # self.replace_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)
        self.replace_label.setFixedWidth(50)
        self.replace_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.replace_lineEdit = QtWidgets.QLineEdit()
        self.replace_button = QtWidgets.QPushButton("Replace")
        self.replace_button.clicked.connect(self.replace)
        self.replace_all_button = QtWidgets.QPushButton("Replace All")
        self.replace_all_button.clicked.connect(
            lambda: self.replace(rep_all=True))
        self.replace_lineEdit.returnPressed.connect(self.replace_button.click)

        # Layout
        self.replace_layout = QtWidgets.QHBoxLayout()
        self.replace_layout.addWidget(self.replace_label)
        self.replace_layout.addWidget(self.replace_lineEdit, stretch=1)
        self.replace_layout.addWidget(self.replace_button)
        self.replace_layout.addWidget(self.replace_all_button)

        # Info text
        self.info_text = QtWidgets.QLabel("")
        self.info_text.setVisible(False)
        self.info_text.mousePressEvent = lambda x: self.info_text.setVisible(
            False)
        #f = self.info_text.font()
        # f.setItalic(True)
        # self.info_text.setFont(f)
        # self.info_text.clicked.connect(lambda:self.info_text.setVisible(False))

        # Divider line
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        line.setLineWidth(0)
        line.setMidLineWidth(1)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)

        # --------------
        # Main Layout
        # --------------

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addSpacing(4)
        self.layout.addWidget(self.info_text)
        self.layout.addLayout(self.find_layout)
        self.layout.addLayout(self.replace_layout)
        self.layout.setSpacing(4)
        try:  # >n11
            self.layout.setMargin(2)
        except:  # <n10
            self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.addSpacing(4)
        self.layout.addWidget(line)
        self.setLayout(self.layout)
        self.setTabOrder(self.find_lineEdit, self.replace_lineEdit)
        # self.adjustSize()
        # self.setMaximumHeight(180)

    def find(self, find_str="", match_case=True):
        if find_str == "":
            find_str = self.find_lineEdit.text()

        matches = self.editor.toPlainText().count(find_str)
        if not matches or matches == 0:
            self.info_text.setText("              No more matches.")
            self.info_text.setVisible(True)
            return
        else:
            self.info_text.setVisible(False)

        # Beginning of undo block
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()

        # Use flags for case match
        flags = QtGui.QTextDocument.FindFlags()
        if match_case:
            flags = flags | QtGui.QTextDocument.FindCaseSensitively

        # Find next
        r = self.editor.find(find_str, flags)

        cursor.endEditBlock()

        self.editor.setFocus()
        self.editor.show()
        return r

    def findBack(self, find_str="", match_case=True):
        if find_str == "":
            find_str = self.find_lineEdit.text()

        matches = self.editor.toPlainText().count(find_str)
        if not matches or matches == 0:
            self.info_text.setText("              No more matches.")
            self.info_text.setVisible(True)
            return
        else:
            self.info_text.setVisible(False)

        # Beginning of undo block
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()

        # Use flags for case match
        flags = QtGui.QTextDocument.FindFlags()
        flags = flags | QtGui.QTextDocument.FindBackward
        if match_case:
            flags = flags | QtGui.QTextDocument.FindCaseSensitively

        # Find prev
        r = self.editor.find(find_str, flags)
        cursor.endEditBlock()
        self.editor.setFocus()
        return r

    def replace(self, find_str="", rep_str="", rep_all=False):
        if find_str == "":
            find_str = self.find_lineEdit.text()
        if rep_str == "":
            rep_str = self.replace_lineEdit.text()

        matches = self.editor.toPlainText().count(find_str)
        if not matches or matches == 0:
            self.info_text.setText("              No more matches.")
            self.info_text.setVisible(True)
            return
        else:
            self.info_text.setVisible(False)

        # Beginning of undo block
        cursor = self.editor.textCursor()
        cursor_orig_pos = cursor.position()
        cursor.beginEditBlock()

        # Use flags for case match
        flags = QtGui.QTextDocument.FindFlags()
        flags = flags | QtGui.QTextDocument.FindCaseSensitively

        if rep_all == True:
            cursor.movePosition(QtGui.QTextCursor.Start)
            self.editor.setTextCursor(cursor)
            cursor = self.editor.textCursor()
            rep_count = 0
            while True:
                if not cursor.hasSelection() or cursor.selectedText() != find_str:
                    self.editor.find(find_str, flags)  # Find next
                    cursor = self.editor.textCursor()
                    if not cursor.hasSelection():
                        break
                else:
                    cursor.insertText(rep_str)
                    rep_count += 1
            self.info_text.setText(
                "              Replaced " + str(rep_count) + " matches.")
            self.info_text.setVisible(True)
        else:  # If not "find all"
            if not cursor.hasSelection() or cursor.selectedText() != find_str:
                self.editor.find(find_str, flags)  # Find next
                if not cursor.hasSelection() and matches > 0:  # If not found but there are matches, start over
                    cursor.movePosition(QtGui.QTextCursor.Start)
                    self.editor.setTextCursor(cursor)
                    self.editor.find(find_str, flags)
            else:
                cursor.insertText(rep_str)
                self.editor.find(
                    rep_str, flags | QtGui.QTextDocument.FindBackward)

        cursor.endEditBlock()
        self.replace_lineEdit.setFocus()
        return


# --------------------------------
# Snippets
# --------------------------------
class SnippetsPanel(QtWidgets.QDialog):
    def __init__(self, parent):
        super(SnippetsPanel, self).__init__(parent)

        self.knobScripter = parent

        self.setWindowFlags(self.windowFlags() |
                            QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Snippet editor")

        self.snippets_txt_path = self.knobScripter.snippets_txt_path
        self.snippets_dict = self.loadSnippetsDict(path=self.snippets_txt_path)
        #self.snippets_dict = snippets_dic

        # self.saveSnippets(snippets_dic)

        self.initUI()
        self.resize(500, 300)

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        # First Area (Titles)
        title_layout = QtWidgets.QHBoxLayout()
        shortcuts_label = QtWidgets.QLabel("Shortcut")
        code_label = QtWidgets.QLabel("Code snippet")
        title_layout.addWidget(shortcuts_label, stretch=1)
        title_layout.addWidget(code_label, stretch=2)
        self.layout.addLayout(title_layout)

        # Main Scroll area
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()

        self.buildSnippetWidgets()

        self.scroll_content.setLayout(self.scroll_layout)

        # Scroll Area Properties
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)

        self.layout.addWidget(self.scroll)

        # File knob test
        #self.filePath_lineEdit = SnippetFilePath(self)
        # self.filePath_lineEdit
        # self.layout.addWidget(self.filePath_lineEdit)

        # Lower buttons
        self.bottom_layout = QtWidgets.QHBoxLayout()

        self.add_btn = QtWidgets.QPushButton("Add snippet")
        self.add_btn.setToolTip("Create empty fields for an extra snippet.")
        self.add_btn.clicked.connect(self.addSnippet)
        self.bottom_layout.addWidget(self.add_btn)

        self.addPath_btn = QtWidgets.QPushButton("Add custom path")
        self.addPath_btn.setToolTip(
            "Add a custom path to an external snippets .txt file.")
        self.addPath_btn.clicked.connect(self.addCustomPath)
        self.bottom_layout.addWidget(self.addPath_btn)

        self.bottom_layout.addStretch()

        self.save_btn = QtWidgets.QPushButton('OK')
        self.save_btn.setToolTip(
            "Save the snippets into a json file and close the panel.")
        self.save_btn.clicked.connect(self.okPressed)
        self.bottom_layout.addWidget(self.save_btn)

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setToolTip("Cancel any new snippets or modifications.")
        self.cancel_btn.clicked.connect(self.close)
        self.bottom_layout.addWidget(self.cancel_btn)

        self.apply_btn = QtWidgets.QPushButton('Apply')
        self.apply_btn.setToolTip("Save the snippets into a json file.")
        self.apply_btn.setShortcut('Ctrl+S')
        self.apply_btn.clicked.connect(self.applySnippets)
        self.bottom_layout.addWidget(self.apply_btn)

        self.help_btn = QtWidgets.QPushButton('Help')
        self.help_btn.setShortcut('F1')
        self.help_btn.clicked.connect(self.showHelp)
        self.bottom_layout.addWidget(self.help_btn)

        self.layout.addLayout(self.bottom_layout)

        self.setLayout(self.layout)

    def reload(self):
        '''
        Clears everything without saving and redoes the widgets etc.
        Only to be called if the panel isn't shown meaning it's closed.
        '''
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.itemAt(i).widget().deleteLater()

        self.snippets_dict = self.loadSnippetsDict(path=self.snippets_txt_path)

        self.buildSnippetWidgets()

    def buildSnippetWidgets(self):
        for i, (key, val) in enumerate(self.snippets_dict.items()):
            if re.match(r"\[custom-path-[0-9]+\]$", key):
                file_edit = SnippetFilePath(val)
                self.scroll_layout.insertWidget(-1, file_edit)
            else:
                snippet_edit = SnippetEdit(key, val, parent=self)
                self.scroll_layout.insertWidget(-1, snippet_edit)

    def loadSnippetsDict(self, path=""):
        ''' Load prefs. TO REMOVE '''
        if path == "":
            path = self.knobScripter.snippets_txt_path
        if not os.path.isfile(self.snippets_txt_path):
            return {}
        else:
            with open(self.snippets_txt_path, "r") as f:
                self.snippets = json.load(f)
                return self.snippets

    def getSnippetsAsDict(self):
        dic = {}
        num_snippets = self.scroll_layout.count()
        path_i = 1
        for s in range(num_snippets):
            se = self.scroll_layout.itemAt(s).widget()
            if se.__class__.__name__ == "SnippetEdit":
                key = se.shortcut_editor.text()
                val = se.script_editor.toPlainText()
                if key != "":
                    dic[key] = val
            else:
                path = se.filepath_lineEdit.text()
                if path != "":
                    dic["[custom-path-{}]".format(str(path_i))] = path
                    path_i += 1
        return dic

    def saveSnippets(self, snippets=""):
        if snippets == "":
            snippets = self.getSnippetsAsDict()
        with open(self.snippets_txt_path, "w") as f:
            prefs = json.dump(snippets, f, sort_keys=True, indent=4)
        return prefs

    def applySnippets(self):
        self.saveSnippets()
        self.knobScripter.snippets = self.knobScripter.loadSnippets(maxDepth=5)
        self.knobScripter.loadSnippets()

    def okPressed(self):
        self.applySnippets()
        self.accept()

    def addSnippet(self, key="", val=""):
        se = SnippetEdit(key, val, parent=self)
        self.scroll_layout.insertWidget(0, se)
        self.show()
        return se

    def addCustomPath(self, path=""):
        cpe = SnippetFilePath(path)
        self.scroll_layout.insertWidget(0, cpe)
        self.show()
        cpe.browseSnippets()
        return cpe

    def showHelp(self):
        ''' Create a new snippet, auto-completed with the help '''
        help_key = "help"
        help_val = """Snippets are a convenient way to have code blocks that you can call through a shortcut.\n\n1. Simply write a shortcut on the text input field on the left. You can see this one is set to "test".\n\n2. Then, write a code or whatever in this script editor. You can include $$ as the placeholder for where you'll want the mouse cursor to appear.\n\n3. Finally, click OK or Apply to save the snippets. On the main script editor, you'll be able to call any snippet by writing the shortcut (in this example: help) and pressing the Tab key.\n\nIn order to remove a snippet, simply leave the shortcut and contents blank, and save the snippets."""
        help_se = self.addSnippet(help_key, help_val)
        help_se.script_editor.resize(160, 160)


class SnippetEdit(QtWidgets.QWidget):
    ''' Simple widget containing two fields, for the snippet shortcut and content '''

    def __init__(self, key="", val="", parent=None):
        super(SnippetEdit, self).__init__(parent)

        self.knobScripter = parent.knobScripter
        self.color_scheme = self.knobScripter.color_scheme
        self.layout = QtWidgets.QHBoxLayout()

        self.shortcut_editor = QtWidgets.QLineEdit(self)
        f = self.shortcut_editor.font()
        f.setWeight(QtGui.QFont.Bold)
        self.shortcut_editor.setFont(f)
        self.shortcut_editor.setText(str(key))
        #self.script_editor = QtWidgets.QTextEdit(self)
        self.script_editor = KnobScripterTextEdit()
        self.script_editor.setMinimumHeight(100)
        self.script_editor.setStyleSheet(
            'background:#282828;color:#EEE;')  # Main Colors
        self.highlighter = KSScriptEditorHighlighter(
            self.script_editor.document(), self)
        self.script_editor_font = self.knobScripter.script_editor_font
        self.script_editor.setFont(self.script_editor_font)
        self.script_editor.resize(90, 90)
        self.script_editor.setPlainText(str(val))
        self.layout.addWidget(self.shortcut_editor,
                              stretch=1, alignment=Qt.AlignTop)
        self.layout.addWidget(self.script_editor, stretch=2)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)


class SnippetFilePath(QtWidgets.QWidget):
    ''' Simple widget containing a filepath lineEdit and a button to open the file browser '''

    def __init__(self, path="", parent=None):
        super(SnippetFilePath, self).__init__(parent)

        self.layout = QtWidgets.QHBoxLayout()

        self.custompath_label = QtWidgets.QLabel(self)
        self.custompath_label.setText("Custom path: ")

        self.filepath_lineEdit = QtWidgets.QLineEdit(self)
        self.filepath_lineEdit.setText(str(path))
        #self.script_editor = QtWidgets.QTextEdit(self)
        self.filepath_lineEdit.setStyleSheet(
            'background:#282828;color:#EEE;')  # Main Colors
        self.script_editor_font = QtGui.QFont()
        self.script_editor_font.setFamily("Courier")
        self.script_editor_font.setStyleHint(QtGui.QFont.Monospace)
        self.script_editor_font.setFixedPitch(True)
        self.script_editor_font.setPointSize(11)
        self.filepath_lineEdit.setFont(self.script_editor_font)

        self.file_button = QtWidgets.QPushButton(self)
        self.file_button.setText("Browse...")
        self.file_button.clicked.connect(self.browseSnippets)

        self.layout.addWidget(self.custompath_label)
        self.layout.addWidget(self.filepath_lineEdit)
        self.layout.addWidget(self.file_button)
        self.layout.setContentsMargins(0, 10, 0, 10)

        self.setLayout(self.layout)

    def browseSnippets(self):
        ''' Opens file panel for ...snippets.txt '''
        browseLocation = nuke.getFilename('Select snippets file', '*.txt')

        if not browseLocation:
            return

        self.filepath_lineEdit.setText(browseLocation)
        return


# --------------------------------
# Implementation
# --------------------------------

def showKnobScripter(knob="knobChanged"):
    selection = nuke.selectedNodes()
    if not len(selection):
        pan = KnobScripter()
    else:
        pan = KnobScripter(selection[0], knob)
    pan.show()


def addKnobScripterPanel():
    global knobScripterPanel
    try:
        knobScripterPanel = panels.registerWidgetAsPanel('nuke.KnobScripterPane', 'Knob Scripter',
                                                         'com.adrianpueyo.KnobScripterPane')
        knobScripterPanel.addToPane(nuke.getPaneFor('Properties.1'))

    except:
        knobScripterPanel = panels.registerWidgetAsPanel(
            'nuke.KnobScripterPane', 'Knob Scripter', 'com.adrianpueyo.KnobScripterPane')


nuke.KnobScripterPane = KnobScripterPane
log("KS LOADED")
ksShortcut = "alt+z"
addKnobScripterPanel()
nuke.menu('Nuke').addCommand(
    'Edit/Node/Open Floating Knob Scripter', showKnobScripter, ksShortcut)
nuke.menu('Nuke').addCommand('Edit/Node/Update KnobScripter Context',
                             updateContext).setVisible(False)
