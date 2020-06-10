from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import sys
import numbers
import copy
import collections

from .vendor.Qt import QtCore
from .vendor.six import text_type
import pyblish.api

root = os.path.dirname(__file__)


def get_asset(*path):
    """Return path to asset, relative the install directory

    Usage:
        >>> path = get_asset("dir", "to", "asset.png")
        >>> path == os.path.join(root, "dir", "to", "asset.png")
        True

    Arguments:
        path (str): One or more paths, to be concatenated

    """

    return os.path.join(root, *path)


def defer(delay, func):
    """Append artificial delay to `func`

    This aids in keeping the GUI responsive, but complicates logic
    when producing tests. To combat this, the environment variable ensures
    that every operation is synchonous.

    Arguments:
        delay (float): Delay multiplier; default 1, 0 means no delay
        func (callable): Any callable

    """

    delay *= float(os.getenv("PYBLISH_DELAY", 1))
    if delay > 0:
        return QtCore.QTimer.singleShot(delay, func)
    else:
        return func()


def u_print(msg, **kwargs):
    """`print` with encoded unicode.

    `print` unicode may cause UnicodeEncodeError
    or non-readable result when `PYTHONIOENCODING` is not set.
    this will fix it.

    Arguments:
        msg (unicode): Message to print.
        **kwargs: Keyword argument for `print` function.
    """

    if isinstance(msg, text_type):
        encoding = None
        try:
            encoding = os.getenv('PYTHONIOENCODING', sys.stdout.encoding)
        except AttributeError:
            # `sys.stdout.encoding` may not exists.
            pass
        msg = msg.encode(encoding or 'utf-8', 'replace')
    print(msg, **kwargs)


def collect_families_from_instances(instances, only_active=False):
    all_families = set()
    for instance in instances:
        if only_active:
            if instance.data.get("publish") is False:
                continue
        family = instance.data.get("family")
        if family:
            all_families.add(family)

        families = instance.data.get("families") or tuple()
        for family in families:
            all_families.add(family)

    return list(all_families)


class OrderGroups:
    # Validator order can be set with environment "PYBLISH_VALIDATION_ORDER"
    # - this variable sets when validation button will hide and proecssing
    #   of validation will end with ability to continue in process
    default_validation_order = pyblish.api.ValidatorOrder + 0.5

    # Group range can be set with environment "PYBLISH_GROUP_RANGE"
    default_group_range = 1

    # Group string can be set with environment "PYBLISH_GROUP_SETTING"
    default_groups = {
        pyblish.api.CollectorOrder + 0.5: "Collect",
        pyblish.api.ValidatorOrder + 0.5: "Validate",
        pyblish.api.ExtractorOrder + 0.5: "Extract",
        pyblish.api.IntegratorOrder + 0.5: "Integrate",
        None: "Other"
    }

    # *** This example should have same result as is `default_groups` if
    # `group_range` is set to "1"
    __groups_str_example__ = (
        # half of `group_range` is added to 0 because number means it is Order
        "0=Collect"
        # if `<` is before than it means group range is not used
        # but is expected that number is already max
        ",<1.5=Validate"
        # "Extractor" will be used in range `<1.5; 2.5)`
        ",<2.5=Extract"
        ",<3.5=Integrate"
        # "Other" if number is not set than all remaining plugins are in
        # - in this case Other's range is <3.5; infinity)
        ",Other"
    )

    _groups = None
    _validation_order = None
    _group_range = None

    def __init__(
        self, group_str=None, group_range=None, validation_order=None
    ):
        super(OrderGroups, self).__init__()
        # Override class methods with object methods
        self.groups = self._object_groups
        self.validation_order = self._object_validation_order
        self.group_range = self._object_group_range
        self.reset = self._object_reset

        # set
        if group_range is not None:
            self._group_range = self.parse_group_range(
                group_range
            )

        if group_str is not None:
            self._groups = self.parse_group_str(
                group_str
            )

        if validation_order is not None:
            self._validation_order = self.parse_validation_order(
                validation_order
            )

    @staticmethod
    def _groups_method(obj):
        if obj._groups is None:
            obj._groups = obj.parse_group_str(
                group_range=obj.group_range()
            )
        return obj._groups

    @staticmethod
    def _reset_method(obj):
        obj._groups = None
        obj._validation_order = None
        obj._group_range = None

    @classmethod
    def reset(cls):
        return cls._reset_method(cls)

    def _object_reset(self):
        return self._reset_method(self)

    @classmethod
    def groups(cls):
        return cls._groups_method(cls)

    def _object_groups(self):
        return self._groups_method(self)

    @staticmethod
    def _validation_order_method(obj):
        if obj._validation_order is None:
            obj._validation_order = obj.parse_validation_order(
                group_range=obj.group_range()
            )
        return obj._validation_order

    @classmethod
    def validation_order(cls):
        return cls._validation_order_method(cls)

    def _object_validation_order(self):
        return self._validation_order_method(self)

    @staticmethod
    def _group_range_method(obj):
        if obj._group_range is None:
            obj._group_range = obj.parse_group_range()
        return obj._group_range

    @classmethod
    def group_range(cls):
        return cls._group_range_method(cls)

    def _object_group_range(self):
        return self._group_range_method(self)

    @staticmethod
    def sort_groups(_groups_dict):
        sorted_dict = collections.OrderedDict()

        # make sure wont affect any dictionary as pointer
        groups_dict = copy.deepcopy(_groups_dict)
        last_order = None
        if None in groups_dict:
            last_order = groups_dict.pop(None)

        for key in sorted(groups_dict):
            sorted_dict[key] = groups_dict[key]

        if last_order is not None:
            sorted_dict[None] = last_order

        return sorted_dict

    @staticmethod
    def parse_group_str(groups_str=None, group_range=None):
        if groups_str is None:
            groups_str = os.environ.get("PYBLISH_GROUP_SETTING")

        if groups_str is None:
            return OrderGroups.sort_groups(OrderGroups.default_groups)

        items = groups_str.split(",")
        groups = {}
        for item in items:
            if "=" not in item:
                order = None
                label = item
            else:
                order, label = item.split("=")
                order = order.strip()
                if not order:
                    order = None
                elif order.startswith("<"):
                    order = float(order.replace("<", ""))
                else:
                    if group_range is None:
                        group_range = OrderGroups.default_group_range
                        print(
                            "Using default Plugin group range \"{}\".".format(
                                OrderGroups.default_group_range
                            )
                        )
                    order = float(order) + float(group_range) / 2

            if order in groups:
                print((
                    "Order \"{}\" is registered more than once."
                    " Using first found."
                ).format(str(order)))
                continue

            groups[order] = label

        return OrderGroups.sort_groups(groups)

    @staticmethod
    def parse_validation_order(validation_order_value=None, group_range=None):
        if validation_order_value is None:
            validation_order_value = os.environ.get("PYBLISH_VALIDATION_ORDER")

        if validation_order_value is None:
            return OrderGroups.default_validation_order

        if group_range is None:
            group_range = OrderGroups.default_group_range

        group_range_half = float(group_range) / 2

        if isinstance(validation_order_value, numbers.Integral):
            return validation_order_value + group_range_half

        if validation_order_value.startswith("<"):
            validation_order_value = float(
                validation_order_value.replace("<", "")
            )
        else:
            validation_order_value = (
                float(validation_order_value)
                + group_range_half
            )
        return validation_order_value

    @staticmethod
    def parse_group_range(group_range=None):
        if group_range is None:
            group_range = os.environ.get("PYBLISH_GROUP_RANGE")

        if group_range is None:
            return OrderGroups.default_group_range

        if isinstance(group_range, numbers.Integral):
            return group_range

        return float(group_range)
