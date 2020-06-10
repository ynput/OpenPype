"""Main Window

States:
    These are all possible states and their transitions.


      reset
        '
        '
        '
     ___v__
    |      |       reset
    | Idle |--------------------.
    |      |<-------------------'
    |      |
    |      |                   _____________
    |      |     validate     |             |    reset     # TODO
    |      |----------------->| In-progress |-----------.
    |      |                  |_____________|           '
    |      |<-------------------------------------------'
    |      |
    |      |                   _____________
    |      |      publish     |             |
    |      |----------------->| In-progress |---.
    |      |                  |_____________|   '
    |      |<-----------------------------------'
    |______|


Todo:
    There are notes spread throughout this project with the syntax:

    - TODO(username)

    The `username` is a quick and dirty indicator of who made the note
    and is by no means exclusive to that person in terms of seeing it
    done. Feel free to do, or make your own TODO's as you code. Just
    make sure the description is sufficient for anyone reading it for
    the first time to understand how to actually to it!

"""
from functools import partial

from . import delegate, model, settings, util, view, widgets
from .awesome import tags as awesome

from .vendor.Qt import QtCore, QtGui, QtWidgets
from .constants import (
    PluginStates, PluginActionStates, InstanceStates, GroupStates, Roles
)


class Window(QtWidgets.QDialog):
    def __init__(self, controller, parent=None):
        super(Window, self).__init__(parent=parent)

        # Use plastique style for specific ocations
        # TODO set style name via environment variable
        low_keys = {
            key.lower(): key
            for key in QtWidgets.QStyleFactory.keys()
        }
        if "plastique" in low_keys:
            self.setStyle(
                QtWidgets.QStyleFactory.create(low_keys["plastique"])
            )

        icon = QtGui.QIcon(util.get_asset("img", "logo-extrasmall.png"))
        if parent is None:
            on_top_flag = QtCore.Qt.WindowStaysOnTopHint
        else:
            on_top_flag = QtCore.Qt.Dialog

        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMaximizeButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
            | on_top_flag
        )
        self.setWindowIcon(icon)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.controller = controller

        main_widget = QtWidgets.QWidget(self)

        # General layout
        header_widget = QtWidgets.QWidget(parent=main_widget)

        header_tab_widget = QtWidgets.QWidget(header_widget)
        header_tab_artist = QtWidgets.QRadioButton(header_tab_widget)
        header_tab_overview = QtWidgets.QRadioButton(header_tab_widget)
        header_tab_terminal = QtWidgets.QRadioButton(header_tab_widget)
        header_spacer = QtWidgets.QWidget(header_tab_widget)

        header_aditional_btns = QtWidgets.QWidget(header_tab_widget)

        aditional_btns_layout = QtWidgets.QHBoxLayout(header_aditional_btns)

        presets_button = widgets.ButtonWithMenu(awesome["filter"])
        presets_button.setEnabled(False)
        aditional_btns_layout.addWidget(presets_button)

        layout_tab = QtWidgets.QHBoxLayout(header_tab_widget)
        layout_tab.setContentsMargins(0, 0, 0, 0)
        layout_tab.setSpacing(0)
        layout_tab.addWidget(header_tab_artist, 0)
        layout_tab.addWidget(header_tab_overview, 0)
        layout_tab.addWidget(header_tab_terminal, 0)
        # Compress items to the left
        layout_tab.addWidget(header_spacer, 1)
        layout_tab.addWidget(header_aditional_btns, 1)

        layout = QtWidgets.QHBoxLayout(header_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header_tab_widget)

        header_widget.setLayout(layout)

        # Artist Page
        instance_model = model.InstanceModel(controller)

        artist_page = QtWidgets.QWidget()

        artist_view = view.ArtistView()
        artist_view.show_perspective.connect(self.toggle_perspective_widget)
        artist_proxy = model.ArtistProxy()
        artist_proxy.setSourceModel(instance_model)
        artist_view.setModel(artist_proxy)

        artist_delegate = delegate.ArtistDelegate()
        artist_view.setItemDelegate(artist_delegate)

        layout = QtWidgets.QVBoxLayout(artist_page)
        layout.addWidget(artist_view)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        artist_page.setLayout(layout)

        # Overview Page
        # TODO add parent
        overview_page = QtWidgets.QWidget()

        overview_instance_view = view.OverviewView(parent=overview_page)
        overview_instance_delegate = delegate.InstanceDelegate(
            parent=overview_instance_view
        )
        overview_instance_view.setItemDelegate(overview_instance_delegate)
        overview_instance_view.setModel(instance_model)

        overview_plugin_view = view.OverviewView(parent=overview_page)
        overview_plugin_delegate = delegate.PluginDelegate(
            parent=overview_plugin_view
        )
        overview_plugin_view.setItemDelegate(overview_plugin_delegate)
        plugin_model = model.PluginModel(controller)
        plugin_proxy = model.PluginFilterProxy()
        plugin_proxy.setSourceModel(plugin_model)
        overview_plugin_view.setModel(plugin_proxy)

        layout = QtWidgets.QHBoxLayout(overview_page)
        layout.addWidget(overview_instance_view, 1)
        layout.addWidget(overview_plugin_view, 1)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        overview_page.setLayout(layout)

        # Terminal
        terminal_container = QtWidgets.QWidget()

        terminal_view = view.TerminalView()
        terminal_model = model.TerminalModel()
        terminal_proxy = model.TerminalProxy(terminal_view)
        terminal_proxy.setSourceModel(terminal_model)

        terminal_view.setModel(terminal_proxy)
        terminal_delegate = delegate.TerminalItem()
        terminal_view.setItemDelegate(terminal_delegate)

        layout = QtWidgets.QVBoxLayout(terminal_container)
        layout.addWidget(terminal_view)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        terminal_container.setLayout(layout)

        terminal_page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(terminal_page)
        layout.addWidget(terminal_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add some room between window borders and contents
        body_widget = QtWidgets.QWidget(main_widget)
        layout = QtWidgets.QHBoxLayout(body_widget)
        layout.setContentsMargins(5, 5, 5, 1)
        layout.addWidget(artist_page)
        layout.addWidget(overview_page)
        layout.addWidget(terminal_page)

        # Comment Box
        comment_box = widgets.CommentBox("Comment...", self)

        intent_box = QtWidgets.QComboBox()

        intent_model = model.IntentModel()
        intent_box.setModel(intent_model)
        intent_box.currentIndexChanged.connect(self.on_intent_changed)

        comment_intent_widget = QtWidgets.QWidget()
        comment_intent_layout = QtWidgets.QHBoxLayout(comment_intent_widget)
        comment_intent_layout.setContentsMargins(0, 0, 0, 0)
        comment_intent_layout.setSpacing(5)
        comment_intent_layout.addWidget(comment_box)
        comment_intent_layout.addWidget(intent_box)

        # Terminal filtering
        terminal_filters_widget = widgets.TerminalFilterWidget()

        # Footer
        footer_widget = QtWidgets.QWidget(main_widget)

        footer_info = QtWidgets.QLabel(footer_widget)
        footer_spacer = QtWidgets.QWidget(footer_widget)
        footer_button_reset = QtWidgets.QPushButton(
            awesome["refresh"], footer_widget
        )
        footer_button_validate = QtWidgets.QPushButton(
            awesome["flask"], footer_widget
        )
        footer_button_play = QtWidgets.QPushButton(
            awesome["play"], footer_widget
        )
        footer_button_stop = QtWidgets.QPushButton(
            awesome["stop"], footer_widget
        )

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(footer_info, 0)
        layout.addWidget(footer_spacer, 1)
        layout.addWidget(footer_button_stop, 0)
        layout.addWidget(footer_button_reset, 0)
        layout.addWidget(footer_button_validate, 0)
        layout.addWidget(footer_button_play, 0)

        footer_layout = QtWidgets.QVBoxLayout(footer_widget)
        footer_layout.addWidget(comment_intent_widget)
        footer_layout.addLayout(layout)

        footer_widget.setProperty("success", -1)

        # Placeholder for when GUI is closing
        # TODO(marcus): Fade to black and the the user about what's happening
        closing_placeholder = QtWidgets.QWidget(main_widget)
        closing_placeholder.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        closing_placeholder.hide()

        perspective_widget = widgets.PerspectiveWidget(self)
        perspective_widget.hide()

        # Main layout
        layout = QtWidgets.QVBoxLayout(main_widget)
        layout.addWidget(header_widget, 0)
        layout.addWidget(body_widget, 3)
        layout.addWidget(perspective_widget, 3)
        layout.addWidget(closing_placeholder, 1)
        layout.addWidget(terminal_filters_widget, 0)
        layout.addWidget(footer_widget, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        main_widget.setLayout(layout)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(main_widget)

        # Display info
        info_effect = QtWidgets.QGraphicsOpacityEffect(footer_info)
        footer_info.setGraphicsEffect(info_effect)

        on = QtCore.QPropertyAnimation(info_effect, b"opacity")
        on.setDuration(0)
        on.setStartValue(0)
        on.setEndValue(1)

        off = QtCore.QPropertyAnimation(info_effect, b"opacity")
        off.setDuration(0)
        off.setStartValue(1)
        off.setEndValue(0)

        fade = QtCore.QPropertyAnimation(info_effect, b"opacity")
        fade.setDuration(500)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)

        animation_info_msg = QtCore.QSequentialAnimationGroup()
        animation_info_msg.addAnimation(on)
        animation_info_msg.addPause(50)
        animation_info_msg.addAnimation(off)
        animation_info_msg.addPause(50)
        animation_info_msg.addAnimation(on)
        animation_info_msg.addPause(2000)
        animation_info_msg.addAnimation(fade)

        """Setup

        Widgets are referred to in CSS via their object-name. We
        use the same mechanism internally to refer to objects; so rather
        than storing widgets as self.my_widget, it is referred to as:

        >>> my_widget = self.findChild(QtWidgets.QWidget, "MyWidget")

        This way there is only ever a single method of referring to any widget.
        """

        names = {
            # Main
            "Header": header_widget,
            "Body": body_widget,
            "Footer": footer_widget,

            # Pages
            "Artist": artist_page,
            "Overview": overview_page,
            "Terminal": terminal_page,

            # Tabs
            "ArtistTab": header_tab_artist,
            "OverviewTab": header_tab_overview,
            "TerminalTab": header_tab_terminal,

            # Views
            "TerminalView": terminal_view,

            # Buttons
            "Play": footer_button_play,
            "Validate": footer_button_validate,
            "Reset": footer_button_reset,
            "Stop": footer_button_stop,

            # Misc
            "HeaderSpacer": header_spacer,
            "FooterSpacer": footer_spacer,
            "FooterInfo": footer_info,
            "CommentIntentWidget": comment_intent_widget,
            "CommentBox": comment_box,
            "CommentPlaceholder": comment_box.placeholder,
            "ClosingPlaceholder": closing_placeholder,
            "IntentBox": intent_box
        }

        for name, _widget in names.items():
            _widget.setObjectName(name)

        # Enable CSS on plain QWidget objects
        for _widget in (
            header_widget,
            body_widget,
            artist_page,
            comment_box,
            overview_page,
            terminal_page,
            footer_widget,
            footer_button_play,
            footer_button_validate,
            footer_button_stop,
            footer_button_reset,
            footer_spacer,
            closing_placeholder
        ):
            _widget.setAttribute(QtCore.Qt.WA_StyledBackground)

        # Signals
        header_tab_artist.toggled.connect(
            lambda: self.on_tab_changed("artist")
        )
        header_tab_overview.toggled.connect(
            lambda: self.on_tab_changed("overview")
        )
        header_tab_terminal.toggled.connect(
            lambda: self.on_tab_changed("terminal")
        )

        overview_instance_view.show_perspective.connect(
            self.toggle_perspective_widget
        )
        overview_plugin_view.show_perspective.connect(
            self.toggle_perspective_widget
        )

        controller.switch_toggleability.connect(self.change_toggleability)

        controller.was_reset.connect(self.on_was_reset)
        # This is called synchronously on each process
        controller.was_processed.connect(self.on_was_processed)
        controller.passed_group.connect(self.on_passed_group)
        controller.was_stopped.connect(self.on_was_stopped)
        controller.was_finished.connect(self.on_was_finished)

        controller.was_skipped.connect(self.on_was_skipped)
        controller.was_acted.connect(self.on_was_acted)

        # NOTE: Listeners to this signal are run in the main thread
        controller.about_to_process.connect(
            self.on_about_to_process,
            QtCore.Qt.DirectConnection
        )

        artist_view.toggled.connect(self.on_item_toggled)
        overview_instance_view.toggled.connect(self.on_item_toggled)
        overview_plugin_view.toggled.connect(self.on_item_toggled)

        footer_button_stop.clicked.connect(self.on_stop_clicked)
        footer_button_reset.clicked.connect(self.on_reset_clicked)
        footer_button_validate.clicked.connect(self.on_validate_clicked)
        footer_button_play.clicked.connect(self.on_play_clicked)

        comment_box.textChanged.connect(self.on_comment_entered)
        comment_box.returnPressed.connect(self.on_play_clicked)
        overview_plugin_view.customContextMenuRequested.connect(
            self.on_plugin_action_menu_requested
        )

        instance_model.group_created.connect(
            overview_instance_view.expand
        )

        self.main_widget = main_widget

        self.header_widget = header_widget
        self.body_widget = body_widget

        self.terminal_filters_widget = terminal_filters_widget

        self.footer_widget = footer_widget
        self.footer_button_reset = footer_button_reset
        self.footer_button_validate = footer_button_validate
        self.footer_button_play = footer_button_play
        self.footer_button_stop = footer_button_stop

        self.overview_instance_view = overview_instance_view
        self.overview_plugin_view = overview_plugin_view
        self.plugin_model = plugin_model
        self.plugin_proxy = plugin_proxy
        self.instance_model = instance_model

        self.artist_proxy = artist_proxy
        self.artist_view = artist_view

        self.presets_button = presets_button

        self.animation_info_msg = animation_info_msg

        self.terminal_model = terminal_model
        self.terminal_proxy = terminal_proxy
        self.terminal_view = terminal_view

        self.comment_main_widget = comment_intent_widget
        self.comment_box = comment_box
        self.intent_box = intent_box
        self.intent_model = intent_model

        self.perspective_widget = perspective_widget

        self.tabs = {
            "artist": header_tab_artist,
            "overview": header_tab_overview,
            "terminal": header_tab_terminal
        }
        self.pages = {
            "artist": artist_page,
            "overview": overview_page,
            "terminal": terminal_page
        }

        current_page = settings.InitialTab or "artist"
        self.state = {
            "is_closing": False,
            "current_page": current_page
        }

        self.tabs[current_page].setChecked(True)

    # -------------------------------------------------------------------------
    #
    # Event handlers
    #
    # -------------------------------------------------------------------------
    def set_presets(self, key):
        plugin_settings = self.controller.possible_presets.get(key)
        if not plugin_settings:
            return

        for plugin_item in self.plugin_model.plugin_items.values():
            if not plugin_item.plugin.optional:
                continue

            value = plugin_settings.get(
                plugin_item.plugin.__name__,
                # if plugin is not in presets then set default value
                self.controller.optional_default.get(
                    plugin_item.plugin.__name__
                )
            )
            if value is None:
                continue

            plugin_item.setData(value, QtCore.Qt.CheckStateRole)

    def toggle_perspective_widget(self, index=None):
        show = False
        if index:
            show = True
            self.perspective_widget.set_context(index)

        self.body_widget.setVisible(not show)
        self.header_widget.setVisible(not show)

        self.perspective_widget.setVisible(show)
        self.terminal_filters_widget.setVisible(show)

    def change_toggleability(self, enable_value):
        for plugin_item in self.plugin_model.plugin_items.values():
            plugin_item.setData(enable_value, Roles.IsEnabledRole)

        for instance_item in (
            self.instance_model.instance_items.values()
        ):
            instance_item.setData(enable_value, Roles.IsEnabledRole)

    def on_item_toggled(self, index, state=None):
        """An item is requesting to be toggled"""
        if not index.data(Roles.IsOptionalRole):
            return self.info("This item is mandatory")

        if self.controller.collect_state != 1:
            return self.info("Cannot toggle")

        if state is None:
            state = not index.data(QtCore.Qt.CheckStateRole)

        index.model().setData(index, state, QtCore.Qt.CheckStateRole)
        self.update_compatibility()

    def on_tab_changed(self, target):
        self.comment_main_widget.setVisible(not target == "terminal")
        self.terminal_filters_widget.setVisible(target == "terminal")

        for name, page in self.pages.items():
            if name != target:
                page.hide()

        self.pages[target].show()

        self.state["current_page"] = target

    def on_validate_clicked(self):
        self.comment_box.setEnabled(False)
        self.intent_box.setEnabled(False)

        self.validate()

    def on_play_clicked(self):
        self.comment_box.setEnabled(False)
        self.intent_box.setEnabled(False)

        self.publish()

    def on_reset_clicked(self):
        self.reset()

    def on_stop_clicked(self):
        self.info("Stopping..")
        self.controller.stop()

        # TODO checks
        self.footer_button_reset.setEnabled(True)
        self.footer_button_play.setEnabled(False)
        self.footer_button_stop.setEnabled(False)

    def on_comment_entered(self):
        """The user has typed a comment."""
        self.controller.context.data["comment"] = self.comment_box.text()

    def on_intent_changed(self):
        idx = self.intent_model.index(self.intent_box.currentIndex(), 0)
        intent_value = self.intent_model.data(idx, Roles.IntentItemValue)
        intent_label = self.intent_model.data(idx, QtCore.Qt.DisplayRole)

        # TODO move to play
        if self.controller.context:
            self.controller.context.data["intent"] = {
                "value": intent_value,
                "label": intent_label
            }

    def on_about_to_process(self, plugin, instance):
        """Reflect currently running pair in GUI"""
        if instance is None:
            instance_id = self.controller.context.id
        else:
            instance_id = instance.id

        instance_item = (
            self.instance_model.instance_items[instance_id]
        )
        instance_item.setData(
            {InstanceStates.InProgress: True},
            Roles.PublishFlagsRole
        )

        plugin_item = self.plugin_model.plugin_items[plugin._id]
        plugin_item.setData(
            {PluginStates.InProgress: True},
            Roles.PublishFlagsRole
        )

        self.info("{} {}".format(
            self.tr("Processing"), plugin_item.data(QtCore.Qt.DisplayRole)
        ))

    def on_plugin_action_menu_requested(self, pos):
        """The user right-clicked on a plug-in
         __________
        |          |
        | Action 1 |
        | Action 2 |
        | Action 3 |
        |          |
        |__________|

        """

        index = self.overview_plugin_view.indexAt(pos)
        actions = index.data(Roles.PluginValidActionsRole)

        if not actions:
            return

        menu = QtWidgets.QMenu(self)
        plugin_id = index.data(Roles.ObjectIdRole)
        plugin_item = self.plugin_model.plugin_items[plugin_id]
        print("plugin is: %s" % plugin_item.plugin)

        for action in actions:
            qaction = QtWidgets.QAction(action.label or action.__name__, self)
            qaction.triggered.connect(partial(self.act, plugin_item, action))
            menu.addAction(qaction)

        menu.popup(self.overview_plugin_view.viewport().mapToGlobal(pos))

    def update_compatibility(self):
        self.plugin_model.update_compatibility()
        self.plugin_proxy.invalidateFilter()

    def on_was_reset(self):
        # Append context object to instances model
        self.instance_model.append(self.controller.context)

        for plugin in self.controller.plugins:
            self.plugin_model.append(plugin)

        self.overview_instance_view.expandAll()
        self.overview_plugin_view.expandAll()

        self.presets_button.clearMenu()
        if self.controller.possible_presets:
            self.presets_button.setEnabled(True)
            for key in self.controller.possible_presets:
                self.presets_button.addItem(
                    key, partial(self.set_presets, key)
                )

        self.instance_model.restore_checkstates()
        self.plugin_model.restore_checkstates()

        self.perspective_widget.reset()

        # Append placeholder comment from Context
        # This allows users to inject a comment from elsewhere,
        # or to perhaps provide a placeholder comment/template
        # for artists to fill in.
        comment = self.controller.context.data.get("comment")
        self.comment_box.setText(comment or None)
        self.comment_box.setEnabled(True)

        if self.intent_model.has_items:
            self.on_intent_changed()
        self.intent_box.setEnabled(True)

        # Refresh tab
        self.on_tab_changed(self.state["current_page"])
        self.update_compatibility()

        self.footer_button_validate.setEnabled(True)
        self.footer_button_reset.setEnabled(True)
        self.footer_button_stop.setEnabled(False)
        self.footer_button_play.setEnabled(True)
        self.footer_button_play.setFocus()

    def on_passed_group(self, order):

        for group_item in self.instance_model.group_items.values():
            if self.overview_instance_view.isExpanded(group_item.index()):
                continue

            if group_item.publish_states & GroupStates.HasError:
                self.overview_instance_view.expand(group_item.index())

        for group_item in self.plugin_model.group_items.values():
            # TODO check only plugins from the group
            if (
                group_item.publish_states & GroupStates.HasFinished
                or (order is not None and group_item.order >= order)
            ):
                continue

            if group_item.publish_states & GroupStates.HasError:
                self.overview_plugin_view.expand(
                    self.plugin_proxy.mapFromSource(group_item.index())
                )
                continue

            group_item.setData(
                {GroupStates.HasFinished: True},
                Roles.PublishFlagsRole
            )
            self.overview_plugin_view.collapse(
                self.plugin_proxy.mapFromSource(group_item.index())
            )

    def on_was_stopped(self):
        errored = self.controller.errored
        self.footer_button_play.setEnabled(not errored)
        self.footer_button_validate.setEnabled(
            not errored and not self.controller.validated
        )
        self.footer_button_reset.setEnabled(True)
        self.footer_button_stop.setEnabled(False)
        if errored:
            self.footer_widget.setProperty("success", 0)
            self.footer_widget.style().polish(self.footer_widget)

    def on_was_skipped(self, plugin):
        plugin_item = self.plugin_model.plugin_items[plugin.id]
        plugin_item.setData(
            {PluginStates.WasSkipped: True},
            Roles.PublishFlagsRole
        )

    def on_was_finished(self):
        self.footer_button_play.setEnabled(False)
        self.footer_button_validate.setEnabled(False)
        self.footer_button_reset.setEnabled(True)
        self.footer_button_stop.setEnabled(False)

        if self.controller.errored:
            success_val = 0
            self.info(self.tr("Stopped due to error(s), see Terminal."))
            self.comment_box.setEnabled(False)
            self.intent_box.setEnabled(False)

        else:
            success_val = 1
            self.info(self.tr("Finished successfully!"))

        self.footer_widget.setProperty("success", success_val)
        self.footer_widget.style().polish(self.footer_widget)

        for instance_item in (
            self.instance_model.instance_items.values()
        ):
            instance_item.setData(
                {InstanceStates.HasFinished: True},
                Roles.PublishFlagsRole
            )

        for group_item in self.instance_model.group_items.values():
            group_item.setData(
                {GroupStates.HasFinished: True},
                Roles.PublishFlagsRole
            )

        self.update_compatibility()

    def on_was_processed(self, result):
        existing_ids = set(self.instance_model.instance_items.keys())
        existing_ids.remove(self.controller.context.id)
        for instance in self.controller.context:
            if instance.id not in existing_ids:
                self.instance_model.append(instance)
            else:
                existing_ids.remove(instance.id)

        for instance_id in existing_ids:
            self.instance_model.remove(instance_id)

        if result.get("error"):
            # Toggle from artist to overview tab on error
            if self.tabs["artist"].isChecked():
                self.tabs["overview"].toggle()

        result["records"] = self.terminal_model.prepare_records(result)

        plugin_item = self.plugin_model.update_with_result(result)
        instance_item = self.instance_model.update_with_result(result)

        self.terminal_model.update_with_result(result)
        while not self.terminal_model.items_to_set_widget.empty():
            item = self.terminal_model.items_to_set_widget.get()
            widget = widgets.TerminalDetail(item.data(QtCore.Qt.DisplayRole))
            index = self.terminal_proxy.mapFromSource(item.index())
            self.terminal_view.setIndexWidget(index, widget)

        self.update_compatibility()

        if self.perspective_widget.isVisible():
            self.perspective_widget.update_context(
                plugin_item, instance_item
            )

    # -------------------------------------------------------------------------
    #
    # Functions
    #
    # -------------------------------------------------------------------------

    def reset(self):
        """Prepare GUI for reset"""
        self.info(self.tr("About to reset.."))

        self.presets_button.setEnabled(False)
        self.footer_widget.setProperty("success", -1)
        self.footer_widget.style().polish(self.footer_widget)

        self.instance_model.store_checkstates()
        self.plugin_model.store_checkstates()

        # Reset current ids to secure no previous instances get mixed in.
        self.instance_model.reset()
        self.plugin_model.reset()
        self.intent_model.reset()
        self.terminal_model.reset()

        self.footer_button_stop.setEnabled(False)
        self.footer_button_reset.setEnabled(False)
        self.footer_button_validate.setEnabled(False)
        self.footer_button_play.setEnabled(False)

        self.intent_box.setVisible(self.intent_model.has_items)
        if self.intent_model.has_items:
            self.intent_box.setCurrentIndex(self.intent_model.default_index)

        self.comment_box.placeholder.setVisible(False)
        self.comment_box.placeholder.setVisible(True)
        # Launch controller reset
        util.defer(500, self.controller.reset)

    def validate(self):
        self.info(self.tr("Preparing validate.."))
        self.footer_button_stop.setEnabled(True)
        self.footer_button_reset.setEnabled(False)
        self.footer_button_validate.setEnabled(False)
        self.footer_button_play.setEnabled(False)

        util.defer(5, self.controller.validate)

    def publish(self):
        self.info(self.tr("Preparing publish.."))

        self.footer_button_stop.setEnabled(True)
        self.footer_button_reset.setEnabled(False)
        self.footer_button_validate.setEnabled(False)
        self.footer_button_play.setEnabled(False)

        util.defer(5, self.controller.publish)

    def act(self, plugin_item, action):
        self.info("%s %s.." % (self.tr("Preparing"), action))

        self.footer_button_stop.setEnabled(True)
        self.footer_button_reset.setEnabled(False)
        self.footer_button_validate.setEnabled(False)
        self.footer_button_play.setEnabled(False)

        # Cause view to update, but it won't visually
        # happen until Qt is given time to idle..
        plugin_item.setData(
            PluginActionStates.InProgress, Roles.PluginActionProgressRole
        )

        # Give Qt time to draw
        util.defer(100, lambda: self.controller.act(
            plugin_item.plugin, action
        ))

        self.info(self.tr("Action prepared."))

    def on_was_acted(self, result):
        self.footer_button_reset.setEnabled(True)
        self.footer_button_stop.setEnabled(False)

        # Update action with result
        plugin_item = self.plugin_model.plugin_items[result["plugin"].id]
        action_state = plugin_item.data(Roles.PluginActionProgressRole)
        action_state |= PluginActionStates.HasFinished

        error = result.get("error")
        if error:
            records = result.get("records") or []
            action_state |= PluginActionStates.HasFailed
            fname, line_no, func, exc = error.traceback

            records.append({
                "label": str(error),
                "type": "error",
                "filename": str(fname),
                "lineno": str(line_no),
                "func": str(func),
                "traceback": error.formatted_traceback
            })

            result["records"] = records

        plugin_item.setData(action_state, Roles.PluginActionProgressRole)

        self.plugin_model.update_with_result(result)
        self.instance_model.update_with_result(result)
        self.terminal_model.update_with_result(result)

    def closeEvent(self, event):
        """Perform post-flight checks before closing

        Make sure processing of any kind is wrapped up before closing

        """

        # Make it snappy, but take care to clean it all up.
        # TODO(marcus): Enable GUI to return on problem, such
        # as asking whether or not the user really wants to quit
        # given there are things currently running.
        self.hide()

        if self.state["is_closing"]:

            # Explicitly clear potentially referenced data
            self.info(self.tr("Cleaning up models.."))
            self.intent_model.deleteLater()
            self.plugin_model.deleteLater()
            self.terminal_model.deleteLater()
            self.terminal_proxy.deleteLater()
            self.plugin_proxy.deleteLater()

            self.artist_view.setModel(None)
            self.overview_instance_view.setModel(None)
            self.overview_plugin_view.setModel(None)
            self.terminal_view.setModel(None)

            self.info(self.tr("Cleaning up controller.."))
            self.controller.cleanup()

            self.info(self.tr("All clean!"))
            self.info(self.tr("Good bye"))
            return super(Window, self).closeEvent(event)

        self.info(self.tr("Closing.."))

        def on_problem():
            self.heads_up(
                "Warning", "Had trouble closing down. "
                "Please tell someone and try again."
            )
            self.show()

        if self.controller.is_running:
            self.info(self.tr("..as soon as processing is finished.."))
            self.controller.stop()
            self.finished.connect(self.close)
            util.defer(2000, on_problem)
            return event.ignore()

        self.state["is_closing"] = True

        util.defer(200, self.close)
        return event.ignore()

    def reject(self):
        """Handle ESC key"""

        if self.controller.is_running:
            self.info(self.tr("Stopping.."))
            self.controller.stop()

    # -------------------------------------------------------------------------
    #
    # Feedback
    #
    # -------------------------------------------------------------------------

    def info(self, message):
        """Print user-facing information

        Arguments:
            message (str): Text message for the user

        """

        info = self.findChild(QtWidgets.QLabel, "FooterInfo")
        info.setText(message)

        # Include message in terminal
        self.terminal_model.append({
            "label": message,
            "type": "info"
        })

        self.animation_info_msg.stop()
        self.animation_info_msg.start()

        # TODO(marcus): Should this be configurable? Do we want
        # the shell to fill up with these messages?
        util.u_print(message)

    def warning(self, message):
        """Block processing and print warning until user hits "Continue"

        Arguments:
            message (str): Message to display

        """

        # TODO(marcus): Implement this.
        self.info(message)

    def heads_up(self, title, message, command=None):
        """Provide a front-and-center message with optional command

        Arguments:
            title (str): Bold and short message
            message (str): Extended message
            command (optional, callable): Function is provided as a button

        """

        # TODO(marcus): Implement this.
        self.info(message)
