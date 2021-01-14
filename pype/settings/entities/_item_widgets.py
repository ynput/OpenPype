class SettingWidget:
    def __init__(self):
        # TODO move to widget
        if not self.available_for_role():
            self.hide()
            self.hidden_by_role = True

    @classmethod
    def style_state(
        cls, has_studio_override, is_invalid, is_overriden, is_modified
    ):
        """Return stylesheet state by intered booleans."""
        items = []
        if is_invalid:
            items.append("invalid")
        else:
            if is_overriden:
                items.append("overriden")
            if is_modified:
                items.append("modified")

        if not items and has_studio_override:
            items.append("studio")

        return "-".join(items) or ""

    def show_actions_menu(self, event=None):
        if event and event.button() != QtCore.Qt.RightButton:
            return

        if not self.allow_actions:
            if event:
                return self.mouseReleaseEvent(event)
            return

        menu = QtWidgets.QMenu()

        actions_mapping = {}
        if self.child_modified:
            action = QtWidgets.QAction("Discard changes")
            actions_mapping[action] = self._discard_changes
            menu.addAction(action)

        if (
            self.is_overidable
            and not self.is_overriden
            and not self.any_parent_is_group
        ):
            action = QtWidgets.QAction("Set project override")
            actions_mapping[action] = self._set_as_overriden
            menu.addAction(action)

        if (
            not self.is_overidable
            and (
                self.has_studio_override or self.child_has_studio_override
            )
        ):
            action = QtWidgets.QAction("Reset to pype default")
            actions_mapping[action] = self._reset_to_pype_default
            menu.addAction(action)

        if (
            not self.is_overidable
            and not self.is_overriden
            and not self.any_parent_is_group
            and not self._had_studio_override
        ):
            action = QtWidgets.QAction("Set studio default")
            actions_mapping[action] = self._set_studio_default
            menu.addAction(action)

        if (
            not self.any_parent_overriden()
            and (self.is_overriden or self.child_overriden)
        ):
            # TODO better label
            action = QtWidgets.QAction("Remove project override")
            actions_mapping[action] = self._remove_overrides
            menu.addAction(action)

        if not actions_mapping:
            action = QtWidgets.QAction("< No action >")
            actions_mapping[action] = None
            menu.addAction(action)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            to_run = actions_mapping[result]
            if to_run:
                to_run()

    def mouseReleaseEvent(self, event):
        if self.allow_actions and event.button() == QtCore.Qt.RightButton:
            return self.show_actions_menu()

        mro = type(self).mro()
        index = mro.index(self.__class__)
        item = None
        for idx in range(index + 1, len(mro)):
            _item = mro[idx]
            if hasattr(_item, "mouseReleaseEvent"):
                item = _item
                break

        if item:
            return item.mouseReleaseEvent(self, event)

    def hierarchical_style_update(self):
        """Trigger update style method down the hierarchy."""
        raise NotImplementedError(
            "{} Method `hierarchical_style_update` not implemented!".format(
                repr(self)
            )
        )
