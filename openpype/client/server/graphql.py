ALL_SUBFIELDS = object()


def fields_to_dict(fields):
    if not fields:
        return ALL_SUBFIELDS

    output = {}
    for field in fields:
        hierarchy = field.split(".")
        last = hierarchy.pop(-1)
        value = output
        for part in hierarchy:
            if value is ALL_SUBFIELDS:
                break

            if part not in value:
                value[part] = {}
            value = value[part]

        if value is not ALL_SUBFIELDS:
            value[last] = ALL_SUBFIELDS
    return output


class GraphQlQueryItem:
    def __init__(self, data, parent=None, offset=None):
        if offset is None:
            offset = 2

        indent = 2
        if parent is not None:
            indent = parent.indent + offset

        self._parent = parent
        self._data = data
        self._children = {}
        self._indent = indent

        for key, value in data.items():
            if value is ALL_SUBFIELDS:
                self._children[key] = ALL_SUBFIELDS
            else:
                self._children[key] = self.__class__(value, self, offset)

    @property
    def indent(self):
        return self._indent

    def calculate_query(self):
        output = []
        output.append("{")
        offset = self.indent * " "
        for key, value in self._children.items():
            part = "{}{}".format(offset, key)
            if value is not ALL_SUBFIELDS:
                part = "{} {}".format(part, value.calculate_query())
            output.append(part)

        ending_indent = 0
        if self._parent is not None:
            ending_indent = self._parent.indent
        output.append((ending_indent * " ") + "}")
        return "\n".join(output)


def fields_to_graphql(fields):
    dicted_fields = fields_to_dict(fields)
    if dicted_fields is ALL_SUBFIELDS:
        return None

    return GraphQlQueryItem(dicted_fields).calculate_query()
