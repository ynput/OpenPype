# Publish
OpenPype is using `pyblish` for publishing process which is a little bit extented and modified mainly for UI purposes. OpenPype's (new) publish UI does not allow to enable/disable instances or plugins that can be done during creation part. Also does support actions only for validators after validation exception.

## Exceptions
OpenPype define few specific exceptions that should be used in publish plugins.

### Validation exception
Validation plugins should raise `PublishValidationError` to show to an artist what's wrong and give him actions to fix it. The exception says that error happened in plugin can be fixed by artist himself (with or without action on plugin). Any other errors will stop publishing immediately. Exception `PublishValidationError` raised after validation order has same effect as any other exception.

Exception `PublishValidationError` 3 arguments:
- **message** Which is not used in UI but for headless publishing.
- **title** Short description of error (2-5 words). Title is used for grouping of exceptions per plugin.
- **description** Detailed description of happened issue where markdown and html can be used.


### Known errors
When there is a known error that can't be fixed by user (e.g. can't connect to deadline service, etc.) `KnownPublishError` should be raise. The only difference is that it's message is shown in UI to artist otherwise a neutral message without context is shown.

## Plugin extension
Publish plugins can be extended by additional logic when inherits from `OpenPypePyblishPluginMixin` which can be used as mixin (additional inheritance of class).

```python
import pyblish.api
from openpype.pipeline import OpenPypePyblishPluginMixin


# Example context plugin
class MyExtendedPlugin(
    pyblish.api.ContextPlugin, OpenPypePyblishPluginMixin
):
    pass

```

### Extensions
Currently only extension is ability to define attributes for instances during creation. Method `get_attribute_defs` returns attribute definitions for families defined in plugin's `families` attribute if it's instance plugin or for whole context if it's context plugin. To convert existing values (or to remove legacy values) can be implemented `convert_attribute_values`. Values of publish attributes from created instance are never removed automatically so implementing of this method is best way to remove legacy data or convert them to new data structure.

Possible attribute definitions can be found in `openpype/pipeline/lib/attribute_definitions.py`.
