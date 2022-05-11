import attr
import abc
import six

from openpype.lib import PypeLogger


log = PypeLogger().get_logger("SyncServer")

STATUS = {
    0: 'In Progress',
    1: 'Queued',
    2: 'Failed',
    3: 'Paused',
    4: 'Synced OK',
    -1: 'Not available'
}

DUMMY_PROJECT = "No project configured"


@six.add_metaclass(abc.ABCMeta)
class AbstractColumnFilter:

    def __init__(self, column_name, dbcon=None):
        self.column_name = column_name
        self.dbcon = dbcon
        self._search_variants = []

    def search_variants(self):
        """
            Returns all flavors of search available for this column,
        """
        return self._search_variants

    @abc.abstractmethod
    def values(self):
        """
            Returns dict of available values for filter {'label':'value'}
        """
        pass

    @abc.abstractmethod
    def prepare_match_part(self, values):
        """
            Prepares format valid for $match part from 'values

            Args:
                values (dict): {'label': 'value'}
            Returns:
                (dict): {'COLUMN_NAME': {'$in': ['val1', 'val2']}}
        """
        pass


class PredefinedSetFilter(AbstractColumnFilter):

    def __init__(self, column_name, values):
        super().__init__(column_name)
        self._search_variants = ['checkbox']
        self._values = values
        if self._values and \
                list(self._values.keys())[0] == list(self._values.values())[0]:
            self._search_variants.append('text')

    def values(self):
        return {k: v for k, v in self._values.items()}

    def prepare_match_part(self, values):
        return {'$in': list(values.keys())}


class RegexTextFilter(AbstractColumnFilter):

    def __init__(self, column_name):
        super().__init__(column_name)
        self._search_variants = ['text']

    def values(self):
        return {}

    def prepare_match_part(self, values):
        """ values = {'text1 text2': 'text1 text2'} """
        if not values:
            return {}

        regex_strs = set()
        text = list(values.keys())[0]  # only single key always expected
        for word in text.split():
            regex_strs.add('.*{}.*'.format(word))

        return {"$regex": "|".join(regex_strs),
                "$options": 'i'}


class MultiSelectFilter(AbstractColumnFilter):

    def __init__(self, column_name, values=None, dbcon=None):
        super().__init__(column_name)
        self._values = values
        self.dbcon = dbcon
        self._search_variants = ['checkbox']

    def values(self):
        if self._values:
            return {k: v for k, v in self._values.items()}

        recs = self.dbcon.find({'type': self.column_name}, {"name": 1,
                                                            "_id": -1})
        values = {}
        for item in recs:
            values[item["name"]] = item["name"]
        return dict(sorted(values.items(), key=lambda it: it[1]))

    def prepare_match_part(self, values):
        return {'$in': list(values.keys())}


@attr.s
class FilterDefinition:
    type = attr.ib()
    values = attr.ib(factory=list)


def pretty_size(value, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(value) < 1024.0:
            return "%3.1f%s%s" % (value, unit, suffix)
        value /= 1024.0
    return "%.1f%s%s" % (value, 'Yi', suffix)


def convert_progress(value):
    try:
        progress = float(value)
    except (ValueError, TypeError):
        progress = 0.0

    return progress


def translate_provider_for_icon(sync_server, project, site):
    """
        Get provider for 'site'

        This is used for getting icon, 'studio' should have different icon
        then local sites, even the provider 'local_drive' is same

    """
    if site == sync_server.DEFAULT_SITE:
        return sync_server.DEFAULT_SITE
    return sync_server.get_provider_for_site(site=site)


def get_value_from_id_by_role(model, object_id, role):
    """Return value from item with 'object_id' with 'role'."""
    index = model.get_index(object_id)
    return model.data(index, role)
