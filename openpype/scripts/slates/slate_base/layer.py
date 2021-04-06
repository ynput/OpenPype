from .base import BaseObj


class Layer(BaseObj):
    obj_type = "layer"
    available_parents = ["main_frame", "layer"]

    # Direction can be 0=vertical/ 1=horizontal
    def __init__(self, direction=0, *args, **kwargs):
        super(Layer, self).__init__(*args, **kwargs)
        self._direction = direction

    @property
    def item_pos_x(self):
        if self.parent.obj_type == self.obj_type:
            pos_x = self.parent.child_pos_x(self.id)
        elif self.parent.obj_type == "main_frame":
            pos_x = self._pos_x
        else:
            pos_x = self.parent.value_pos_x
        return int(pos_x)

    @property
    def item_pos_y(self):
        if self.parent.obj_type == self.obj_type:
            pos_y = self.parent.child_pos_y(self.id)
        elif self.parent.obj_type == "main_frame":
            pos_y = self._pos_y
        else:
            pos_y = self.parent.value_pos_y

        return int(pos_y)

    @property
    def direction(self):
        if self._direction not in (0, 1):
            self.log.warning((
                "Direction of Layer must be 0 or 1 "
                "(0 is horizontal / 1 is vertical)! Setting to 0."
            ))
            return 0
        return self._direction

    def child_pos_x(self, item_id):
        pos_x = self.value_pos_x
        alignment_hor = self.style["alignment-horizontal"].lower()

        item = None
        for id, _item in self.items.items():
            if item_id == id:
                item = _item
                break

        if self.direction == 1:
            for id, _item in self.items.items():
                if item_id == id:
                    break

                pos_x += _item.width()
                if _item.obj_type not in ["image", "placeholder"]:
                    pos_x += 1

        else:
            if alignment_hor in ["center", "centre"]:
                pos_x += (self.content_width() - item.content_width()) / 2

            elif alignment_hor == "right":
                pos_x += self.content_width() - item.content_width()

            else:
                margin = self.style["margin"]
                margin_left = self.style.get("margin-left") or margin
                pos_x += margin_left

        return int(pos_x)

    def child_pos_y(self, item_id):
        pos_y = self.value_pos_y
        alignment_ver = self.style["alignment-horizontal"].lower()

        item = None
        for id, _item in self.items.items():
            if item_id == id:
                item = _item
                break

        if self.direction != 1:
            for id, item in self.items.items():
                if item_id == id:
                    break
                pos_y += item.height()
                if item.obj_type not in ["image", "placeholder"]:
                    pos_y += 1

        else:
            if alignment_ver in ["center", "centre"]:
                pos_y += (self.content_height() - item.content_height()) / 2

            elif alignment_ver == "bottom":
                pos_y += self.content_height() - item.content_height()

        return int(pos_y)

    def value_height(self):
        height = 0
        for item in self.items.values():
            if self.direction == 1:
                if height > item.height():
                    continue
                # times 1 because won't get object pointer but number
                height = item.height()
            else:
                height += item.height()

        # TODO this is not right
        min_height = self.style.get("min-height")
        if min_height and min_height > height:
            return min_height
        return height

    def value_width(self):
        width = 0
        for item in self.items.values():
            if self.direction == 0:
                if width > item.width():
                    continue
                # times 1 because won't get object pointer but number
                width = item.width()
            else:
                width += item.width()

        min_width = self.style.get("min-width")
        if min_width and min_width > width:
            return min_width
        return width

    def draw(self, image, drawer):
        for item in self.items.values():
            item.draw(image, drawer)
